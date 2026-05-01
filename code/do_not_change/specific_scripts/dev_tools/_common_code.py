import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Iterable

from do_not_change.specific_scripts.common_variables import (
    default_packages_file_path,
    developer_settings_path,
    excluded_folders_for_package_search,
    portable_python_installer_path,
    portable_venv_creator_path,
    py_env_folder_path,
    python_dist_path,
    python_exe_path,
    python_scripts_folder_path,
    relative_venv_to_python_dist,
    variable_in_default_packages_path_that_triggers_search_if_true,
    venv_dir_path,
)


def abs_norm(path: str) -> str:
    return os.path.normpath(os.path.abspath(path))


def join_path(*parts: str) -> str:
    return os.path.normpath(os.path.join(*parts))


class DevToolError(RuntimeError):
    pass


def format_command(command) -> str:
    if isinstance(command, (str, bytes)):
        return os.fsdecode(command)

    parts = []
    for part in command:
        text = os.fspath(part)
        if any(char.isspace() for char in text):
            text = f'"{text}"'
        parts.append(text)
    return " ".join(parts)


def run_command(
    command: list[str],
    *,
    cwd: str | None = None,
    check: bool = True,
    capture_output: bool = False,
    stdout=None,
    stderr=None,
) -> subprocess.CompletedProcess[str]:
    print(f"[Run] {format_command(command)}")
    return subprocess.run(
        command,
        cwd=cwd,
        check=check,
        capture_output=capture_output,
        stdout=stdout,
        stderr=stderr,
        text=True,
    )


def run_batch(batch_file: str, *args: object, check: bool = True) -> subprocess.CompletedProcess[str]:
    if not os.path.exists(batch_file):
        raise FileNotFoundError(f'Batch helper not found: "{batch_file}"')
    return run_command(["cmd", "/c", "call", batch_file, *[os.fspath(str(arg)) for arg in args]], check=check)


def venv_python_path() -> str:
    candidates = [
        join_path(venv_dir_path, "portable_Scripts", "python.bat"),
        join_path(venv_dir_path, "Portable_Scripts", "python.bat"),
    ]
    for candidate in candidates:
        if os.path.exists(candidate):
            return candidate
    return candidates[0]


def run_venv_python(
    *args: object,
    check: bool = True,
    capture_output: bool = False,
    stdout=None,
    stderr=None,
) -> subprocess.CompletedProcess[str]:
    python_bat = venv_python_path()
    if not os.path.exists(python_bat):
        raise FileNotFoundError(f'Virtual environment Python not found: "{python_bat}"')
    return run_command(
        ["cmd", "/c", "call", python_bat, *[os.fspath(str(arg)) for arg in args]],
        check=check,
        capture_output=capture_output,
        stdout=stdout,
        stderr=stderr,
    )


def run_python_exe(
    python_executable: str,
    *args: object,
    check: bool = True,
    capture_output: bool = False,
    stdout=None,
    stderr=None,
) -> subprocess.CompletedProcess[str]:
    return run_command(
        [python_executable, *[os.fspath(str(arg)) for arg in args]],
        check=check,
        capture_output=capture_output,
        stdout=stdout,
        stderr=stderr,
    )


def load_developer_settings():
    spec = importlib.util.spec_from_file_location("_pyapp_template_developer_settings", developer_settings_path)
    if spec is None or spec.loader is None:
        raise DevToolError(f'Could not load developer settings from "{developer_settings_path}"')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def ensure_python_distribution() -> None:
    if os.path.exists(python_exe_path):
        return

    settings = load_developer_settings()
    python_version = str(getattr(settings, "python_version", "") or "")
    install_tkinter = "1" if bool(getattr(settings, "install_tkinter", True)) else "0"
    install_tests = "1" if bool(getattr(settings, "install_tests", False)) else "0"
    install_tools = "1" if bool(getattr(settings, "install_tools", False)) else "0"

    print(f'[Info] Python distribution not found. Installing it into "{python_dist_path}".')
    run_batch(
        portable_python_installer_path,
        python_version,
        py_env_folder_path,
        install_tkinter,
        install_tests,
        install_tools,
        "0",
    )

    if not os.path.exists(python_exe_path):
        raise DevToolError(f'Portable Python installer did not create "{python_exe_path}"')


def recreate_venv() -> None:
    ensure_python_distribution()
    if os.path.exists(venv_dir_path):
        delete_folder_safe(
            venv_dir_path,
            allowed_base=python_scripts_folder_path,
            expected_name=os.path.basename(venv_dir_path),
        )

    run_batch(portable_venv_creator_path, py_env_folder_path, relative_venv_to_python_dist)

    if not os.path.exists(venv_python_path()):
        raise DevToolError(f'Virtual environment creator did not create "{venv_python_path()}"')


def ensure_venv() -> None:
    ensure_python_distribution()
    if not os.path.exists(venv_python_path()):
        recreate_venv()


def delete_folder_safe(target: str, *, allowed_base: str, expected_name: str) -> None:
    target_abs = abs_norm(target)
    base_abs = abs_norm(allowed_base)

    if os.path.basename(target_abs).lower() != expected_name.lower():
        raise DevToolError(f'Refusing to delete "{target_abs}" because its folder name is not "{expected_name}".')

    common = os.path.commonpath([target_abs, base_abs])
    if os.path.normcase(common) != os.path.normcase(base_abs):
        raise DevToolError(f'Refusing to delete "{target_abs}" because it is outside "{base_abs}".')

    if not os.path.exists(target_abs):
        return

    print(f'[Info] Deleting "{target_abs}"')
    shutil.rmtree(target_abs)
    if os.path.exists(target_abs):
        raise DevToolError(f'Failed to delete "{target_abs}"')


def ensure_parent(path: str) -> None:
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)


def resolve_output_path(raw_path: str | None, default_path: str) -> str:
    if raw_path:
        path = raw_path.strip('"')
        if not os.path.isabs(path):
            path = join_path(os.getcwd(), path)
        return abs_norm(path)
    return abs_norm(default_path)


def read_text(path: str) -> str:
    with open(path, encoding="utf-8", errors="replace") as file:
        return file.read()


def write_text(path: str, text: str) -> None:
    ensure_parent(path)
    with open(path, "w", encoding="utf-8") as file:
        file.write(text)


def has_installable_requirements(path: str) -> bool:
    for line in read_text(path).splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            return True
    return False


def install_requirements(path: str, *, upgrade: bool = True, no_cache: bool = True) -> None:
    if not os.path.exists(path):
        raise FileNotFoundError(f'Package list not found: "{path}"')

    print()
    print(f'[Info] Package list: "{path}"')
    if not has_installable_requirements(path):
        print("[Info] No packages to install.")
        return

    command: list[object] = ["-m", "pip", "install", "-r", path, "--disable-pip-version-check"]
    if upgrade:
        command.append("--upgrade")
    if no_cache:
        command.append("--no-cache-dir")
    run_venv_python(*command)


def read_default_auto_find_state() -> bool:
    if not os.path.exists(default_packages_file_path):
        return False

    for line in read_text(default_packages_file_path).splitlines():
        if variable_in_default_packages_path_that_triggers_search_if_true not in line:
            continue
        value = (
            line.replace(variable_in_default_packages_path_that_triggers_search_if_true, "")
            .replace("#", "")
            .replace("=", "")
            .strip()
            .lower()
        )
        if value == "true":
            return True
        if value == "false":
            return False
    return False


def write_lines(path: str, lines: Iterable[str], *, header: Iterable[str] = ()) -> None:
    path = abs_norm(path)
    ensure_parent(path)
    if os.path.exists(path):
        print(f'[Warning] Overwriting "{path}"')

    normalized_lines = [line.rstrip() for line in lines if line.strip()]
    content_lines = [line.rstrip() for line in header if line.strip()]
    content_lines.extend(sorted(dict.fromkeys(normalized_lines), key=str.lower))

    write_text(path, "\n".join(content_lines) + ("\n" if content_lines else ""))
    print(f'[Success] Wrote "{path}"')


def write_default_packages(lines: Iterable[str]) -> None:
    state = read_default_auto_find_state()
    write_lines(
        default_packages_file_path,
        lines,
        header=[f"{variable_in_default_packages_path_that_triggers_search_if_true} = {state}"],
    )


def get_freeze_lines() -> list[str]:
    ensure_venv()
    result = run_venv_python(
        "-m",
        "pip",
        "--disable-pip-version-check",
        "freeze",
        "--local",
        capture_output=True,
    )
    return [line.strip() for line in result.stdout.splitlines() if line.strip() and not line.startswith("#")]


def normalize_package_name(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def requirement_name(requirement: str) -> str:
    text = requirement.strip()
    if not text or text.startswith(("#", "-r ", "--")):
        return ""
    if text.startswith("-e "):
        text = text[3:].strip()
    if " @ " in text:
        text = text.split(" @ ", 1)[0].strip()
    else:
        for operator in ("===", "==", "~=", ">=", "<=", "!=", ">", "<"):
            if operator in text:
                text = text.split(operator, 1)[0].strip()
                break
    if "[" in text:
        text = text.split("[", 1)[0].strip()
    return text


def requirement_names_without_versions(requirements: Iterable[str]) -> list[str]:
    names = []
    for requirement in requirements:
        name = requirement_name(requirement)
        if name:
            names.append(name)
    return names


def save_current_packages(output_path: str, *, with_versions: bool) -> None:
    lines = get_freeze_lines()
    if not with_versions:
        lines = requirement_names_without_versions(lines)
    write_lines(output_path, lines)


def get_temp_python(temp_venv: str) -> str:
    return join_path(temp_venv, "Scripts", "python.exe")


def create_temp_package_install_environment(python_executable: str) -> tuple[str, str]:
    temp_venv = tempfile.mkdtemp(prefix="pyapp_template_package_pin_")
    try:
        run_python_exe(python_executable, "-m", "venv", temp_venv)
        temp_python = get_temp_python(temp_venv)
        if not os.path.exists(temp_python):
            raise DevToolError(f'Temporary environment did not create "{temp_python}"')
        return temp_venv, temp_python
    except Exception:
        shutil.rmtree(temp_venv, ignore_errors=True)
        raise


def run_pipreqs(
    python_executable: str,
    *,
    folder: str,
    output_path: str,
    ignored_folders: Iterable[str],
) -> None:
    if not os.path.exists(python_executable):
        raise FileNotFoundError(f'Python executable not found: "{python_executable}"')

    ignore_value = ",".join([*ignored_folders, ".git", ".hg", ".svn"])
    run_python_exe(
        python_executable,
        "-m",
        "pipreqs.pipreqs",
        folder,
        "--force",
        "--savepath",
        output_path,
        "--ignore",
        ignore_value,
        "--encoding",
        "utf-8",
        "--mode",
        "no-pin",
        "--no-follow-links",
    )


def installed_versions(temp_python: str) -> dict[str, tuple[str, str]]:
    script = (
        "import importlib.metadata as m, json; "
        "print(json.dumps({d.metadata['Name']: d.version for d in m.distributions()}))"
    )
    result = run_python_exe(temp_python, "-c", script, capture_output=True)
    data = json.loads(result.stdout or "{}")
    return {normalize_package_name(name): (name, version) for name, version in data.items()}


def pin_requirements_to_installed_versions(path: str, temp_python: str) -> None:
    requirements = [
        line.strip() for line in read_text(path).splitlines() if line.strip() and not line.strip().startswith("#")
    ]
    if not requirements:
        return

    run_python_exe(temp_python, "-m", "pip", "install", "-r", path, "--disable-pip-version-check")
    versions = installed_versions(temp_python)
    pinned = []
    for requirement in requirements:
        name = requirement_name(requirement)
        installed = versions.get(normalize_package_name(name))
        pinned.append(f"{installed[0]}=={installed[1]}" if installed else requirement)
    write_lines(path, pinned)


def save_required_packages(
    output_path: str,
    *,
    with_versions: bool,
    folder: str = python_scripts_folder_path,
    ignored_folders: Iterable[str] = excluded_folders_for_package_search,
) -> None:
    output_path = abs_norm(output_path)
    ensure_parent(output_path)
    print(f'[Info] Scanning Python imports in "{folder}"')
    run_pipreqs(
        sys.executable,
        folder=abs_norm(folder),
        output_path=output_path,
        ignored_folders=ignored_folders,
    )

    if with_versions:
        ensure_python_distribution()
        temp_venv, temp_python = create_temp_package_install_environment(python_exe_path)
        try:
            print("[Info] Installing detected packages in a temporary environment to pin versions.")
            pin_requirements_to_installed_versions(output_path, temp_python)
        finally:
            shutil.rmtree(temp_venv, ignore_errors=True)
    else:
        lines = [
            line.strip()
            for line in read_text(output_path).splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]
        write_lines(output_path, lines)
