import json
import os
import re
import sys
import tempfile
from collections.abc import Iterable

# add root dir for imports:
root_dir = os.path.dirname(__file__) + "\\..\\..\\.."
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from DONT_CHANGE.specific_scripts.common_code import (
    _run_python_exe,
    ensure_parent,
    ensure_python_distro_and_venv
)
from DONT_CHANGE.specific_scripts.common_variables import (
    excluded_folders_for_package_search,
    python_exe_path,
    python_scripts_dir,
)


def resolve_output_path(raw_path: str | None, default_path: str) -> str:
    if raw_path:
        path = raw_path.strip('"')
        if not os.path.isabs(path):
            path = os.getcwd()+"\\"+ path
        return os.path.normpath(os.path.abspath(path))
    return os.path.normpath(os.path.abspath(default_path))


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


def get_temp_python(temp_venv: str) -> str:
    return temp_venv+ "\\Scripts\\python.exe"


def create_temp_package_install_environment(python_executable: str) -> tuple[str, str]:
    import shutil  # lazy import because slow

    temp_venv = tempfile.mkdtemp(prefix="pyapp_template_package_pin_")
    try:
        _run_python_exe(python_executable, "-m", "venv", temp_venv)
        temp_python = get_temp_python(temp_venv)
        if not os.path.exists(temp_python):
            raise RuntimeError(f'Temporary environment did not create "{temp_python}"')
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
    _run_python_exe(
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
    result = _run_python_exe(temp_python, "-c", script, capture_output=True)
    data = json.loads(result.stdout or "{}")
    return {normalize_package_name(name): (name, version) for name, version in data.items()}


def pin_requirements_to_installed_versions(path: str, temp_python: str) -> None:
    with open(path,"r",encoding="utf8") as f:
        lines=f.readlines()
    requirements =[
        line.strip() for line in lines if line.strip() and not line.strip().startswith("#")
    ]
    if not requirements:
        return

    _run_python_exe(temp_python, "-m", "pip", "install", "-r", path, "--disable-pip-version-check")
    versions = installed_versions(temp_python)
    pinned = []
    for requirement in requirements:
        name = requirement_name(requirement)
        installed = versions.get(normalize_package_name(name))
        pinned.append(f"{installed[0]}=={installed[1]}" if installed else requirement)
    with open(path,"w",encoding="utf8") as f:
        f.writelines(pinned)


def save_required_packages(
    output_path: str,
    *,
    with_versions: bool,
    folder: str = python_scripts_dir,
    ignored_folders: Iterable[str] = excluded_folders_for_package_search,
) -> None:
    output_path = os.path.normpath(os.path.abspath(output_path))
    ensure_parent(output_path)
    print(f'[Info] Scanning Python imports in "{folder}"')
    run_pipreqs(
        sys.executable,
        folder=os.path.normpath(os.path.abspath(folder)),
        output_path=output_path,
        ignored_folders=ignored_folders,
    )

    if with_versions:
        import shutil  # lazy import because slow

        ensure_python_distro_and_venv()
        temp_venv, temp_python = create_temp_package_install_environment(python_exe_path)
        try:
            print("[Info] Installing detected packages in a temporary environment to pin versions.")
            pin_requirements_to_installed_versions(output_path, temp_python)
        finally:
            shutil.rmtree(temp_venv, ignore_errors=True)
    else:
        with open(output_path) as f:
            lines=f.readlines()
        
        
        lines = [
            line.strip()
            for line in lines
            if line.strip() and not line.strip().startswith("#")
        ]
        with open(output_path,"w",encoding="utf8") as f:
            f.writelines(lines)
