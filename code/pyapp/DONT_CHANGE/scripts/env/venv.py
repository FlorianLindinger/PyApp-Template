"""The app environment (pyapp/generated/.venv): checked on every launch, built, re-linked, synced.

ensure_environment() is the entry point; it also handles a changed python_version and offers
the package actions used by the dev tools and the missing-package menu.
"""

from __future__ import annotations

import contextlib
import os
import re
import shutil
import subprocess
import sys
import uuid
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Dict, List, Mapping, NamedTuple, Optional, Tuple, Union

from pyapp.DONT_CHANGE.backend_settings import (
    DEV_SETTINGS_PATH,
    ENVIRONMENT_LOCK_PATH,
    ENVIRONMENT_STAMP_PATH,
    PROCESS_REGISTRY_DIR,
    PROJECT_DIR,
    PYPROJECT_PATH,
    PYTHON_SCRIPTS_DIR,
    PYTHON_VERSION_FILE,
    UV_LOCK_PATH,
    VENV_DIR,
    VENV_PYTHON_EXE,
)
from pyapp.DONT_CHANGE.scripts.banner import show_setup_window
from pyapp.DONT_CHANGE.scripts.config import describe_python_request, edit_settings, settings, validate
from pyapp.DONT_CHANGE.scripts.console_tools import (
    ask,
    print_choices,
    print_error,
    print_fields,
    print_heading,
    print_info,
    print_settings_diff,
    print_step,
    print_success,
    print_warn,
)
from pyapp.DONT_CHANGE.scripts.env.pyproject import (
    clear_dependencies,
    current_requires_python,
    declared_dependencies,
    reconcile_pyproject,
    set_requires_python,
    version_satisfies_requires,
)
from pyapp.DONT_CHANGE.scripts.env.pythons import (
    find_or_install_python,
    interpreter_version,
    invalidate_runtime_cache,
    read_python_version_file,
    request_matches,
    version_text,
    write_python_version_file,
)
from pyapp.DONT_CHANGE.scripts.env.uv import run_uv, uv_environment, uv_exe, uv_succeeds
from pyapp.DONT_CHANGE.scripts.errors import LaunchCancelled, SetupError
from pyapp.DONT_CHANGE.scripts.runtime_state import FileLock


class AppPython(NamedTuple):
    """The interpreter that runs main.py and its extra interpreter options."""

    exe: str
    flags: List[str]


# -E: ignore PYTHON* variables. -s: no per-user packages. -X utf8: UTF-8 is the default text encoding.
APP_PYTHON_FLAGS = ["-E", "-s", "-X", "utf8"]


def read_venv_config(venv_dir: str = VENV_DIR) -> Dict[str, str]:
    values = {}
    try:
        with (Path(venv_dir) / "pyvenv.cfg").open(encoding="utf-8") as stream:
            for line in stream:
                if "=" in line:
                    key, value = line.split("=", 1)
                    values[key.strip().lower()] = value.strip()
    except OSError:
        pass
    return values


def venv_version(config: Mapping[str, str]) -> Optional[Tuple[int, ...]]:
    text = config.get("version_info") or config.get("version") or ""
    numbers = re.findall(r"\d+", text)
    return tuple(int(n) for n in numbers[:3]) if len(numbers) >= 2 else None


def venv_home_valid(config: Mapping[str, str]) -> bool:
    home = config.get("home", "")
    return bool(home) and (Path(home) / "python.exe").is_file()


def venv_base_executable(venv_dir: str = VENV_DIR) -> Optional[str]:
    """The base interpreter the venv's python.exe really starts, or None if it cannot start.

    uv venvs on Windows can store the base path inside Scripts\\python.exe itself, so
    pyvenv.cfg alone does not show whether a moved project still works.
    """
    exe = str(Path(venv_dir) / "Scripts" / "python.exe")
    try:
        # Probe the selected interpreter or intentionally open the package command prompt.
        output = subprocess.check_output(  # noqa: S603
            [
                exe,
                "-I",
                "-S",
                "-X",
                "utf8",
                "-c",
                "import sys; print(getattr(sys, '_base_executable', sys.executable))",
            ],
            universal_newlines=True,
            encoding="utf-8",
            stderr=subprocess.DEVNULL,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    base = output.strip()
    return base if Path(base).is_file() else None


def _same_file(first: str, second: str) -> bool:
    return os.path.normcase(os.path.realpath(first)) == os.path.normcase(os.path.realpath(second))


def venv_needs_relink(config: Mapping[str, str], base_python: str) -> bool:
    """True if the venv points at a missing or different base interpreter than the project's Python."""
    if not venv_home_valid(config):
        return True
    base = venv_base_executable()
    return base is None or not _same_file(base, base_python)


def relink_venv(base_python: str, s: Optional[Union[ModuleType, SimpleNamespace]] = None) -> bool:
    """Point an existing venv at base_python (moved project, portable copy), keeping its packages."""
    previous = read_venv_config().get("home", "?")
    code = run_uv(
        ["venv", "--allow-existing", "--relocatable", "--quiet", "--python", base_python, VENV_DIR], check=False, s=s
    )
    # uv caches interpreter details keyed on python.exe's timestamp, which the re-link does not
    # change; without a new timestamp uv would keep using the old base and rebuild the venv.
    for name in ("python.exe", "pythonw.exe"):
        with contextlib.suppress(OSError):
            os.utime(str(Path(VENV_DIR) / "Scripts" / name), None)
    base = venv_base_executable()
    if code or base is None or not _same_file(base, base_python):
        return False
    print_info(
        f'Re-linked the environment to "{Path(base_python).parent!s}" (was "{previous}"), e.g. after moving the project.'
    )
    return True


def refuse_mutation_while_running() -> None:
    """Running app instances lock files inside the environment."""
    from pyapp.DONT_CHANGE.scripts.runtime_state import ProcessRegistry

    records, _ = ProcessRegistry(PROCESS_REGISTRY_DIR).records()
    if records:
        raise SetupError("Close the running app instance(s) first; they use the files in the Python environment.")


def ensure_lock(s: Optional[Union[ModuleType, SimpleNamespace]] = None) -> None:
    """Create or update uv.lock when pyproject.toml changed (offline first)."""
    if Path(UV_LOCK_PATH).is_file() and uv_succeeds(["lock", "--check", "--offline"], s=s):
        return
    print_step("Updating uv.lock for the declared dependencies...")
    if uv_succeeds(["lock", "--offline"], s=s):
        return
    run_uv(["lock"], s=s)


def sync(
    python_exe: str,
    *,
    venv_dir: str = VENV_DIR,
    exact: bool = False,
    s: Optional[Union[ModuleType, SimpleNamespace]] = None,
) -> None:
    """Install exactly what uv.lock says (offline first, then online)."""
    arguments = ["sync", "--locked", "--python", python_exe]
    if not exact:
        arguments.append("--inexact")  # keep packages added by hand (uv pip install) until the next exact sync
    project_environment = None if os.path.normcase(venv_dir) == os.path.normcase(VENV_DIR) else venv_dir
    if uv_succeeds([*arguments, "--offline"], project_environment=project_environment, s=s):
        return
    show_setup_window()
    print_step("Installing packages...")
    run_uv(arguments, project_environment=project_environment, s=s)


def best_effort_install(python_exe: str, s: Optional[Union[ModuleType, SimpleNamespace]] = None) -> None:
    """For a Python outside requires-python: install the declared dependencies without the lock."""
    if not declared_dependencies():
        return
    if not uv_succeeds(["pip", "install", "--python", python_exe, "-r", PYPROJECT_PATH, "--offline"], s=s):
        run_uv(["pip", "install", "--python", python_exe, "-r", PYPROJECT_PATH], s=s)


def create_venv(base_python: str, venv_dir: str, s: Optional[Union[ModuleType, SimpleNamespace]] = None) -> None:
    run_uv(["venv", "--relocatable", "--quiet", "--python", base_python, venv_dir], s=s)


def build_venv(
    base_python: str, *, locked: bool = True, s: Optional[Union[ModuleType, SimpleNamespace]] = None
) -> None:
    """Build a new venv beside the old one, fill it, then swap it in (the old one stays until then)."""
    staging = VENV_DIR + ".staging-" + uuid.uuid4().hex[:8]
    try:
        show_setup_window()
        print_step(f"Creating the app environment for Python {version_text(interpreter_version(base_python))}...")
        create_venv(base_python, staging, s)
        staged_python = str(Path(staging) / "Scripts" / "python.exe")
        if locked:
            sync(staged_python, venv_dir=staging, exact=True, s=s)
        else:
            best_effort_install(staged_python, s)
        swap_in_venv(staging)
    finally:
        if Path(staging).is_dir():
            shutil.rmtree(staging, ignore_errors=True)


def swap_in_venv(staging: str) -> None:
    previous = VENV_DIR + ".previous-" + uuid.uuid4().hex[:8]
    if Path(VENV_DIR).is_dir():
        Path(VENV_DIR).rename(previous)
    try:
        Path(staging).rename(VENV_DIR)
    except OSError:
        if Path(previous).is_dir():
            Path(previous).rename(VENV_DIR)
        raise
    if Path(previous).is_dir():
        shutil.rmtree(previous, ignore_errors=True)
        if Path(previous).is_dir():
            print_warn(f'The old environment could not be deleted completely: "{previous}"')


def ensure_environment(interactive: bool = True) -> AppPython:
    """Validate settings and make sure the app's interpreter and packages are ready."""
    s = settings()
    validate(s)
    Path(PROJECT_DIR).mkdir(parents=True, exist_ok=True)
    base_python = sys.executable

    with FileLock(ENVIRONMENT_LOCK_PATH, timeout=600):
        base_version = tuple(sys.version_info[:3])  # base_python is this interpreter
        file_request = read_python_version_file()

        if file_request is None:
            # First run: the bootstrap resolved the launcher Python from python_version.
            # An empty python_version keeps the newest Python chosen now ("pick once").
            request = s.python_version or ".".join(str(n) for n in base_version[:2])
            write_python_version_file(request)
        elif not request_matches(s.python_version, file_request):
            switched = handle_version_change(file_request, s, interactive)
            if switched:
                return AppPython(VENV_PYTHON_EXE, APP_PYTHON_FLAGS)
        # pyproject.toml follows developer_settings.py ("packages"); requires-python follows the project's Python.
        s = reconcile_pyproject(s, None if current_requires_python() else base_version)

        # Fast path: nothing relevant changed since the last successful check, so skip the uv
        # lock check, the sync and the venv check (each starts a process).
        fingerprint = environment_fingerprint(s)
        if _read_stamp() == fingerprint:
            return AppPython(VENV_PYTHON_EXE, APP_PYTHON_FLAGS)
        # From here on the environment may be synced or rebuilt, which a running instance would
        # see change under it (or block with its open files).
        refuse_mutation_while_running()
        _write_stamp(None)

        locked = version_satisfies_requires(base_version, current_requires_python())
        if not locked:
            print_warn(
                f"Python {version_text(base_version)} is outside requires-python ({current_requires_python()}); "
                "installing the declared dependencies without the lock file."
            )
        if locked:
            ensure_lock(s)

        config = read_venv_config()
        if not Path(VENV_PYTHON_EXE).is_file() or not config:
            build_venv(base_python, locked=locked, s=s)
        elif (venv_version(config) or ())[:2] == base_version[:2] and venv_needs_relink(config, base_python):
            # The project (or its Python) moved: re-link instead of reinstalling (works offline).
            if not relink_venv(base_python, s):
                build_venv(base_python, locked=locked, s=s)
            elif locked:
                sync(VENV_PYTHON_EXE, s=s)
        elif (venv_version(config) or ())[:2] != base_version[:2]:
            print_info(
                f"The environment uses Python {version_text(venv_version(config) or ())}; rebuilding it for Python {version_text(base_version)}."
            )
            build_venv(base_python, locked=locked, s=s)
        elif locked:
            sync(VENV_PYTHON_EXE, s=s)
        else:
            best_effort_install(VENV_PYTHON_EXE, s)
        if locked:
            _write_stamp(environment_fingerprint(s))
    return AppPython(VENV_PYTHON_EXE, APP_PYTHON_FLAGS)


def environment_fingerprint(s: Union[ModuleType, SimpleNamespace]) -> str:
    """Everything the environment check depends on: files (time and size), paths and settings.

    Any change (uv.lock, pyproject.toml, packages added or removed in site-packages, a moved
    project, another Python or uv, ...) makes the next launch run the full check again.
    """
    import hashlib

    parts = [
        "v2",
        PROJECT_DIR,
        sys.executable,
        ".".join(map(str, sys.version_info)),
        os.environ.get("PYAPP_UV", ""),
        s.python_source,
        s.uv_cache,
    ]
    for path in (
        sys.executable,
        PYPROJECT_PATH,
        UV_LOCK_PATH,
        PYTHON_VERSION_FILE,
        VENV_PYTHON_EXE,
        str(Path(VENV_DIR) / "pyvenv.cfg"),
    ):
        try:
            stat = Path(path).stat()
            parts.append(f"{path}|{stat.st_mtime_ns}|{stat.st_size}")
        except OSError:
            parts.append(f"{path}|missing")
    parts.append(_site_packages_entries())
    return hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()


def _site_packages_entries() -> str:
    """The names in site-packages, without __pycache__, as one line for the fingerprint.

    Not the folder's modification time: uv does not compile bytecode, so the app's first import
    of a top-level module (six.py, typing_extensions.py, ...) creates site-packages\\__pycache__ and
    changes that time. The stamp written by Setup would then never match on the second start, which
    repeats the uv checks and refuses to start while the first instance runs. Installing, removing
    or upgrading a package always adds, removes or renames a *.dist-info folder, so the names
    still see every change uv or pip makes.
    """
    site_packages = Path(VENV_DIR) / "Lib" / "site-packages"
    try:
        names = sorted(entry.name for entry in os.scandir(site_packages) if entry.name != "__pycache__")
    except OSError:
        return f"{site_packages}|missing"
    return f"{site_packages}|" + "|".join(names)


def _read_stamp() -> Optional[str]:
    try:
        with Path(ENVIRONMENT_STAMP_PATH).open(encoding="utf-8") as stream:
            return stream.read().strip()
    except OSError:
        return None


def _write_stamp(fingerprint: Optional[str]) -> None:
    """Record a successful check (None forgets it, e.g. before changing the environment)."""
    try:
        if fingerprint is None:
            if Path(ENVIRONMENT_STAMP_PATH).exists():
                Path(ENVIRONMENT_STAMP_PATH).unlink()
        else:
            with Path(ENVIRONMENT_STAMP_PATH).open("w", encoding="utf-8") as stream:
                stream.write(fingerprint)
    except OSError:
        from pyapp.DONT_CHANGE.scripts.diagnostics import note_ignored

        note_ignored("environment stamp")


def handle_version_change(current: str, s: Union[ModuleType, SimpleNamespace], interactive: bool) -> bool:
    """python_version differs from the Python the project uses. Returns True after a switch."""
    wanted = s.python_version
    show_setup_window()
    print()
    print_warn(
        f"python_version in developer_settings.py is {describe_python_request(wanted)}, but this project uses Python {current} (pyapp\\generated\\.python-version)."
    )
    choices = [
        f"Switch to Python {wanted}; re-lock, keeping package versions where possible",
        f"Switch to Python {wanted}; re-lock and upgrade all packages",
        f"Switch to Python {wanted} with an empty package list (empties packages in developer_settings.py)",
        f"Keep Python {current} for this launch (ask again next time)",
        f'Keep Python {current} and set python_version = "{current}" in developer_settings.py',
        "Cancel this launch",
    ]
    print_choices(choices)
    if not interactive or sys.stdin is None:
        raise SetupError(
            "python_version changed; run a launch with a terminal or the change_python dev tool to choose how to switch."
        )
    while True:
        try:
            # Enter: the last choice, cancel this launch.
            answer = ask(f"What now? [1-{len(choices)}, Enter = cancel]").strip() or str(len(choices))
        except EOFError:
            raise SetupError(
                "python_version changed, but no answer could be read; run the change_python dev tool."
            ) from None
        if answer in {str(i) for i in range(1, len(choices) + 1)}:
            break
    answer = int(answer)
    if answer == 6:
        raise LaunchCancelled()
    if answer == 4:
        return False
    if answer == 5:
        print_settings_diff(edit_settings({"python_version": current}))
        return False
    if (
        answer == 3
        and ask('This empties "packages" in developer_settings.py. Type yes to continue:').strip().lower() != "yes"
    ):
        raise LaunchCancelled()
    switch_python(wanted, upgrade=answer == 2, clear=answer == 3, s=s)
    return True


def switch_python(
    request: str, *, upgrade: bool = False, clear: bool = False, s: Optional[Union[ModuleType, SimpleNamespace]] = None
) -> None:
    """Move the project to another Python; restores all files if anything fails."""
    s = s or settings()
    refuse_mutation_while_running()
    new_python = find_or_install_python(request, s)
    new_version = interpreter_version(new_python)
    backups: Dict[str, Optional[bytes]] = {}
    for path in (PYPROJECT_PATH, UV_LOCK_PATH, PYTHON_VERSION_FILE, DEV_SETTINGS_PATH):
        try:
            with Path(path).open("rb") as stream:
                backups[path] = stream.read()
        except OSError:
            backups[path] = None
    try:
        write_python_version_file(request)
        set_requires_python(new_version)
        if clear:
            clear_dependencies()
        print_step(f"Re-locking dependencies for Python {version_text(new_version)}...")
        lock_arguments = ["lock"] + (["--upgrade"] if upgrade else [])
        if not uv_succeeds([*lock_arguments, "--offline"], s=s):
            run_uv(lock_arguments, s=s)
        build_venv(new_python, locked=True, s=s)
    except BaseException:
        for path, content in backups.items():
            if content is None:
                if Path(path).exists():
                    Path(path).unlink()
            else:
                with Path(path).open("wb") as stream:
                    stream.write(content)
        sys.modules.pop("pyapp.developer_settings", None)
        print_error("Switching Python failed; the previous Python, environment and files were kept.")
        raise
    invalidate_runtime_cache()
    print_success(f"The project now uses Python {version_text(new_version)}.")


def add_packages(names: List[str], s: Optional[Union[ModuleType, SimpleNamespace]] = None) -> None:
    """uv add (resolves, locks, installs), then record the result in developer_settings.py."""
    refuse_mutation_while_running()
    reconcile_pyproject(s)
    run_uv(["add", *names], s=s)
    reconcile_pyproject()


def remove_packages(names: List[str], s: Optional[Union[ModuleType, SimpleNamespace]] = None) -> None:
    """uv remove, then record the result in developer_settings.py."""
    refuse_mutation_while_running()
    reconcile_pyproject(s)
    run_uv(["remove", *names], s=s)
    reconcile_pyproject()


def install_without_recording(
    names: List[str], python_exe: str, s: Optional[Union[ModuleType, SimpleNamespace]] = None
) -> None:
    """Install into an environment without recording it in developer_settings.py (uv pip install)."""
    refuse_mutation_while_running()
    run_uv(["pip", "install", "--python", python_exe, *names], s=s)


def open_package_terminal(s: Optional[Union[ModuleType, SimpleNamespace]] = None) -> int:
    """Open a command prompt with the app environment activated and uv on PATH; wait for exit."""
    s = s or settings()
    env = uv_environment(s, python_command=False)
    env["VIRTUAL_ENV"] = VENV_DIR
    env["UV_PROJECT"] = PROJECT_DIR  # uv add/remove/lock work from the code folder too
    env["PATH"] = os.pathsep.join([str(Path(VENV_DIR) / "Scripts"), str(Path(uv_exe()).parent), env.get("PATH", "")])
    env["PROMPT"] = "(app packages) $P$G"
    # Printed here, not with "echo" inside the cmd command line: paths like "R&D" would break that.
    print_heading("Package terminal")
    print_info("Python: " + VENV_PYTHON_EXE)
    print_fields(
        [
            ("uv add NAME", "add a package and install it (copied into developer_settings.py on the next start)"),
            ("", "only plain uv add is kept: --dev, --group and --optional packages are dropped"),
            ("uv remove NAME", "remove a package"),
            ("uv lock --upgrade", "upgrade all packages, then: uv sync"),
            ("uv pip list", "show installed packages"),
            ("uv pip install NAME", "install without recording it (the next exact sync removes it)"),
            ("python ...", "run this Python"),
            ("exit", "close this terminal"),
        ]
    )
    print(flush=True)
    # Probe the selected interpreter or intentionally open the package command prompt.
    from pyapp.DONT_CHANGE.backend_settings import CMD_EXE

    return subprocess.run([CMD_EXE, "/d"], cwd=PYTHON_SCRIPTS_DIR, env=env, check=False).returncode  # noqa: S603
