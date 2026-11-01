"""Manage the frontend runtime, dependency state, repair menus and package tools."""

# =========================

import os
import sys

# =========================
# add root dir for debug cases where this script is called on its own:
ROOT_DIR: str = os.path.normpath(os.path.dirname(__file__) + "\\..\\..\\..")
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
# =========================

from functools import wraps
from pathlib import Path

from backend.developer_settings import (
    install_tests,
    install_tkinter,
    install_tools,
    python_version,
    use_uv_to_install_packages,
)
from backend.DONT_CHANGE.scripts.console_tools import input_warn, print_warn
from backend.DONT_CHANGE.scripts.environment_state import (
    packages_healthy,
    replace_directory,
    requirements_fingerprint,
    runtime_healthy,
    stage_directory,
    write_package_state,
)
from backend.DONT_CHANGE.scripts.filesystem_tools import delete_folder_safe, read_lines, write_lines
from backend.DONT_CHANGE.scripts.launcher_ui import (
    get_running_processes_from_pid_file,
    set_hidden_in_explorer,
    set_terminal_appearance_once,
)
from backend.DONT_CHANGE.scripts.package_tools import (
    get_installed_packages,
    install_packages,
    save_installed_packages,
    save_requirements_of_folder_noVersion,
    save_requirements_of_folder_withVersion,
)
from backend.DONT_CHANGE.scripts.python_runtime import (
    configure_python_package_path,
    install_full_python,
    is_python_version_compatible,
)
from backend.DONT_CHANGE.scripts.python_runtime import (
    get_python_version as _get_python_version,
)
from backend.DONT_CHANGE.scripts.runtime_state import (
    FileLock,
    atomic_json,
    clean_python_environment,
)
from backend.DONT_CHANGE.settings.backend_settings import (
    BACKEND_DIR,
    BACKEND_PYTHON_EXE,
    CURRENT_PACKAGES_NO_VERSION_PATH,
    CURRENT_PACKAGES_WITH_VERSION_PATH,
    DEFAULT_PACKAGES_PATH,
    EXCLUDED_FOLDERS_FOR_PACKAGE_SEARCH,
    FRONTEND_LAUNCHER_FOR_PIP_INSTALL_TERMINAL,
    FRONTEND_PACKAGES_ARE_INSTALLED_MARKER_PATH,
    FRONTEND_PACKAGES_DIR,
    FRONTEND_PYTHON_DIR,
    FRONTEND_PYTHON_EXE,
    NEEDED_PACKAGES_NO_VERSION_PATH,
    NEEDED_PACKAGES_WITH_VERSION_PATH,
    PROCESS_ID_FILE_PATH,
    PYTHON_SCRIPTS_DIR,
    PYTHON_VERSION_INDICATOR_FILE_PATH,
    TEMPORARY_DIR,
    VARIABLE_IN_DEFAULT_PACKAGES_THAT_TRIGGERS_SEARCH_IF_TRUE,
)


def environment_locked(function):
    @wraps(function)
    def locked(*args, **kwargs):
        with FileLock(Path(TEMPORARY_DIR) / "environment.lock", timeout=600):
            return function(*args, **kwargs)

    return locked


def refuse_mutation_while_running():
    running, _ = get_running_processes_from_pid_file(PROCESS_ID_FILE_PATH)
    if running:
        raise RuntimeError("Close running application instances before changing their Python environment.")


def get_python_version() -> str:
    """Return the version reported by the managed frontend Python executable."""
    return _get_python_version(FRONTEND_PYTHON_EXE)


def read_python_version_from_file() -> str:
    return get_python_version()


def is_python_version_correct(target_version: str | float) -> tuple[bool, str | None]:
    """
    Returns whether the Python executable at ``exe_path`` matches ``target_version`` and the actual version:
        if target_version in [None, False, ""]:
            return [True,None]
        else:
            returns: [match,current_verison]

    Matching is prefix-based on proven version components:
    - If ``target_version`` is ``"3"``, any Python 3.x matches.
    - If ``target_version`` is ``"3.13"``, any Python 3.13.x matches.
    - If ``target_version`` is ``"3.13.2"``, only Python 3.13.2 matches.
    """
    if target_version in [None, False, ""]:
        return (True, None)

    if isinstance(target_version, (float, int)):
        target_version = str(target_version)

    found_version = read_python_version_from_file()

    return (is_python_version_compatible(found_version, target_version), found_version)


def delete_python_distro() -> None:
    """Safely remove and recreate the managed frontend Python directory."""
    refuse_mutation_while_running()
    deleted = delete_folder_safe(
        FRONTEND_PYTHON_DIR,
        always_prompt_for_confirmation=False,
        allowed_base_abs_path=PYTHON_SCRIPTS_DIR,
        expected_folder_name=None,
        required_included_files=None,
        required_included_dirs=None,
        require_direct_child_of_allowed_base=False,
        max_size_GB_before_prompt=1.2,
        min_path_depth=6,
    )
    if not deleted:
        raise RuntimeError("Python deletion cancelled")
    os.makedirs(FRONTEND_PYTHON_DIR, exist_ok=True)


def recreate_python_distro(keep_previous: bool = False) -> None:
    """Install a fresh managed frontend Python distribution and its helper launcher."""
    refuse_mutation_while_running()

    rel_path_dist_to_packages = os.path.relpath(path=FRONTEND_PACKAGES_DIR, start=FRONTEND_PYTHON_DIR)

    import json

    runtime_lock = Path(BACKEND_DIR) / "frontend-python.lock.json"
    requested = {
        "version": python_version,
        "tkinter": install_tkinter,
        "tests": install_tests,
        "tools": install_tools,
    }
    selected_version = python_version
    try:
        locked = json.loads(runtime_lock.read_text(encoding="utf-8"))
        if locked["requested"] == requested:
            selected_version = locked["resolved"]
    except (OSError, ValueError, KeyError):
        pass
    install_full_python(
        python_version=selected_version,
        keep_previous=keep_previous,
        python_dir_abs_path=FRONTEND_PYTHON_DIR,
        install_tkinter=install_tkinter,
        install_tests=install_tests,
        install_tools=install_tools,
        install_docs=False,
        rel_path_to_packages=rel_path_dist_to_packages,
    )

    if not os.path.exists(FRONTEND_PYTHON_EXE):
        raise RuntimeError(f'Python installation did not produce expected file at "{FRONTEND_PYTHON_EXE}"')
    else:
        # Create a batch file that launches a terminal that has python and pip install target set:
        batch_content = r"""
:: turn off command print and make variables local
@echo off & setlocal

:: settings (%~dp0 is file dir with "\" at end)
set "PYTHON_DIR=%~dp0.."
set "PACKAGES_TARGET=%~dp0..\..\packages"

:: local variables + resolve paths
for %%I in ("%PYTHON_DIR%") do set "PYTHON_DIR=%%~fI"
for %%I in ("%PACKAGES_TARGET%") do set "PACKAGES_TARGET=%%~fI"
set "PYTHON_EXE=%PYTHON_DIR%\python.exe"

:: create folder
if not exist "%PACKAGES_TARGET%" mkdir "%PACKAGES_TARGET%"

:: set global variables withing terminal to tell set python and package target and disable pip version check
set "PATH=%PYTHON_DIR%;%PYTHON_DIR%\Scripts;%PATH%"
set "PIP_TARGET=%PACKAGES_TARGET%"
set "PIP_DISABLE_PIP_VERSION_CHECK=1"
set "PYTHONPATH="
set "PYTHONHOME="
set "PYTHONNOUSERSITE=1"
set "PIP_CONFIG_FILE=NUL"

:: prints
echo Python exe:
echo "%PYTHON_EXE%"
echo Package install target:
echo "%PACKAGES_TARGET%"
echo.
echo Note: pip install commands in this terminal use the local package target. Install packages via "pip install {package-name}"
echo.

:: don't close terminal
cmd /k
"""
        os.makedirs(os.path.dirname(FRONTEND_LAUNCHER_FOR_PIP_INSTALL_TERMINAL), exist_ok=True)
        with open(FRONTEND_LAUNCHER_FOR_PIP_INSTALL_TERMINAL, "w", encoding="utf-8") as f:
            f.write(batch_content)

        # save python version to file to have version fast readable and to indicate successfull python setup:
        with open(PYTHON_VERSION_INDICATOR_FILE_PATH, "w", encoding="utf-8") as f:
            f.write(get_python_version())

        atomic_json(runtime_lock, {"requested": requested, "resolved": get_python_version()})
        set_hidden_in_explorer()


def prompt_for_distro_reinstall(msg: str = "Choose how to replace Python:"):
    print_warn(msg)
    choices = [
        "Keep current Python and packages",
        "Change Python; install declared default packages",
        "Change Python; use an empty package environment",
        "Change Python; re-resolve current package names",
        "Same as 3, then save resolved versions as defaults",
        "Change Python; review and install inferred imports",
        "Same as 5, then save resolved versions as defaults",
        "Change Python; preserve exact current package versions",
        "Cancel this launch",
    ]
    for index, label in enumerate(choices):
        print_warn(f"{index}: {label}")
    print("After a successful change this launch continues automatically. No second restart is needed.")
    while True:
        choice = input_warn("Choose an option [0-8]: ").strip()
        if choice in {str(i) for i in range(len(choices))}:
            return int(choice)
        print_warn("Enter a number from 0 to 8.")


def ensure_python_distro(
    check_auto_determine_flag_for_default_package_install: bool = True,
    used_appid_if_slow: str = "",
):
    """Probe the actual runtime and roll back version changes if package setup fails."""
    import shutil

    actual = runtime_healthy(FRONTEND_PYTHON_EXE, install_tkinter)
    if actual and (not python_version or is_python_version_compatible(actual, python_version)):
        configure_python_package_path(
            FRONTEND_PYTHON_DIR,
            os.path.relpath(FRONTEND_PACKAGES_DIR, FRONTEND_PYTHON_DIR),
        )
        return
    answer = 1
    if actual:
        answer = prompt_for_distro_reinstall(f"Configured Python {python_version}; installed Python {actual}.")
    if answer == 0:
        return
    if answer == 8:
        raise RuntimeError("Launch cancelled; current environment retained")
    if answer not in range(1, 8):
        raise ValueError(f"Invalid answer: {answer}")
    requirements = DEFAULT_PACKAGES_PATH
    if answer in (3, 4, 7):
        requirements = save_current_packages(with_version=answer == 7)
    elif answer in (5, 6):
        success, requirements = save_requirements_of_root_folder_noVersion()
        if not success:
            raise RuntimeError("Import inference failed; current environment retained")
        confirm_inferred_requirements(requirements)
    refuse_mutation_while_running()
    set_terminal_appearance_once(used_appid_if_slow)
    previous = Path(FRONTEND_PYTHON_DIR + ".previous")
    if previous.exists():
        raise RuntimeError("Inspect the retained runtime backup before retrying: " + str(previous))
    try:
        recreate_python_distro(keep_previous=True)
        if answer == 2:
            install_empty_packages()
        else:
            install_packages_from_file(requirements, replace=True, review_inferred=False)
    except BaseException:
        if previous.exists():
            failed = Path(FRONTEND_PYTHON_DIR + ".failed")
            if failed.exists():
                raise RuntimeError("A failed runtime remains; inspect " + str(failed))
            Path(FRONTEND_PYTHON_DIR).rename(failed)
            previous.rename(FRONTEND_PYTHON_DIR)
            shutil.rmtree(failed)
        raise
    if previous.exists():
        try:
            shutil.rmtree(previous)
        except OSError:
            print("[Warning] Previous runtime retained at " + str(previous))
    if answer in (4, 6):
        save_current_packages_as_default(auto_search_phrase_state=False, with_version=True)


def delete_frontend_packages():
    """Delete the packages."""
    refuse_mutation_while_running()
    deleted = delete_folder_safe(
        FRONTEND_PACKAGES_DIR,
        always_prompt_for_confirmation=False,
        allowed_base_abs_path=PYTHON_SCRIPTS_DIR,
        expected_folder_name=None,
        require_direct_child_of_allowed_base=False,
        max_size_GB_before_prompt=5.0,
        required_included_files=None,
        required_included_dirs=None,
        min_path_depth=6,
    )
    if not deleted:
        raise RuntimeError("Package deletion cancelled")
    os.makedirs(FRONTEND_PACKAGES_DIR, exist_ok=True)


def are_frontend_packages_installed() -> bool:
    return packages_healthy(
        FRONTEND_PACKAGES_DIR,
        os.path.basename(FRONTEND_PACKAGES_ARE_INSTALLED_MARKER_PATH),
        DEFAULT_PACKAGES_PATH,
        get_python_version(),
    )


def make_file_to_indicate_frontend_pckgs_installed():
    import subprocess

    subprocess.run(
        [FRONTEND_PYTHON_EXE, "-E", "-s", "-m", "pip", "check"],
        env=clean_python_environment(),
        check=True,
    )
    write_package_state(
        FRONTEND_PACKAGES_DIR,
        os.path.basename(FRONTEND_PACKAGES_ARE_INSTALLED_MARKER_PATH),
        DEFAULT_PACKAGES_PATH,
        get_python_version(),
    )
    atomic_json(
        Path(FRONTEND_PACKAGES_DIR) / "resolved-packages.json",
        {"python": get_python_version(), "packages": get_current_packages()},
    )


def ensure_frontend_packages(used_appid_if_slow: str = ""):
    ensure_python_distro(used_appid_if_slow=used_appid_if_slow)
    if not are_frontend_packages_installed():
        marker = Path(FRONTEND_PACKAGES_ARE_INSTALLED_MARKER_PATH)
        if marker.is_file() and not marker.read_text(encoding="utf-8").strip():
            print("[Info] Migrating legacy package state without removing manually installed packages.")
            install_packages_from_file(DEFAULT_PACKAGES_PATH, replace=False)
            return
        print("[Info] Dependencies changed or installation is incomplete; preparing a verified replacement.")
        install_default_packages(check_auto_determine_flag=True, app_id_for_slow=used_appid_if_slow)


def confirm_inferred_requirements(path):
    print("Inferred imports are suggestions. Check distribution names, optional imports and version constraints:")
    print(Path(path).read_text(encoding="utf-8"))
    if input_warn("Install this reviewed list? [y/N] ").strip().lower() not in {
        "y",
        "yes",
    }:
        raise RuntimeError("Dependency installation cancelled; existing environment retained")


def install_empty_packages():
    import tempfile

    with tempfile.TemporaryDirectory(prefix="pyapp_empty_") as directory:
        requirements = Path(directory) / "empty.txt"
        requirements.write_text("", encoding="utf-8")
        install_packages_from_file(str(requirements), replace=True)


def install_packages_from_file(
    path: str,
    no_cache: bool = False,
    app_id_for_slow: str = "",
    print_: bool = True,
    *,
    replace: bool = False,
    review_inferred: bool = True,
) -> None:
    """Install/validate a staging environment, then atomically publish its manifest."""
    import shutil
    import subprocess

    refuse_mutation_while_running()
    path = os.path.abspath(path)
    if not os.path.isfile(path):
        raise FileNotFoundError(path)
    if review_inferred and path in {
        os.path.abspath(NEEDED_PACKAGES_NO_VERSION_PATH),
        os.path.abspath(NEEDED_PACKAGES_WITH_VERSION_PATH),
    }:
        confirm_inferred_requirements(path)
    if print_:
        print(f"[Info] Preparing packages from {path}")
    if app_id_for_slow:
        set_terminal_appearance_once(app_id_for_slow)
    stage = stage_directory(FRONTEND_PACKAGES_DIR)
    try:
        if not replace and os.path.isdir(FRONTEND_PACKAGES_DIR):
            shutil.copytree(FRONTEND_PACKAGES_DIR, stage, dirs_exist_ok=True)
        (stage / os.path.basename(FRONTEND_PACKAGES_ARE_INSTALLED_MARKER_PATH)).unlink(missing_ok=True)
        actual = [line for line in read_lines(path) if line.strip() and not line.lstrip().startswith("#")]
        if actual:
            install_packages(
                python_exe=FRONTEND_PYTHON_EXE,
                requirements_file=path,
                target=str(stage),
                upgrade=True,
                no_cache=no_cache,
                use_uv=use_uv_to_install_packages,
                local_uv_python_exe=BACKEND_PYTHON_EXE,
            )
        # Check dependency consistency against the staged packages, excluding the old target.
        probe = "import os,sys,site; old=os.path.normcase(os.path.abspath(sys.argv[1])); sys.path[:]=[p for p in sys.path if os.path.normcase(os.path.abspath(p))!=old]; site.addsitedir(sys.argv[2]); from pip._internal.cli.main import main; sys.exit(main(['check']))"
        subprocess.run(
            [
                FRONTEND_PYTHON_EXE,
                "-E",
                "-s",
                "-c",
                probe,
                FRONTEND_PACKAGES_DIR,
                str(stage),
            ],
            env=clean_python_environment(),
            check=True,
        )
        write_package_state(
            stage,
            os.path.basename(FRONTEND_PACKAGES_ARE_INSTALLED_MARKER_PATH),
            DEFAULT_PACKAGES_PATH,
            get_python_version(),
        )
        frozen = subprocess.run(
            [
                FRONTEND_PYTHON_EXE,
                "-E",
                "-s",
                "-m",
                "pip",
                "freeze",
                "--path",
                str(stage),
            ],
            env=clean_python_environment(),
            capture_output=True,
            text=True,
            check=True,
        ).stdout.splitlines()
        atomic_json(
            stage / "resolved-packages.json",
            {"python": get_python_version(), "packages": frozen},
        )
        if replace and path == os.path.abspath(DEFAULT_PACKAGES_PATH):
            atomic_json(
                DEFAULT_PACKAGES_PATH + ".lock.json",
                {
                    "requirements": requirements_fingerprint(DEFAULT_PACKAGES_PATH),
                    "python": get_python_version(),
                    "packages": frozen,
                },
            )
        replace_directory(stage, FRONTEND_PACKAGES_DIR)
    finally:
        if stage.exists():
            shutil.rmtree(stage)


def install_default_packages(check_auto_determine_flag: bool, app_id_for_slow: str = ""):
    import json
    import tempfile

    if check_auto_determine_flag and get_auto_find_pckgs_phrase_state() is True:
        success, path = save_requirements_of_root_folder_noVersion()
        if not success:
            raise RuntimeError("Import inference failed")
        install_packages_from_file(path, replace=True, app_id_for_slow=app_id_for_slow)
        save_current_packages_as_default(auto_search_phrase_state=False)
        return
    try:
        lock = json.loads(Path(DEFAULT_PACKAGES_PATH + ".lock.json").read_text(encoding="utf-8"))
        locked = (
            lock["requirements"] == requirements_fingerprint(DEFAULT_PACKAGES_PATH)
            and lock["python"] == get_python_version()
        )
    except (OSError, ValueError, KeyError):
        locked = False
    if locked:
        with tempfile.TemporaryDirectory(prefix="pyapp_locked_") as directory:
            path = Path(directory) / "requirements.txt"
            path.write_text("\n".join(lock["packages"]) + "\n", encoding="utf-8")
            install_packages_from_file(str(path), replace=True, app_id_for_slow=app_id_for_slow)
    else:
        install_packages_from_file(DEFAULT_PACKAGES_PATH, replace=True, app_id_for_slow=app_id_for_slow)


def get_auto_find_pckgs_phrase_state() -> bool | None:
    """WIP"""
    if not os.path.exists(DEFAULT_PACKAGES_PATH):
        return None

    lines = read_lines(DEFAULT_PACKAGES_PATH)

    for line in lines:
        if VARIABLE_IN_DEFAULT_PACKAGES_THAT_TRIGGERS_SEARCH_IF_TRUE not in line:
            continue
        value = (
            line.replace(VARIABLE_IN_DEFAULT_PACKAGES_THAT_TRIGGERS_SEARCH_IF_TRUE, "")
            .replace("=", "")
            .replace("#", "")
            .strip()
            .lower()
        )
        if value == "true":
            return True
        if value == "false":
            return False
        return None
    return None


def get_current_packages(with_version: bool = True):
    """Return packages installed in the managed frontend Python environment."""
    return get_installed_packages(
        exe_path=FRONTEND_PYTHON_EXE,
        with_version=with_version,
        target=FRONTEND_PACKAGES_DIR,
    )


def save_requirements_of_root_folder_noVersion(
    output_path: str = NEEDED_PACKAGES_NO_VERSION_PATH,
) -> tuple[bool, str]:
    """Discover imports below the project root and save unpinned requirements."""
    return (
        save_requirements_of_folder_noVersion(
            target_folder=PYTHON_SCRIPTS_DIR,
            output_path=output_path,
            excluded_folders=EXCLUDED_FOLDERS_FOR_PACKAGE_SEARCH,
        ),
        output_path,
    )


def save_requirements_of_root_folder_withVersion(
    output_path: str = NEEDED_PACKAGES_WITH_VERSION_PATH,
) -> bool:
    """Discover imports below the project root and save version-pinned requirements."""
    ensure_python_distro()
    return save_requirements_of_folder_withVersion(
        target_folder=PYTHON_SCRIPTS_DIR,
        output_path=output_path,
        python_exe=FRONTEND_PYTHON_EXE,
        excluded_folders=EXCLUDED_FOLDERS_FOR_PACKAGE_SEARCH,
    )


def save_current_packages(output_path: str | None = None, with_version: bool = True):
    """Save packages installed in the frontend environment to a requirements file."""
    if output_path is None:
        if with_version:
            output_path = CURRENT_PACKAGES_WITH_VERSION_PATH
        else:
            output_path = CURRENT_PACKAGES_NO_VERSION_PATH

    return save_installed_packages(
        output_path=output_path,
        with_version=with_version,
        exe_path=FRONTEND_PYTHON_EXE,
        target=FRONTEND_PACKAGES_DIR,
    )


def save_current_packages_as_default(auto_search_phrase_state: bool | None = None, with_version: bool = True):
    """Save current frontend packages as the project's default package list."""
    if auto_search_phrase_state is None:
        auto_search_phrase_state = get_auto_find_pckgs_phrase_state()

    packages = get_current_packages(with_version=with_version)

    write_lines(
        DEFAULT_PACKAGES_PATH,
        [
            f"{VARIABLE_IN_DEFAULT_PACKAGES_THAT_TRIGGERS_SEARCH_IF_TRUE} = {auto_search_phrase_state}",
            "",
            *packages,
        ],
    )
    make_file_to_indicate_frontend_pckgs_installed()


for _name in (
    "ensure_frontend_packages",
    "ensure_python_distro",
    "recreate_python_distro",
    "delete_python_distro",
    "delete_frontend_packages",
    "install_packages_from_file",
    "install_default_packages",
    "install_empty_packages",
    "make_file_to_indicate_frontend_pckgs_installed",
    "save_current_packages_as_default",
    "save_current_packages",
):
    globals()[_name] = environment_locked(globals()[_name])
