import importlib.util
import os
import subprocess
import sys
from collections.abc import Iterable

from DONT_CHANGE.specific_scripts.common_variables import (
    default_packages_file_path,
    developer_settings_path,
    excluded_folders_for_package_search,
    portable_python_installer_path,
    portable_venv_creator_path,
    py_env_dir,
    python_dist_path,
    python_exe_path,
    python_scripts_dir,
    relative_py_env_to_python_dist,
    variable_in_default_packages_path_that_triggers_search_if_true,
    venv_dir_path,
    venv_exe_path,
)

# colored print and input

ANSI_WARN = "\x1b[1;37;41m"  # white text, red bg, bold
ANSI_SUCCESS = "\x1b[1;37;42m"  # white text, green bg, bold
ANSI_RESET = "\033[0m"


class CommonCodeError(RuntimeError):
    pass


def print_warn(msg, sep: str | None = " ", end: str | None = "\n"):
    print(f"{ANSI_WARN}{msg}{ANSI_RESET}", sep=sep, end=end)


def input_warn(msg):
    input(f"{ANSI_WARN}{msg}{ANSI_RESET}")


def input_success(msg):
    input(f"{ANSI_SUCCESS}{msg}{ANSI_RESET}")

def get_process_image_path(pid: int) -> str:
    if os.name != "nt" or pid <= 0:
        return ""

    try:
        import ctypes
        from ctypes import wintypes

        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel32.OpenProcess.restype = wintypes.HANDLE
        kernel32.QueryFullProcessImageNameW.argtypes = [
            wintypes.HANDLE,
            wintypes.DWORD,
            wintypes.LPWSTR,
            ctypes.POINTER(wintypes.DWORD),
        ]
        kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel32.CloseHandle.restype = wintypes.BOOL

        process_handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if not process_handle:
            return ""
        try:
            buffer_length = wintypes.DWORD(32768)
            buffer = ctypes.create_unicode_buffer(buffer_length.value)
            if not kernel32.QueryFullProcessImageNameW(process_handle, 0, buffer, ctypes.byref(buffer_length)):
                return ""
            return buffer.value
        finally:
            kernel32.CloseHandle(process_handle)
    except Exception:
        return ""


def terminate_parent_console_launcher_if_safe() -> bool:
    parent_pid = os.getppid()
    parent_image_path = get_process_image_path(parent_pid)
    parent_name = os.path.basename(parent_image_path).lower()
    if parent_name not in ("cmd.exe", "powershell.exe", "pwsh.exe"):
        return False

    import signal

    os.kill(parent_pid, signal.SIGTERM)
    return True


# colored traceback related
try:
    import rich.box
    import rich.console
    import rich.panel
    import rich.text
    import rich.traceback

    # enable colored traceback (needed especially before python 3.13)
    rich.traceback.install(show_locals=False)

    def print_traceback(message="Error", add_press_enter_to_exit=False) -> None:
        exc_type, exc_value, tb = sys.exc_info()
        if exc_type is None or exc_value is None:
            rich.console.Console().print(
                "[yellow][Warning] Running print_traceback function without active exception.[/yellow]"
            )
            if add_press_enter_to_exit:
                rich.console.Console().print("[red]Press enter to exit[/red]")
        else:
            panel = rich.panel.Panel(
                rich.traceback.Traceback.from_exception(
                    exc_type,
                    exc_value,
                    tb,
                    show_locals=False,
                ),
                title=rich.text.Text(message, style="bold red on white"),
                title_align="left",
                subtitle=rich.text.Text("Press Enter to exit", style="bold red on white")
                if add_press_enter_to_exit
                else None,
                subtitle_align="left",
                box=rich.box.HEAVY,
                border_style="bold red",
                padding=(1, 2),
                expand=False,
            )
            rich.console.Console().print(panel)

        if add_press_enter_to_exit:
            input()
            terminate_parent_console_launcher_if_safe()

except Exception:
    print(
        r'Failed during setup of rich traceback. Is "rich" package installed in the code\DONT_CHANGE\python_packages folder?'
    )
    print("Press enter to exit")
    input()
    os._exit(1)


def abs_norm(path: str) -> str:
    return os.path.normpath(os.path.abspath(path))


def join_path(*parts: str) -> str:
    return os.path.normpath(os.path.join(*parts))


def ensure_parent(path: str) -> None:
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)


def read_text(path: str) -> str:
    with open(path, encoding="utf-8", errors="replace") as file:
        return file.read()


def write_text(path: str, text: str) -> None:
    ensure_parent(path)
    with open(path, "w", encoding="utf-8") as file:
        file.write(text)


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
    return subprocess.run(  # noqa:S603
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


def make_abs_path_relative_to_file(path: str, file: str) -> str:
    if not os.path.isabs(path):
        return os.path.normpath(os.path.dirname(file) + "\\" + path)
    return path


def process_is_running(pid: int) -> bool:
    if pid <= 0:
        return False

    if os.name != "nt":
        try:
            os.kill(pid, 0)
        except OSError:
            return False
        return True

    try:
        import ctypes
        from ctypes import wintypes

        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        STILL_ACTIVE = 259

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel32.OpenProcess.restype = wintypes.HANDLE
        kernel32.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
        kernel32.GetExitCodeProcess.restype = wintypes.BOOL
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel32.CloseHandle.restype = wintypes.BOOL

        process_handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if not process_handle:
            return ctypes.get_last_error() == 5  # ERROR_ACCESS_DENIED means the process still exists.
        try:
            exit_code = wintypes.DWORD()
            if not kernel32.GetExitCodeProcess(process_handle, ctypes.byref(exit_code)):
                return False
            return exit_code.value == STILL_ACTIVE
        finally:
            kernel32.CloseHandle(process_handle)
    except Exception:
        return False


def wait_until_process_stops(pid: int, timeout_seconds: float) -> bool:
    import time

    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if not process_is_running(pid):
            return True
        time.sleep(0.1)
    return not process_is_running(pid)


def taskkill(pid: int, *, force: bool) -> subprocess.CompletedProcess[str]:
    cmd = ["taskkill", "/PID", str(pid), "/T"]
    if force:
        cmd.append("/F")
    return subprocess.run(  # noqa:S603
        cmd,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )


def stop_process_tree(pid: int) -> str:
    if not process_is_running(pid):
        return ""

    if os.name != "nt":
        import signal

        os.kill(pid, signal.SIGTERM)
        return ""

    try:
        graceful_result = taskkill(pid, force=False)
    except FileNotFoundError:
        import signal

        os.kill(pid, signal.SIGTERM)
        return ""

    graceful_output = (graceful_result.stdout or "").strip()
    if graceful_result.returncode == 0 and wait_until_process_stops(pid, 2.0):
        return graceful_output

    if not process_is_running(pid):
        return graceful_output

    forced_result = taskkill(pid, force=True)
    forced_output = (forced_result.stdout or "").strip()
    if forced_result.returncode == 0 or wait_until_process_stops(pid, 2.0):
        return "\n".join(output for output in [graceful_output, forced_output] if output)

    detail = forced_output or graceful_output
    if detail:
        raise RuntimeError(detail)
    raise RuntimeError(f"taskkill failed with exit code {forced_result.returncode}")


def parse_process_id_line(line: str) -> tuple[int, str] | None:
    stripped_line = line.strip()
    if stripped_line == "":
        return None

    process_id_text = stripped_line.split(maxsplit=1)[0]
    try:
        return int(process_id_text), line
    except ValueError:
        return None


def read_process_id_entries(path: str) -> list[tuple[int, str]]:
    entries = []
    with open(path, encoding="utf-8") as pid_file:
        for line in pid_file:
            entry = parse_process_id_line(line)
            if entry is not None:
                entries.append(entry)
    return entries


def write_process_id_lines(path: str, lines: list[str]) -> None:
    non_empty_lines = [line if line.endswith("\n") else line + "\n" for line in lines if line.strip()]
    if non_empty_lines:
        with open(path, "w", encoding="utf-8") as pid_file:
            pid_file.writelines(non_empty_lines)
    elif os.path.exists(path):
        os.remove(path)


def get_running_processes_from_pid_file(pid_path: str) -> tuple[list[int], int]:
    """returns (running_process_ids, stale_count)"""
    
    if pid_path == "" or not os.path.exists(pid_path):
        return [], 0

    process_id_entries = read_process_id_entries(pid_path)
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

        if process_is_running(process_id):
            running_process_ids.append(process_id)
        else:
            stale_count += 1

    write_process_id_lines(pid_path, [f"{process_id}\n" for process_id in running_process_ids])
    return running_process_ids, stale_count


def stop_processes_from_pid_file(pid_path: str) -> tuple[int, int, list[str]]:
    """returns (stopped_count, stale_count, failed_messages)"""
    if pid_path == "" or not os.path.exists(pid_path):
        return 0, 0, []

    process_id_entries = read_process_id_entries(pid_path)
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
        if not process_is_running(process_id):
            stale_count += 1
            continue

        try:
            stop_process_tree(process_id)
            stopped_count += 1
        except Exception as process_error:
            failed_lines.extend(lines)
            failed_messages.append(f"{process_id}: {process_error}")

    write_process_id_lines(pid_path, failed_lines)
    return stopped_count, stale_count, failed_messages


def venv_python_path() -> str:
    candidates = [
        venv_exe_path,
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


def load_developer_settings():
    spec = importlib.util.spec_from_file_location("_pyapp_template_developer_settings", developer_settings_path)
    if spec is None or spec.loader is None:
        raise CommonCodeError(f'Could not load developer settings from "{developer_settings_path}"')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _python_setup_values(
    python_version=None,
    install_tkinter=None,
    install_tests=None,
    install_tools=None,
) -> tuple[str, bool, bool, bool]:
    settings = None
    if None in (python_version, install_tkinter, install_tests, install_tools):
        settings = load_developer_settings()

    if python_version is None:
        python_version = getattr(settings, "python_version", "")
    if install_tkinter is None:
        install_tkinter = getattr(settings, "install_tkinter", True)
    if install_tests is None:
        install_tests = getattr(settings, "install_tests", False)
    if install_tools is None:
        install_tools = getattr(settings, "install_tools", False)

    if python_version in [None, False]:
        python_version = ""

    return str(python_version), bool(install_tkinter), bool(install_tests), bool(install_tools)


def check_python_version(target_version: str | float | int, exe_path: str = "py") -> bool:
    """
    Return whether the Python executable at ``exe_path`` matches ``target_version``.

    Matching is prefix-based on proven version components:
    - If ``target_version`` is ``"3"``, any Python 3.x matches.
    - If ``target_version`` is ``"3.13"``, any Python 3.13.x matches.
    - If ``target_version`` is ``"3.13.2"``, only Python 3.13.2 matches.
    """
    if target_version in [None, False, ""]:
        return True

    if isinstance(target_version, (float, int)):
        target_version = str(target_version)

    output = subprocess.check_output(  # noqa:S603
        [
            exe_path,
            "-c",
            "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')",
        ],
        stderr=subprocess.STDOUT,
        text=True,
    ).strip()

    actual_parts = output.split(".")
    target_parts = target_version.strip().split(".")

    if (len(actual_parts) != 3) or (any(not part.isdigit() for part in actual_parts)):
        raise ValueError(f"Could not determine Python version from output: {output}. Expected format like '3.13.2'.")

    if not target_parts or any(not part.isdigit() for part in target_parts):
        raise ValueError(
            f"Invalid target_version format: {target_version}. Must be a string like '3', '3.13', or '3.13.2'."
        )

    return actual_parts[: len(target_parts)] == target_parts


def format_bytes(num_bytes) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    size = float(num_bytes)
    for unit in units:
        if size < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{int(size)} {unit}"
            else:
                return f"{size:.2f} {unit}"
        size /= 1024
    return f"{num_bytes} B"


def get_folder_size(folder: str | os.PathLike[str]) -> int:
    total = 0
    for root, _dirs, files in os.walk(folder):
        for filename in files:
            path = os.path.join(root, filename)
            try:
                if os.path.isfile(path):
                    total += os.path.getsize(path)
            except (OSError, PermissionError):
                pass
    return total


def is_filesystem_root(path: str) -> bool:
    return os.path.abspath(path) == os.path.abspath(os.path.join(path, os.pardir))


def delete_folder_safe(
    target: str | os.PathLike[str],
    *,
    prompt_message="Delete this folder? [y/n]: ",
    allowed_base: str | os.PathLike[str],
    expected_name: str | None = None,
    prompt_for_confirmation=True,
) -> bool:
    import shutil  # lazy import because takes 0.2 s

    target_path = os.path.realpath(os.path.abspath(os.fspath(target)))
    base_path = os.path.realpath(os.path.abspath(os.fspath(allowed_base)))

    if not os.path.exists(target_path):
        return False

    if expected_name is not None and os.path.basename(target_path).lower() != expected_name.lower():
        raise CommonCodeError(f'Refusing to delete "{target_path}" because its folder name is not "{expected_name}".')

    if not os.path.exists(base_path):
        raise FileNotFoundError(f"Allowed base does not exist: {base_path}")

    if not os.path.isdir(base_path):
        raise NotADirectoryError(f"Allowed base is not a directory: {base_path}")

    if not os.path.isdir(target_path):
        raise NotADirectoryError(f"Target is not a directory: {target_path}")

    if is_filesystem_root(target_path):
        raise ValueError(f"Refusing to delete filesystem root: {target_path}")

    if os.path.normcase(target_path) == os.path.normcase(base_path):
        raise ValueError("Refusing to delete the allowed base directory itself")

    try:
        common_path = os.path.commonpath([base_path, target_path])
    except ValueError as exc:
        raise ValueError(
            f"Refusing to delete directory outside allowed base.\nTarget: {target_path}\nAllowed base: {base_path}"
        ) from exc

    if os.path.normcase(common_path) != os.path.normcase(base_path):
        raise ValueError(
            f"Refusing to delete directory outside allowed base.\nTarget: {target_path}\nAllowed base: {base_path}"
        )

    if prompt_for_confirmation:
        print()
        print("Folder deletion request:")
        print(f"Folder: {target_path}")
        print(f"Folder size: {format_bytes(get_folder_size(target_path))}")
        print()
        answer = input(prompt_message).strip().lower()
        if answer not in {"y", "yes"}:
            print("Cancelled folder deletion.")
            return False

    print(f'[Info] Deleting "{target_path}"')
    shutil.rmtree(target_path)
    if os.path.exists(target_path):
        raise CommonCodeError(f'Failed to delete "{target_path}"')
    return True


def delete_venv() -> bool:
    return delete_folder_safe(
        venv_dir_path,
        prompt_for_confirmation=False,
        allowed_base=python_scripts_dir,
        expected_name=os.path.basename(venv_dir_path),
    )


def delete_python_distro() -> bool:
    return delete_folder_safe(
        python_dist_path,
        prompt_for_confirmation=False,
        allowed_base=python_scripts_dir,
        expected_name=os.path.basename(python_dist_path),
    )


def create_portable_python(
    python_version=None,
    install_tkinter=None,
    install_tests=None,
    install_tools=None,
) -> None:
    python_version, install_tkinter, install_tests, install_tools = _python_setup_values(
        python_version,
        install_tkinter,
        install_tests,
        install_tools,
    )
    run_batch(
        portable_python_installer_path,
        python_version,
        py_env_dir,
        "1" if install_tkinter else "0",
        "1" if install_tests else "0",
        "1" if install_tools else "0",
        "0",
    )

    if not os.path.exists(python_exe_path):
        raise CommonCodeError(f'Portable Python installation did not produce expected file at "{python_exe_path}"')


def create_portable_venv() -> None:
    run_batch(portable_venv_creator_path, py_env_dir, relative_py_env_to_python_dist)

    if not os.path.exists(venv_python_path()):
        raise CommonCodeError(f'Portable virtual environment creator did not produce "{venv_python_path()}"')


def ensure_python_distribution(
    python_version=None,
    install_tkinter=None,
    install_tests=None,
    install_tools=None,
    *,
    reinstall_if_wrong_version=True,
) -> None:
    python_version, install_tkinter, install_tests, install_tools = _python_setup_values(
        python_version,
        install_tkinter,
        install_tests,
        install_tools,
    )

    if not os.path.exists(python_exe_path):
        print("\n" * 5)
        print("[Info] Python distribution not found. Installing portable Python and recreating virtual environment:")
        delete_python_distro()
        create_portable_python(python_version, install_tkinter, install_tests, install_tools)
        delete_venv()
        return

    if reinstall_if_wrong_version and python_version and not check_python_version(python_version, python_exe_path):
        print("\n" * 3)
        print(
            "Installed Python version does not match target version. "
            "Reinstalling Python distribution and recreating virtual environment:"
        )
        delete_python_distro()
        create_portable_python(python_version, install_tkinter, install_tests, install_tools)
        delete_venv()


def reinstall_python_distro_if_nonexistent_or_incorrect_version(
    python_version=None,
    install_tkinter=None,
    install_tests=None,
    install_tools=None,
) -> None:
    ensure_python_distribution(python_version, install_tkinter, install_tests, install_tools)
    if not os.path.exists(venv_python_path()):
        print("[Info] Virtual environment not found. Creating portable virtual environment:")
        delete_venv()


def recreate_portable_venv(
    python_version=None,
    install_tkinter=None,
    install_tests=None,
    install_tools=None,
) -> None:
    ensure_python_distribution(python_version, install_tkinter, install_tests, install_tools)
    delete_venv()
    create_portable_venv()


def recreate_venv() -> None:
    recreate_portable_venv()


def ensure_venv(
    python_version=None,
    install_tkinter=None,
    install_tests=None,
    install_tools=None,
) -> None:
    ensure_python_distribution(python_version, install_tkinter, install_tests, install_tools)
    if not os.path.exists(venv_python_path()):
        delete_venv()
        create_portable_venv()


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


def install_packages(path: str) -> None:
    install_requirements(path, upgrade=False, no_cache=False)


def read_search_phrase_state() -> bool | None:
    if not os.path.exists(default_packages_file_path):
        return None

    for line in read_text(default_packages_file_path).splitlines():
        if variable_in_default_packages_path_that_triggers_search_if_true not in line:
            continue
        value = (
            line.replace(variable_in_default_packages_path_that_triggers_search_if_true, "")
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


def read_default_auto_find_state() -> bool:
    return read_search_phrase_state() is True


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


def save_current_packages_as_default(search_phrase_state=None):
    if search_phrase_state is None:
        search_phrase_state = read_search_phrase_state()

    with open(default_packages_file_path, "w", encoding="utf-8") as file:
        file.write(f"{variable_in_default_packages_path_that_triggers_search_if_true} = {search_phrase_state}\n\n")
        file.flush()
        run_venv_python(
            "-m",
            "pip",
            "freeze",
            "--local",
            stdout=file,
            stderr=subprocess.PIPE,
        )


def save_requirements_of_root_folder_noVersion(output_path):
    searched_folder = python_scripts_dir
    excluded_folders = excluded_folders_for_package_search

    cmd = [
        sys.executable,
        "-m",
        "pipreqs.pipreqs",
        searched_folder,
        "--force",
        "--savepath",
        output_path,
        "--ignore",
        ",".join(excluded_folders),
        "--encoding",
        "utf-8",
        "--mode",
        "no-pin",
        "--no-follow-links",
    ]

    print()
    print("=" * 20)
    print("Start of finding required python packages")
    print("-" * 20)
    subprocess.run(cmd, check=True)  # noqa
    print("-" * 20)
    print(f'End of finding required python packages. Result: "{output_path}":\n')
    with open(output_path, encoding="utf-8") as file:
        contents = file.read()
    print(contents)
    print("=" * 20)
    print()
