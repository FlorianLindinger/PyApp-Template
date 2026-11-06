"""Application environment managed by uv: Python selection, the project venv and packages.

The launcher runs on the project's Python with -I -S (standard library only). The
batch bootstrap (DONT_CHANGE/bootstrap) already found uv (PYAPP_UV) and that Python
(sys.executable). This module keeps the uv project in code/backend (generated
pyproject.toml, uv.lock, .python-version, .venv) consistent with developer_settings.py.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import uuid
from collections import namedtuple

from backend.DONT_CHANGE.scripts.config import (
    SettingsError,
    describe_python_request,
    edit_settings,
    settings,
    validate,
)
from backend.DONT_CHANGE.scripts.console_tools import input_warn, print_warn, show_console
from backend.DONT_CHANGE.scripts.runtime_state import FileLock
from backend.DONT_CHANGE.backend_settings import (
    ENVIRONMENT_LOCK_PATH,
    LOCAL_PYTHONS_DIR,
    LOCAL_UV_CACHE_DIR,
    LOCAL_UV_EXE,
    MINIMUM_PYTHON,
    PROCESS_ID_FILE_PATH,
    DEV_SETTINGS_PATH,
    PROJECT_DIR,
    PYPROJECT_PATH,
    PYTHON_SCRIPTS_DIR,
    PYTHON_VERSION_FILE,
    RUNTIME_CACHE_PATH,
    UV_LOCK_PATH,
    VENV_DIR,
    VENV_PYTHON_EXE,
)

AppPython = namedtuple("AppPython", "exe flags kind")
"""exe: interpreter that runs main.py; flags: extra interpreter options; kind: "venv" or "interpreter"."""


class SetupError(RuntimeError):
    """The environment cannot be prepared; the message says what to do."""


class LaunchCancelled(Exception):
    """The user chose to cancel this launch."""


# ---------------------------------------------------------------- uv


def downloads_allowed(s=None) -> bool:
    """Normal launches follow allow_downloads_at_launch; Setup and dev tools set PYAPP_ALLOW_DOWNLOADS=1."""
    s = s or settings()
    return bool(s.allow_downloads_at_launch) or os.environ.get("PYAPP_ALLOW_DOWNLOADS") == "1"


def uv_exe() -> str:
    """Return the uv chosen by the bootstrap, or the best available fallback."""
    path = os.environ.get("PYAPP_UV", "")
    if path and os.path.isfile(path):
        return path
    if os.path.isfile(LOCAL_UV_EXE):
        return LOCAL_UV_EXE
    found = shutil.which("uv")
    if found:
        return found
    raise SetupError(
        "uv was not found. Start the app through a shortcut or 'Setup - run first and after moving folder.cmd' so the bootstrap can install it."
    )


_OWN_UV_VARIABLES = (
    "UV_PYTHON",
    "UV_PYTHON_INSTALL_DIR",
    "UV_MANAGED_PYTHON",
    "UV_NO_MANAGED_PYTHON",
    "UV_PYTHON_PREFERENCE",
    "UV_PYTHON_INSTALL_BIN",
    "UV_PYTHON_INSTALL_REGISTRY",
    "UV_PROJECT_ENVIRONMENT",
    "UV_PROJECT",
    "UV_WORKING_DIR",
    "UV_NO_SYNC",
    "UV_FROZEN",
    "UV_LOCKED",
    "UV_OFFLINE",
    "UV_CACHE_DIR",
    "UV_PYTHON_DOWNLOADS",
)


def uv_environment(s=None, project_environment: str | None = None, python_command: bool = True) -> dict:
    """Environment for uv calls. Mirrors Set-UvEnvironment in bootstrap/resolve_runtime.ps1.

    The user's other UV_* settings (index URLs, proxies, ...) are kept on purpose.
    """
    s = s or settings()
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.upper().startswith(("PYTHON", "PIP_", "CONDA_"))
        and key.upper() not in ("VIRTUAL_ENV", "PYAPP_ENTRY_SCRIPT")
        and key.upper() not in _OWN_UV_VARIABLES
    }
    source = s.python_source
    if source == "uv_user":
        visible = "1" if s.uv_user_python_visible_globally else "0"
        env.update(UV_MANAGED_PYTHON="1", UV_PYTHON_INSTALL_BIN=visible, UV_PYTHON_INSTALL_REGISTRY=visible)
    elif source == "local":
        env.update(UV_PYTHON_INSTALL_DIR=LOCAL_PYTHONS_DIR, UV_MANAGED_PYTHON="1", UV_PYTHON_INSTALL_BIN="0", UV_PYTHON_INSTALL_REGISTRY="0")
    else:
        env.update(UV_PYTHON_INSTALL_DIR=LOCAL_PYTHONS_DIR, UV_PYTHON_PREFERENCE="system", UV_PYTHON_INSTALL_BIN="0", UV_PYTHON_INSTALL_REGISTRY="0")
    if s.uv_cache == "local":
        env["UV_CACHE_DIR"] = LOCAL_UV_CACHE_DIR
    if s.use_system_certificates:
        env["UV_SYSTEM_CERTS"] = "1"
    env["UV_PYTHON_DOWNLOADS"] = "automatic" if downloads_allowed(s) else "never"
    # The uv cache is often on another drive than the project; copying avoids uv's hard-link warning.
    env.setdefault("UV_LINK_MODE", "copy")
    if project_environment:
        env["UV_PROJECT_ENVIRONMENT"] = project_environment
    if not python_command and env.pop("UV_MANAGED_PYTHON", None):
        # Project commands always get an explicit --python. "Only managed" would make uv re-check
        # the venv against interpreter details it cached before a move/re-link and rebuild the venv.
        env["UV_PYTHON_PREFERENCE"] = "managed"
    return env


def run_uv(arguments, *, capture=False, check=True, cwd=None, project_environment=None, s=None):
    """Run uv; with capture=True return (code, stdout, stderr), otherwise the exit code."""
    command = [uv_exe(), *arguments]
    result = subprocess.run(
        command,
        cwd=cwd or PROJECT_DIR,
        env=uv_environment(s, project_environment, python_command=arguments[:1] == ["python"]),
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
        universal_newlines=True if capture else None,
        encoding="utf-8" if capture else None,
        errors="replace" if capture else None,
    )
    if check and result.returncode:
        detail = (result.stderr or "").strip() if capture else ""
        raise SetupError(
            "uv " + " ".join(arguments[:2]) + f" failed (exit code {result.returncode})." + ("\n" + detail if detail else "")
        )
    if capture:
        return result.returncode, result.stdout or "", result.stderr or ""
    return result.returncode


def uv_version() -> str:
    """Return the uv version string, e.g. "0.11.32"."""
    _, out, _ = run_uv(["--version"], capture=True, check=False)
    parts = out.split()
    return parts[1] if len(parts) > 1 else "?"


# ---------------------------------------------------------------- Python


def interpreter_version(exe: str) -> tuple:
    """Return (major, minor, micro) of an interpreter without running site or user code."""
    output = subprocess.check_output(
        [exe, "-I", "-S", "-c", "import sys; print('%d.%d.%d' % sys.version_info[:3])"],
        universal_newlines=True,
        timeout=30,
    )
    return tuple(int(part) for part in output.strip().split("."))


def version_text(version: tuple) -> str:
    return ".".join(str(part) for part in version)


def find_python(request: str, s=None) -> str | None:
    """Return the interpreter uv would use for a request ("" = system default), or None."""
    arguments = ["python", "find", "--no-project"] + ([request] if request else [])
    # Run outside the project, otherwise uv returns the project .venv's interpreter.
    code, out, _ = run_uv(arguments, capture=True, check=False, cwd=tempfile.gettempdir(), s=s)
    lines = [line.strip() for line in out.splitlines() if line.strip()]
    return lines[-1] if code == 0 and lines else None


def python_downloads(all_versions=False, s=None) -> list:
    """Downloadable CPython builds for this PC as uv reports them."""
    arguments = ["python", "list", "--only-downloads", "--output-format", "json"]
    if all_versions:
        arguments.append("--all-versions")
    code, out, _ = run_uv(arguments, capture=True, check=False, cwd=tempfile.gettempdir(), s=s)
    if code:
        return []
    try:
        entries = json.loads(out)
    except ValueError:
        return []
    return [e for e in entries if e.get("implementation") == "cpython" and e.get("variant") == "default"]


def _version_key(text: str) -> tuple:
    return tuple(int(n) for n in re.findall(r"\d+", text)[:3])


def newest_stable_minor(s=None) -> str:
    """Return "X.Y" of the newest stable CPython uv offers."""
    stable = [e["version"] for e in python_downloads(s=s) if re.fullmatch(r"\d+\.\d+\.\d+", e.get("version", ""))]
    if not stable:
        raise SetupError('uv could not list downloadable Python versions (no internet?). Set python_version, e.g. "3.14".')
    newest = max(stable, key=_version_key)
    return ".".join(newest.split(".")[:2])


def available_summary(s=None) -> str:
    """One line describing which Python versions uv can install here."""
    versions = sorted({e["version"] for e in python_downloads(True, s)}, key=_version_key)
    if not versions:
        return "uv could not list the downloadable versions (no internet?)."
    minors = []
    for v in versions:
        minor = ".".join(v.split(".")[:2])
        if minor not in minors:
            minors.append(minor)
    return f"uv offers {versions[0]} to {versions[-1]} for this PC (minor versions: {', '.join(minors)})."


def install_python(request: str, s=None) -> str:
    """Install a Python with uv (location per python_source) and return its executable."""
    s = s or settings()
    if not downloads_allowed(s):
        raise SetupError(
            f"Python {request} is not installed and downloads at launch are disabled (allow_downloads_at_launch = False). "
            "Run Setup or a dev tool once with internet access."
        )
    show_console()
    print(f"[Setup] Installing Python {request} with uv...")
    if run_uv(["python", "install", request], check=False, cwd=tempfile.gettempdir(), s=s):
        raise SetupError(
            f"uv could not install Python '{request}'. {available_summary(s)} The launcher needs Python 3.8 or newer. "
            "Check python_version in developer_settings.py."
        )
    exe = find_python(request, s)
    if not exe:
        raise SetupError(f"Python {request} was installed but uv cannot find it.")
    return exe


def find_or_install_python(request: str, s=None) -> str:
    """Return a usable interpreter for request, installing it if needed, and check the 3.8 minimum."""
    exe = find_python(request, s) or install_python(request, s)
    version = interpreter_version(exe)
    if version[:2] < MINIMUM_PYTHON:
        raise SetupError(
            f"Python {version_text(version)} is older than 3.8, which the launcher needs. Choose python_version 3.8 or newer."
        )
    return exe


def read_python_version_file() -> str | None:
    """Return the request stored in backend/.python-version, or None."""
    try:
        with open(PYTHON_VERSION_FILE, encoding="utf-8") as stream:
            for line in stream:
                line = line.strip()
                if line and not line.startswith("#"):
                    return line
    except OSError:
        pass
    return None


def write_python_version_file(request: str) -> None:
    with open(PYTHON_VERSION_FILE, "w", encoding="utf-8", newline="\n") as stream:
        stream.write(request + "\n")


def request_matches(setting_value: str, file_value: str | None) -> bool:
    """python_version "" accepts the Python chosen earlier; otherwise both requests must be equal."""
    if file_value is None:
        return False
    if not setting_value:
        return True
    return setting_value.strip().lower() == file_value.strip().lower()


def invalidate_runtime_cache() -> None:
    """Make the next batch bootstrap look up uv and Python again."""
    try:
        os.remove(RUNTIME_CACHE_PATH)
    except OSError:
        pass


# ---------------------------------------------------------------- pyproject.toml (generated)
#
# developer_settings.py ("packages", python_version) is the only place people edit. pyproject.toml
# is generated from it for uv. Its header records the package list it was generated from, so a
# change made to the file itself (e.g. "uv add" in a terminal) can be told apart from a change in
# developer_settings.py and copied back into the settings.

GENERATED_FROM_MARKER = "# generated-from-packages: "

PYPROJECT_TEMPLATE = """# GENERATED by the launcher from developer_settings.py ("packages" and python_version).
# Do not edit: change "packages" in developer_settings.py or use the dev tools. Changes made
# here anyway (for example with "uv add" in a terminal) are copied into developer_settings.py.
{marker}{base}
[project]
name = "pyapp"
version = "0.1.0"
requires-python = "{requires}"
dependencies = {dependencies}

[tool.uv]
package = false
"""


def requires_python_for(version: tuple) -> str:
    return f"=={version[0]}.{version[1]}.*"


def read_pyproject() -> str:
    with open(PYPROJECT_PATH, encoding="utf-8") as stream:
        return stream.read()


def write_pyproject(text: str) -> None:
    with open(PYPROJECT_PATH, "w", encoding="utf-8", newline="\n") as stream:
        stream.write(text)


def render_pyproject(packages, requires: str) -> str:
    """pyproject.toml text for a package list (JSON strings are valid TOML basic strings here)."""
    if packages:
        dependencies = "[\n" + "".join(f"    {json.dumps(p)},\n" for p in packages) + "]"
    else:
        dependencies = "[]"
    return PYPROJECT_TEMPLATE.format(
        marker=GENERATED_FROM_MARKER, base=json.dumps(list(packages)), requires=requires, dependencies=dependencies
    )


def _recorded_packages(text: str):
    """The package list the file was generated from, or None (hand-written or older file)."""
    for line in text.splitlines():
        if line.startswith(GENERATED_FROM_MARKER):
            try:
                value = json.loads(line[len(GENERATED_FROM_MARKER) :])
            except ValueError:
                return None
            return value if isinstance(value, list) and all(isinstance(v, str) for v in value) else None
    return None


def reconcile_pyproject(s=None, version: tuple | None = None):
    """Generate pyproject.toml from developer_settings.py; copy edits made to the file into the settings.

    version: the project's Python, used for requires-python (default: keep the file's value, or the
    launcher's own Python on the first run). Returns the settings module, reloaded if it was edited.
    """
    from backend.DONT_CHANGE.scripts.config import set_list_setting

    s = s or settings()
    wanted = list(s.packages)
    requires = requires_python_for(version) if version else None
    if os.path.isfile(PYPROJECT_PATH):
        text = read_pyproject()
        in_file = declared_dependencies(text)
        recorded = _recorded_packages(text)
        if recorded is None:
            # Hand-written file (or one from before packages moved into the settings): take its
            # packages over only when the settings have none, otherwise the settings win.
            recorded = [] if in_file and not wanted else wanted
        if in_file != recorded and wanted == recorded:
            print("[Info] Copied package changes made in pyproject.toml (e.g. with uv add) into developer_settings.py: " + _change_summary(wanted, in_file))
            set_list_setting("packages", in_file)
            s = settings()
            wanted = list(s.packages)
        elif in_file != recorded and in_file != wanted:
            ignored = [p for p in in_file if p not in wanted]
            print_warn(
                "[Warning] The packages were changed both in developer_settings.py and in pyproject.toml; "
                "developer_settings.py wins." + (" Not taken over: " + ", ".join(ignored) if ignored else "")
            )
        requires = requires or current_requires_python(text)
    requires = requires or requires_python_for(sys.version_info[:2])
    new_text = render_pyproject(wanted, requires)
    if not os.path.isfile(PYPROJECT_PATH) or read_pyproject() != new_text:
        write_pyproject(new_text)
    return s


def _change_summary(old, new) -> str:
    changes = ["+ " + p for p in new if p not in old] + ["- " + p for p in old if p not in new]
    return ", ".join(changes) or "new order"


def set_requires_python(version: tuple, s=None):
    """Point requires-python at the interpreter's minor version (and regenerate pyproject.toml)."""
    return reconcile_pyproject(s, version)


def current_requires_python(text: str | None = None) -> str | None:
    try:
        text = read_pyproject() if text is None else text
    except OSError:
        return None
    match = re.search(r'(?m)^requires-python\s*=\s*"([^"]*)"', text)
    return match.group(1) if match else None


def version_satisfies_requires(version: tuple, requires: str | None) -> bool:
    """Support the "==X.Y.*" form this launcher writes; other forms are left to uv."""
    if not requires:
        return True
    match = re.fullmatch(r"==\s*(\d+)\.(\d+)\.\*", requires.strip())
    if not match:
        return True
    return version[:2] == (int(match.group(1)), int(match.group(2)))


def declared_dependencies(text: str | None = None) -> list:
    """Return the [project] dependencies strings of pyproject.toml (simple parser for uv-written files)."""
    if text is None:
        try:
            text = read_pyproject()
        except OSError:
            return []
    span = _dependencies_span(text)
    if not span:
        return []
    return re.findall(r'"([^"]+)"', text[span[0] : span[1]])


def _dependencies_span(text: str):
    """Locate the value of dependencies = [...] inside [project]."""
    project = re.search(r"(?m)^\[project\]\s*$", text)
    if not project:
        return None
    following = re.search(r"(?m)^\[", text[project.end() :])
    end_of_table = project.end() + following.start() if following else len(text)
    key = re.compile(r"(?m)^dependencies\s*=\s*\[").search(text, project.end(), end_of_table)
    if not key:
        return None
    start = key.end() - 1
    depth = 0
    in_string = False
    for index in range(start, end_of_table):
        char = text[index]
        if char == '"' and text[index - 1] != "\\":
            in_string = not in_string
        elif not in_string and char == "[":
            depth += 1
        elif not in_string and char == "]":
            depth -= 1
            if depth == 0:
                return start, index + 1
    return None


def clear_dependencies() -> None:
    """Empty the package list in developer_settings.py (and pyproject.toml)."""
    from backend.DONT_CHANGE.scripts.config import set_list_setting

    if set_list_setting("packages", []):
        print('[Info] Emptied "packages" in developer_settings.py.')
    reconcile_pyproject(settings())


# ---------------------------------------------------------------- venv


def read_venv_config(venv_dir: str = VENV_DIR) -> dict:
    values = {}
    try:
        with open(os.path.join(venv_dir, "pyvenv.cfg"), encoding="utf-8") as stream:
            for line in stream:
                if "=" in line:
                    key, value = line.split("=", 1)
                    values[key.strip().lower()] = value.strip()
    except OSError:
        pass
    return values


def venv_version(config: dict) -> tuple | None:
    text = config.get("version_info") or config.get("version") or ""
    numbers = re.findall(r"\d+", text)
    return tuple(int(n) for n in numbers[:3]) if len(numbers) >= 2 else None


def venv_home_valid(config: dict) -> bool:
    home = config.get("home", "")
    return bool(home) and os.path.isfile(os.path.join(home, "python.exe"))


def venv_base_executable(venv_dir: str = VENV_DIR) -> str | None:
    """The base interpreter the venv's python.exe really starts, or None if it cannot start.

    uv venvs on Windows can store the base path inside Scripts\\python.exe itself, so
    pyvenv.cfg alone does not show whether a moved project still works.
    """
    exe = os.path.join(venv_dir, "Scripts", "python.exe")
    try:
        output = subprocess.check_output(
            [exe, "-I", "-S", "-X", "utf8", "-c", "import sys; print(getattr(sys, '_base_executable', sys.executable))"],
            universal_newlines=True,
            encoding="utf-8",
            stderr=subprocess.DEVNULL,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    base = output.strip()
    return base if os.path.isfile(base) else None


def _same_file(first: str, second: str) -> bool:
    return os.path.normcase(os.path.realpath(first)) == os.path.normcase(os.path.realpath(second))


def venv_needs_relink(config: dict, base_python: str) -> bool:
    """True if the venv points at a missing or different base interpreter than the project's Python."""
    if not venv_home_valid(config):
        return True
    base = venv_base_executable()
    return base is None or not _same_file(base, base_python)


def relink_venv(base_python: str, s=None) -> bool:
    """Point an existing venv at base_python (moved project, portable copy), keeping its packages."""
    previous = read_venv_config().get("home", "?")
    code = run_uv(["venv", "--allow-existing", "--relocatable", "--quiet", "--python", base_python, VENV_DIR], check=False, s=s)
    # uv caches interpreter details keyed on python.exe's timestamp, which the re-link does not
    # change; without a new timestamp uv would keep using the old base and rebuild the venv.
    for name in ("python.exe", "pythonw.exe"):
        try:
            os.utime(os.path.join(VENV_DIR, "Scripts", name), None)
        except OSError:
            pass
    base = venv_base_executable()
    if code or base is None or not _same_file(base, base_python):
        return False
    print(f'[Info] Re-linked the environment to "{os.path.dirname(base_python)}" (was "{previous}"), e.g. after moving the project.')
    return True


def refuse_mutation_while_running() -> None:
    """Running app instances lock files inside the environment."""
    from backend.DONT_CHANGE.scripts.runtime_state import ProcessRegistry

    records, _ = ProcessRegistry(PROCESS_ID_FILE_PATH).records()
    if records:
        raise SetupError("Close the running app instance(s) first; they use the files in the Python environment.")


def _quiet_attempt(arguments, project_environment=None, s=None) -> bool:
    """Try a uv command without printing anything (used for offline-first attempts)."""
    code, _, _ = run_uv(arguments, capture=True, check=False, project_environment=project_environment, s=s)
    return code == 0


def ensure_lock(s=None) -> None:
    """Create or update uv.lock when pyproject.toml changed (offline first)."""
    if os.path.isfile(UV_LOCK_PATH) and _quiet_attempt(["lock", "--check", "--offline"], s=s):
        return
    print("[Setup] Updating uv.lock for the declared dependencies...")
    if _quiet_attempt(["lock", "--offline"], s=s):
        return
    if not downloads_allowed(s):
        raise SetupError("uv.lock needs an update that requires internet, but downloads at launch are disabled (allow_downloads_at_launch = False).")
    run_uv(["lock"], s=s)


def sync(python_exe: str, *, venv_dir: str = VENV_DIR, exact: bool = False, s=None) -> None:
    """Install exactly what uv.lock says (offline first, then online if allowed)."""
    arguments = ["sync", "--locked", "--python", python_exe]
    if not exact:
        arguments.append("--inexact")  # keep packages added by hand (uv pip install) until the next exact sync
    project_environment = None if os.path.normcase(venv_dir) == os.path.normcase(VENV_DIR) else venv_dir
    if _quiet_attempt(arguments + ["--offline"], project_environment=project_environment, s=s):
        return
    if not downloads_allowed(s):
        raise SetupError("Installing the locked packages needs internet, but downloads at launch are disabled (allow_downloads_at_launch = False).")
    show_console()
    print("[Setup] Installing packages...")
    run_uv(arguments, project_environment=project_environment, s=s)


def best_effort_install(python_exe: str, s=None) -> None:
    """For a Python outside requires-python: install the declared dependencies without the lock."""
    if not declared_dependencies():
        return
    if not _quiet_attempt(["pip", "install", "--python", python_exe, "-r", PYPROJECT_PATH, "--offline"], s=s) and downloads_allowed(s):
        run_uv(["pip", "install", "--python", python_exe, "-r", PYPROJECT_PATH], s=s)


def create_venv(base_python: str, venv_dir: str, s=None) -> None:
    run_uv(["venv", "--relocatable", "--quiet", "--python", base_python, venv_dir], s=s)


def build_venv(base_python: str, *, locked: bool = True, s=None) -> None:
    """Build a new venv beside the old one, fill it, then swap it in (the old one stays until then)."""
    staging = VENV_DIR + ".staging-" + uuid.uuid4().hex[:8]
    try:
        show_console()
        print(f"[Setup] Creating the app environment for Python {version_text(interpreter_version(base_python))}...")
        create_venv(base_python, staging, s)
        staged_python = os.path.join(staging, "Scripts", "python.exe")
        if locked:
            sync(staged_python, venv_dir=staging, exact=True, s=s)
        else:
            best_effort_install(staged_python, s)
        swap_in_venv(staging)
    finally:
        if os.path.isdir(staging):
            shutil.rmtree(staging, ignore_errors=True)


def swap_in_venv(staging: str) -> None:
    previous = VENV_DIR + ".previous-" + uuid.uuid4().hex[:8]
    if os.path.isdir(VENV_DIR):
        os.rename(VENV_DIR, previous)
    try:
        os.rename(staging, VENV_DIR)
    except OSError:
        if os.path.isdir(previous):
            os.rename(previous, VENV_DIR)
        raise
    if os.path.isdir(previous):
        shutil.rmtree(previous, ignore_errors=True)
        if os.path.isdir(previous):
            print_warn(f'[Warning] The old environment could not be deleted completely: "{previous}"')


# ---------------------------------------------------------------- main entry


def ensure_environment(interactive: bool = True, purpose: str = "launch") -> AppPython:
    """Validate settings and make sure the app's interpreter and packages are ready."""
    s = settings()
    validate(s)
    base_python = sys.executable
    if s.package_environment == "interpreter_site_packages":
        return AppPython(base_python, [], "interpreter")

    with FileLock(ENVIRONMENT_LOCK_PATH, timeout=600):
        base_version = interpreter_version(base_python)
        any_version = s.python_source == "system_default_any_version"
        file_request = read_python_version_file()

        if file_request is None:
            # First run: the bootstrap resolved the launcher Python from python_version.
            # An empty python_version keeps the newest Python chosen now ("pick once").
            request = s.python_version or ".".join(str(n) for n in base_version[:2])
            write_python_version_file(request)
        elif not any_version and not request_matches(s.python_version, file_request):
            switched = handle_version_change(file_request, s, interactive)
            if switched:
                return AppPython(VENV_PYTHON_EXE, ["-E", "-s"], "venv")
        # pyproject.toml follows developer_settings.py ("packages"); requires-python follows the project's Python.
        s = reconcile_pyproject(s, None if current_requires_python() else base_version)

        locked = version_satisfies_requires(base_version, current_requires_python())
        if not locked:
            print_warn(
                f"[Warning] Python {version_text(base_version)} is outside requires-python ({current_requires_python()}); "
                "installing the declared dependencies without the lock file."
            )
        if locked:
            ensure_lock(s)

        config = read_venv_config()
        if not os.path.isfile(VENV_PYTHON_EXE) or not config:
            build_venv(base_python, locked=locked, s=s)
        else:
            if (venv_version(config) or ())[:2] == base_version[:2] and venv_needs_relink(config, base_python):
                # The project (or its Python) moved: re-link instead of reinstalling (works offline).
                if not relink_venv(base_python, s):
                    build_venv(base_python, locked=locked, s=s)
                elif locked:
                    sync(VENV_PYTHON_EXE, s=s)
            elif (venv_version(config) or ())[:2] != base_version[:2]:
                print(f"[Info] The environment uses Python {version_text(venv_version(config) or ())}; rebuilding it for Python {version_text(base_version)}.")
                build_venv(base_python, locked=locked, s=s)
            elif locked:
                sync(VENV_PYTHON_EXE, s=s)
            else:
                best_effort_install(VENV_PYTHON_EXE, s)
    return AppPython(VENV_PYTHON_EXE, ["-E", "-s"], "venv")


def handle_version_change(current: str, s, interactive: bool) -> bool:
    """python_version differs from the Python the project uses. Returns True after a switch."""
    wanted = s.python_version
    show_console()
    print()
    print_warn(f"python_version in developer_settings.py is {describe_python_request(wanted)}, but this project uses Python {current} (backend\\.python-version).")
    choices = [
        f"Switch to Python {wanted}; re-lock, keeping package versions where possible",
        f"Switch to Python {wanted}; re-lock and upgrade all packages",
        f"Switch to Python {wanted} with an empty package list (empties packages in developer_settings.py)",
        f"Keep Python {current} for this launch (ask again next time)",
        f'Keep Python {current} and set python_version = "{current}" in developer_settings.py',
        "Cancel this launch",
    ]
    for index, label in enumerate(choices, 1):
        print(f"  {index}: {label}")
    if not interactive or sys.stdin is None:
        raise SetupError("python_version changed; run a launch with a terminal or the change_python dev tool to choose how to switch.")
    while True:
        try:
            answer = input_warn(f"Choose an option [1-{len(choices)}]: ").strip()
        except EOFError:
            raise SetupError("python_version changed, but no answer could be read; run the change_python dev tool.") from None
        if answer in {str(i) for i in range(1, len(choices) + 1)}:
            break
    answer = int(answer)
    if answer == 6:
        raise LaunchCancelled()
    if answer == 4:
        return False
    if answer == 5:
        for line in edit_settings({"python_version": current}):
            print(line)
        return False
    if answer == 3 and input_warn('This empties "packages" in developer_settings.py. Type yes to continue: ').strip().lower() != "yes":
        raise LaunchCancelled()
    switch_python(wanted, upgrade=answer == 2, clear=answer == 3, s=s)
    return True


def switch_python(request: str, *, upgrade=False, clear=False, s=None) -> None:
    """Move the project to another Python; restores all files if anything fails."""
    s = s or settings()
    refuse_mutation_while_running()
    new_python = find_or_install_python(request, s)
    new_version = interpreter_version(new_python)
    backups = {}
    for path in (PYPROJECT_PATH, UV_LOCK_PATH, PYTHON_VERSION_FILE, DEV_SETTINGS_PATH):
        try:
            with open(path, "rb") as stream:
                backups[path] = stream.read()
        except OSError:
            backups[path] = None
    try:
        write_python_version_file(request)
        set_requires_python(new_version)
        if clear:
            clear_dependencies()
        print(f"[Setup] Re-locking dependencies for Python {version_text(new_version)}...")
        lock_arguments = ["lock"] + (["--upgrade"] if upgrade else [])
        if not _quiet_attempt(lock_arguments + ["--offline"], s=s):
            run_uv(lock_arguments, s=s)
        build_venv(new_python, locked=True, s=s)
    except BaseException:
        for path, content in backups.items():
            if content is None:
                if os.path.exists(path):
                    os.remove(path)
            else:
                with open(path, "wb") as stream:
                    stream.write(content)
        sys.modules.pop("backend.developer_settings", None)
        print_warn("[Error] Switching Python failed; the previous Python, environment and files were kept.")
        raise
    invalidate_runtime_cache()
    print(f"[Success] The project now uses Python {version_text(new_version)}.")


# ---------------------------------------------------------------- package actions


def add_packages(names, s=None) -> None:
    """uv add (resolves, locks, installs), then record the result in developer_settings.py."""
    reconcile_pyproject(s)
    run_uv(["add", *names], s=s)
    reconcile_pyproject()


def remove_packages(names, s=None) -> None:
    """uv remove, then record the result in developer_settings.py."""
    reconcile_pyproject(s)
    run_uv(["remove", *names], s=s)
    reconcile_pyproject()


def install_without_recording(names, python_exe: str, s=None) -> None:
    """Install into an environment without recording it in developer_settings.py (uv pip install)."""
    run_uv(["pip", "install", "--python", python_exe, *names], s=s)


def app_python_for_tools() -> str:
    """Interpreter whose packages the dev tools change."""
    s = settings()
    if s.package_environment == "interpreter_site_packages":
        return sys.executable
    return VENV_PYTHON_EXE


def open_package_terminal(s=None) -> int:
    """Open a command prompt with the app environment activated and uv on PATH; wait for exit."""
    s = s or settings()
    env = uv_environment(s, python_command=False)
    python = app_python_for_tools()
    scripts = os.path.dirname(python) if s.package_environment == "interpreter_site_packages" else os.path.join(VENV_DIR, "Scripts")
    extra = [scripts, os.path.dirname(uv_exe())]
    if s.package_environment == "interpreter_site_packages":
        extra.append(os.path.join(os.path.dirname(python), "Scripts"))
    else:
        env["VIRTUAL_ENV"] = VENV_DIR
    env["UV_PROJECT"] = PROJECT_DIR  # uv add/remove/lock work from the code folder too
    env["PATH"] = os.pathsep.join(extra + [env.get("PATH", "")])
    env["PROMPT"] = "(app packages) $P$G"
    lines = [
        "echo.",
        "echo Package terminal for this app. Python: " + python,
        "echo   uv add NAME          add a package and install it (copied into developer_settings.py on the next start)",
        "echo   uv remove NAME       remove a package",
        "echo   uv lock --upgrade    upgrade all packages, then: uv sync",
        "echo   uv pip list          show installed packages",
        "echo   uv pip install NAME  install without recording it (next exact sync removes it)",
        "echo   python ...           run this Python",
        "echo   exit                 close this terminal",
        "echo.",
    ]
    if s.package_environment == "interpreter_site_packages":
        lines.insert(2, "echo   Note: this changes the selected interpreter's own packages; use: uv pip install --python python NAME")
    return subprocess.run(["cmd.exe", "/d", "/k", " & ".join(lines)], cwd=PYTHON_SCRIPTS_DIR, env=env).returncode


def ensure_valid_settings() -> None:
    """Raise SettingsError with readable messages (used by tools before doing work)."""
    validate(settings())


__all__ = [
    "AppPython",
    "LaunchCancelled",
    "SettingsError",
    "SetupError",
    "ensure_environment",
]
