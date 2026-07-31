"""Shared code in scripts that are run in Python backend of this PyApp-Template

Code here should raise an error instead of handling terminal closing or press-enter-to-exit logic.
Imports are mostly lazy because it is not clear what will be needed
"""

# =========================

import os
import sys

# =========================
# add root dir for debug cases where this script is called on its own:
root_dir: str = os.path.dirname(__file__) + "\\..\\..\\.."
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)
# =========================

from backend.developer_settings import (
    install_tests,
    install_tkinter,
    install_tools,
    program_name,
    python_version,
    terminal_bg_color,
    terminal_text_color,
    use_uv_to_install_packages,
)
from backend.DONT_CHANGE.scripts.generic_helpers import (
    can_reach_url,
    delete_folder_safe,
    get_installed_packages,
    input_warn,
    install_full_python,
    install_packages,
    is_process_running,
    is_python_version_compatible,
    print_warn,
    read_lines,
    save_installed_packages,
    save_requirements_of_folder_noVersion,
    save_requirements_of_folder_withVersion,
    set_terminal_app_id,
    set_terminal_icon,
    set_terminal_title,
    write_lines,
)
from backend.DONT_CHANGE.scripts.generic_helpers import get_python_version as _get_python_version
from backend.DONT_CHANGE.scripts.generic_helpers import set_terminal_colors as _set_terminal_colors
from backend.DONT_CHANGE.settings.backend_settings import (
    BACKEND_PYTHON_EXE,
    CURRENT_PACKAGES_NO_VERSION_PATH,
    CURRENT_PACKAGES_WITH_VERSION_PATH,
    DEFAULT_PACKAGES_PATH,
    DEV_SETTINGS_DIR,
    DEV_TOOLS_REFERAL_NOTE_PATH,
    EMPTY_ARG_INDICATOR,
    EXCLUDED_FOLDERS_FOR_PACKAGE_SEARCH,
    FRONTEND_LAUNCHER_FOR_PIP_INSTALL_TERMINAL,
    FRONTEND_PACKAGES_ARE_INSTALLED_MARKER_PATH,
    FRONTEND_PACKAGES_DIR,
    FRONTEND_PYTHON_DIR,
    FRONTEND_PYTHON_EXE,
    ICON_PATH,
    NEEDED_PACKAGES_NO_VERSION_PATH,
    NEEDED_PACKAGES_WITH_VERSION_PATH,
    PYTHON_SCRIPTS_DIR,
    PYTHON_VERSION_INDICATOR_FILE_PATH,
    VARIABLE_IN_DEFAULT_PACKAGES_THAT_TRIGGERS_SEARCH_IF_TRUE,
)

# =========================
# global variables

_TERMINAL_APPEARANCE_WAS_SET: bool = False

TERMINAL_COLORS: str = ""
if terminal_bg_color:
    TERMINAL_COLORS += terminal_bg_color
if terminal_text_color:
    TERMINAL_COLORS += terminal_text_color

# =========================
# general helper functions


def make_empty_args_safe(args: list[str | None]) -> list[str]:
    """Needed because passing empty args as "" in Windows can be flimsy -> replace "" with EMPTY_ARG_INDICATOR and decode in child.

    None get conveted to EMPTY_ARG_INDICATOR as well."""
    return [a if a not in ("", None) else EMPTY_ARG_INDICATOR for a in args]


# =========================
# colored print and input and prompt and general print related


def print_traceback(message: str = "") -> None:
    """Print a colored traceback and optionally wait for the user before the terminal closes."""

    # `rich` is installed into the managed backend Python, not this analyzer's environment.
    from rich.console import Console  # pyrefly: ignore [missing-import]
    from rich.traceback import Traceback  # pyrefly: ignore [missing-import]

    console = Console()

    exc_type, exc_value, traceback_ = sys.exc_info()

    print()
    print()
    print_warn("=" * 30)

    if message:
        print_warn(message)
        print("-" * 30)

    console.print(Traceback.from_exception(exc_type, exc_value, traceback_, show_locals=False))  # type:ignore

    print_warn("=" * 30)


# =========================
# terminal related


def set_terminal_appearance_once(app_id: str) -> None:
    """Apply terminal title, AppID, and icon once per process."""
    global _TERMINAL_APPEARANCE_WAS_SET

    if not _TERMINAL_APPEARANCE_WAS_SET:
        set_terminal_title(program_name)
        set_terminal_icon(ICON_PATH)

        if app_id:
            set_terminal_app_id(app_id)

        _TERMINAL_APPEARANCE_WAS_SET = True


def set_terminal_colors(colors: str | None = TERMINAL_COLORS) -> None:
    _set_terminal_colors(colors=colors)


# =========================
# path related/file name related


def get_log_folder_path(log_path: str | bool | None, is_relative_to_start_folder_if_relative: bool) -> str | None:
    """Converts log_path = None, False, "" to None. Converts datetime format. Converts relative path either relative to developer_settings.py or start folder (where the start shortcut is)."""

    assert log_path is not True, "True is not a valid value for the log path. Choose: (relative) path, None, or False."
    if log_path:
        if not os.path.isabs(log_path):
            if is_relative_to_start_folder_if_relative:
                log_path_resolved = os.path.normpath(os.path.join(os.getcwd(), log_path))
            else:
                log_path_resolved = os.path.normpath(os.path.join(DEV_SETTINGS_DIR, log_path))
        else:
            log_path_resolved = log_path

        log_folder_path_resolved = os.path.dirname(log_path_resolved)

        if "%" in log_folder_path_resolved:
            from datetime import datetime

            log_path_resolved = datetime.now().astimezone().strftime(log_folder_path_resolved)

        return log_folder_path_resolved
    else:
        return None


def get_log_path(log_path: str | bool | None, is_relative_to_start_folder_if_relative: bool) -> str:
    """Handles log paths: Converts None and False to "". Converts datetime format. Converts relative path either relative to developer_settings.py or start folder (where the start shortcut is)."""

    assert log_path is not True, "True is not a valid value for the log path. Choose: (relative) path, None, or False."
    if log_path:
        if not os.path.isabs(log_path):
            if is_relative_to_start_folder_if_relative:
                log_path_resolved = os.path.normpath(os.path.join(os.getcwd(), log_path))
            else:
                log_path_resolved = os.path.normpath(os.path.join(DEV_SETTINGS_DIR, log_path))
        else:
            log_path_resolved = log_path

        if "%" in log_path_resolved:
            from datetime import datetime

            log_path_resolved = datetime.now().astimezone().strftime(log_path_resolved)

        return log_path_resolved
    else:
        return ""


# =========================
# pid/process related


def get_running_processes_from_pid_file(pid_path: str) -> tuple[list[int], int]:
    """returns (running_process_ids, stale_count)"""

    if pid_path == "" or not os.path.exists(pid_path):
        return [], 0

    process_id_entries = _read_process_id_entries(pid_path)
    if not process_id_entries:
        os.remove(pid_path)
        return [], 0

    running_process_ids = []
    stale_count = 0
    seen_process_ids: set[int] = set()
    for process_id, _line in process_id_entries:
        if process_id in seen_process_ids:
            continue
        seen_process_ids.add(process_id)

        if is_process_running(process_id):
            running_process_ids.append(process_id)
        else:
            stale_count += 1

    non_empty_lines = [str(pid) for pid in running_process_ids if str(pid).strip()]
    if non_empty_lines:
        write_lines(pid_path, non_empty_lines)
    elif os.path.exists(pid_path):
        os.remove(pid_path)

    return running_process_ids, stale_count


def stop_processes_from_pid_file(pid_path: str) -> tuple[int, int, list[str]]:
    """returns (stopped_count, stale_count, failed_messages)"""
    import subprocess

    def _wait_until_process_stops(pid: int, timeout_seconds: float) -> bool:
        import time

        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            if not is_process_running(pid):
                return True
            time.sleep(0.1)
        return not is_process_running(pid)

    def _stop_process_tree(pid: int) -> str:
        """WIP"""
        if not is_process_running(pid):
            return ""
        cmd = ["taskkill", "/PID", str(pid), "/T"]
        try:
            graceful_result = subprocess.run(  # noqa:S603
                cmd,
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="oem",
                errors="replace",
            )

        except FileNotFoundError:
            import signal

            os.kill(pid, signal.SIGTERM)
            return ""

        graceful_output = (graceful_result.stdout or "").strip()
        if graceful_result.returncode == 0 and _wait_until_process_stops(pid, 2.0):
            return graceful_output

        if not is_process_running(pid):
            return graceful_output
        forced_result = subprocess.run(  # noqa:S603
            cmd + ["/F"],  # force
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="oem",
            errors="replace",
        )
        forced_output = (forced_result.stdout or "").strip()
        if forced_result.returncode == 0 or _wait_until_process_stops(pid, 2.0):
            return "\n".join(output for output in [graceful_output, forced_output] if output)

        detail = forced_output or graceful_output
        if detail:
            raise RuntimeError(detail)
        raise RuntimeError(f"taskkill failed with exit code {forced_result.returncode}")

    if pid_path == "" or not os.path.exists(pid_path):
        return 0, 0, []

    process_id_entries = _read_process_id_entries(pid_path)
    if not process_id_entries:
        os.remove(pid_path)
        return 0, 0, []

    lines_by_process_id: dict[int, list[str]] = {}
    for process_id, line in process_id_entries:
        lines_by_process_id.setdefault(process_id, []).append(line)

    failed_lines = []
    failed_messages = []
    stopped_count = 0
    stale_count = 0
    for process_id, lines in lines_by_process_id.items():
        if not is_process_running(process_id):
            stale_count += 1
            continue

        try:
            _stop_process_tree(process_id)
            stopped_count += 1
        except Exception as process_error:
            failed_lines.extend(lines)
            failed_messages.append(f"{process_id}: {process_error}")

    non_empty_lines = [l for l in failed_lines if l.strip()]
    if non_empty_lines:
        write_lines(pid_path, non_empty_lines)
    elif os.path.exists(pid_path):
        os.remove(pid_path)

    return stopped_count, stale_count, failed_messages


def _read_process_id_entries(path: str) -> list[tuple[int, str]]:
    lines = read_lines(path)

    out = []
    for line in lines:
        line = line.strip()
        if line != "":
            process_id_text = line.split(maxsplit=1)[0]
            try:
                out.append((int(process_id_text), line))
            except ValueError:
                pass
    return out


# =========================
# python version related


def get_python_version() -> str:
    return _get_python_version(FRONTEND_PYTHON_EXE)


def read_python_version_from_file() -> str:
    if not os.path.exists(PYTHON_VERSION_INDICATOR_FILE_PATH):
        print_warn(
            f'[Warning] missing file "{PYTHON_VERSION_INDICATOR_FILE_PATH}". Using fallback python version determination.'
        )
        return get_python_version()

    try:
        return read_lines(PYTHON_VERSION_INDICATOR_FILE_PATH)[0].strip()
    except Exception:
        print_warn("[Error] Failed to determine python version from file. Using Fallback determination.")
        return get_python_version()


def is_python_version_correct(target_version: str | float | int) -> tuple[bool, str | None]:
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


# =========================
# python distribution related


def delete_python_distro():
    delete_folder_safe(
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
    os.makedirs(FRONTEND_PYTHON_DIR, exist_ok=True)


def recreate_python_distro() -> None:
    delete_python_distro()

    rel_path_dist_to_packages = os.path.relpath(path=FRONTEND_PACKAGES_DIR, start=FRONTEND_PYTHON_DIR)

    install_full_python(
        python_version=python_version,
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
if defined PYTHONPATH (
    set "PYTHONPATH=%PACKAGES_TARGET%;%PYTHONPATH%"
) else (
    set "PYTHONPATH=%PACKAGES_TARGET%"
)

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


def prompt_for_distro_reinstall(msg: str = "Reinstall distro / recreate virtual environment?"):
    """
    Return int in prints below for cases in print:
        print("0: Leave current Python version and packages")
        print("1: Change Python version + Reset packages + Reinstall default packages")
        print("2: Change Python version + Reset packages + Don't install packages")
        print("3: Change Python version + Reset packages + Reinstall current packages")
        print("4: Change Python version + Reset packages + Reinstall current packages + set them default")
        print("5: Change Python version + Reset packages + Install auto-determined needed packages")
        print("6: Change Python version + Reset packages + Install auto-determined needed packages + set them default")
    """
    print_warn(msg)
    print()
    print_warn("0: Leave current Python version and packages")
    print_warn("1: Change Python version + Reset packages + Reinstall default packages")
    print_warn("2: Change Python version + Reset packages + Don't install packages")
    print_warn("3: Change Python version + Reset packages + Reinstall current packages")
    print_warn("4: Change Python version + Reset packages + Reinstall current packages + set them default")
    print_warn("5: Change Python version + Reset packages + Install auto-determined needed packages")
    print_warn("6: Change Python version + Reset packages + Install auto-determined needed packages + set them default")

    while True:
        choice = input_warn("Choose an option [0-6]: ").strip()

        if choice in {"0", "1", "2", "3", "4", "5", "6"}:
            return int(choice)

        print_warn("Invalid choice. Please enter 0, 1, 2, 3, 4, 5, or 6.")


def ensure_python_distro(
    check_auto_determine_flag_for_default_package_install: bool = True, used_appid_if_slow: str = ""
):
    """returns if python version is correct"""

    if not os.path.exists(FRONTEND_PYTHON_EXE):  # no python distro existing case:
        set_terminal_appearance_once(used_appid_if_slow)
        print("\n" * 5)
        print("[Info] Python distribution not found. Installing Python:")
        recreate_python_distro()

        if are_frontend_packages_installed() == True:
            print("Deleting packages because are not connected to a Python exe.")
            delete_frontend_packages()
        return

    else:  # alread existing python distro case:
        if python_version:
            matching, actual_version = is_python_version_correct(python_version)
        else:
            matching = True

        if matching == True:  # right python version case:
            return

        else:  # wrong python version case:
            if not are_frontend_packages_installed():
                recreate_python_distro()
                return

            else:
                answer = prompt_for_distro_reinstall(
                    f"[Warning] Python version in settings ({python_version}) is not matching the current one ({actual_version}). Please enter how to proceed:"  # type:ignore
                )

                if answer == 0:
                    return
                elif answer in [1, 2, 3, 4, 5]:
                    set_terminal_appearance_once(used_appid_if_slow)
                    recreate_python_distro()
                    if answer == 1:
                        delete_frontend_packages()
                        install_default_packages(
                            check_auto_determine_flag=check_auto_determine_flag_for_default_package_install
                        )
                    elif answer == 2:
                        delete_frontend_packages()
                    elif answer in [3, 4]:
                        p = save_current_packages(with_version=False)
                        delete_frontend_packages()
                        install_packages_from_file(p)
                        if answer == 4:
                            save_current_packages_as_default()
                    elif answer in [5, 6]:
                        delete_frontend_packages()
                        success, p = save_requirements_of_root_folder_noVersion()
                        if success == True:
                            install_packages_from_file(p)
                            if answer == 6:
                                save_current_packages_as_default()
                        else:
                            print(
                                "[Warning] Failed to auto determine needed packages (see above). Installing default packages instead:"
                            )
                            install_default_packages(check_auto_determine_flag=False)
                else:
                    raise ValueError(f"Invalid answer: {answer}")


# ========================
# package related


def delete_frontend_packages():
    """Delete the packages."""
    delete_folder_safe(
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
    os.makedirs(FRONTEND_PACKAGES_DIR, exist_ok=True)


def are_frontend_packages_installed() -> bool:
    """returns True if frontend packages are installed"""

    if not os.path.exists(FRONTEND_PACKAGES_DIR):
        return False
    else:
        num_elems = len(os.listdir(FRONTEND_PACKAGES_DIR))

        if num_elems == 0:
            return False
        elif num_elems == 1:
            if os.path.exists(FRONTEND_PACKAGES_ARE_INSTALLED_MARKER_PATH):
                return True
            else:
                return False
        else:
            return True


def ensure_frontend_packages(used_appid_if_slow: str = ""):
    ensure_python_distro(used_appid_if_slow=used_appid_if_slow)

    if not os.path.exists(FRONTEND_PACKAGES_DIR):  # packages folder not existing - case
        install_default_packages(check_auto_determine_flag=True, app_id_for_slow=used_appid_if_slow)

    else:  # packages folder existing - case
        if os.path.exists(FRONTEND_PACKAGES_ARE_INSTALLED_MARKER_PATH):
            return
        else:
            print("[Info] Resetting Python packages:")
            delete_frontend_packages()  # resetting packages
            install_default_packages(check_auto_determine_flag=True, app_id_for_slow=used_appid_if_slow)

    # create file to note where to change packages if missing
    if not os.path.exists(DEV_TOOLS_REFERAL_NOTE_PATH):
        open(DEV_TOOLS_REFERAL_NOTE_PATH, "w", encoding="utf-8").close()


def install_packages_from_file(
    path: str, no_cache: bool = False, app_id_for_slow: str = "", print_: bool = True
) -> None:
    """raises if failure"""

    os.makedirs(FRONTEND_PACKAGES_DIR, exist_ok=True)

    if not os.path.exists(path):
        raise FileNotFoundError(f'Package list not found: "{path}"')

    packages = read_lines(path)
    actual_packgages = [l for l in packages if (not l.strip().startswith("#") and l.strip() != "")]

    if print_:
        print()
        print(f'[Info] Package list file: "{path}"')
        if len(actual_packgages) > 0:
            print("-" * 20)
            print(*actual_packgages, sep="\n")
            print("-" * 20)
            print()
        else:
            print("[Info] No packages to install.")
            print("-" * 20)
            print()

    # create file to indicate frontend packages as installed. (Needed to differentiate 0 packages from not yet installed)
    open(FRONTEND_PACKAGES_ARE_INSTALLED_MARKER_PATH, "w", encoding="utf-8").close()

    if len(actual_packgages) == 0:
        return

    if app_id_for_slow:
        set_terminal_appearance_once(app_id_for_slow)

    try:
        install_packages(
            python_exe=FRONTEND_PYTHON_EXE,
            requirements_file=path,
            target=FRONTEND_PACKAGES_DIR,
            upgrade=True,
            no_cache=no_cache,
            use_uv=use_uv_to_install_packages,
            local_uv_python_exe=BACKEND_PYTHON_EXE,
        )
    except Exception as e:
        if not can_reach_url("https://pypi.org/simple/pip/", 5):
            raise RuntimeError(
                f"Failed to install packages because cannot reach PyPI. Check internet, firewall, proxy, or DNS.: {e}"
            ) from e
        else:
            raise RuntimeError(f"Failed to install packages: {e}") from e


def install_default_packages(check_auto_determine_flag: bool, app_id_for_slow: str = ""):
    if check_auto_determine_flag == True:
        if get_auto_find_pckgs_phrase_state() == True:
            set_terminal_appearance_once(app_id_for_slow)
            print(
                f'[Info] Found flag "{VARIABLE_IN_DEFAULT_PACKAGES_THAT_TRIGGERS_SEARCH_IF_TRUE} = True" in default packages file "{DEFAULT_PACKAGES_PATH}"'
            )
            print(
                "--> Auto determine needed packages & reset installed packages to them & set them as new defaults if success."
            )

            success, p = save_requirements_of_root_folder_noVersion()

            if success:
                install_packages_from_file(p)
                save_current_packages_as_default(auto_search_phrase_state=False)
                return
            else:
                raise RuntimeError("[Error] Failed to auto determine required Python packages.")
        else:
            install_packages_from_file(DEFAULT_PACKAGES_PATH, app_id_for_slow=app_id_for_slow)
    else:
        install_packages_from_file(DEFAULT_PACKAGES_PATH, app_id_for_slow=app_id_for_slow)


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
    return get_installed_packages(exe_path=FRONTEND_PYTHON_EXE, with_version=with_version)


def save_requirements_of_root_folder_noVersion(
    output_path: str = NEEDED_PACKAGES_NO_VERSION_PATH,
) -> tuple[bool, str]:
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
    ensure_python_distro()
    return save_requirements_of_folder_withVersion(
        target_folder=PYTHON_SCRIPTS_DIR, output_path=output_path, python_exe=FRONTEND_PYTHON_EXE
    )


def save_current_packages(output_path: str | None = None, with_version: bool = True):
    if output_path is None:
        if with_version:
            output_path = CURRENT_PACKAGES_WITH_VERSION_PATH
        else:
            output_path = CURRENT_PACKAGES_NO_VERSION_PATH

    return save_installed_packages(output_path=output_path, with_version=with_version, exe_path=FRONTEND_PYTHON_EXE)


def save_current_packages_as_default(auto_search_phrase_state: bool | None = None, with_version: bool = True):
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


# ========================
