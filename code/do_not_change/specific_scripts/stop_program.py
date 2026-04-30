# ==========================================================================
# package imports

import ctypes
import os
import signal
import subprocess
import sys
import time
from ctypes import wintypes

# ==========================================================================
# import from common variables and developer settings
from do_not_change.specific_scripts.common_variables import (
    developer_settings_path,
    print_traceback,
    process_id_file_path,
)

# ==========================================================================
# needed functions


def make_abs_path_relative_to_file(path, file):
    """makes a path absolute if relative with respect to the file (as if the file defined it)"""
    if not os.path.isabs(path):
        return os.path.normpath(os.path.dirname(file) + "\\" + path)
    else:
        return path


def process_is_running(pid: int) -> bool:
    if pid <= 0:
        return False

    try:
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
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if not process_is_running(pid):
            return True
        time.sleep(0.1)
    return not process_is_running(pid)


def taskkill(pid: int, *, force: bool):
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
    if os.name != "nt":
        os.kill(pid, signal.SIGTERM)
        return ""

    try:
        graceful_result = taskkill(pid, force=False)
    except FileNotFoundError:
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


# ==========================================================================
# code execution

pid_path = make_abs_path_relative_to_file(process_id_file_path, developer_settings_path)

if not os.path.exists(pid_path):
    print(f"[Info] No PID file found at {pid_path}.")
    print("This could mean it was already stopped via this script.")
    input("Press enter to exit")
    sys.exit(0)

try:
    process_id_entries = read_process_id_entries(pid_path)
    if not process_id_entries:
        os.remove(pid_path)
        print(f"[Info] No valid PID entries found at {pid_path}.")
        input("Press enter to exit")
        sys.exit(0)

    lines_by_process_id: dict[int, list[str]] = {}
    for process_id, line in process_id_entries:
        lines_by_process_id.setdefault(process_id, []).append(line)

    failed_lines = []
    failed_messages = []
    stopped_count = 0
    for process_id, lines in lines_by_process_id.items():
        try:
            stop_process_tree(process_id)
            stopped_count += 1
        except Exception as process_error:
            failed_lines.extend(lines)
            failed_messages.append(f"{process_id}: {process_error}")

    write_process_id_lines(pid_path, failed_lines)

    if failed_messages:
        raise RuntimeError("Failed to stop these PID(s):\n" + "\n".join(failed_messages))

    print(f"[Success] Stopped {stopped_count} process(es).")
    time.sleep(1)
    sys.exit(0)

except Exception as e:
    print_traceback(f"[Error] Failed to stop process: {e}", add_press_enter_to_exit=True)
