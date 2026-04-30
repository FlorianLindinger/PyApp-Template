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


# ==========================================================================
# code execution

pid_path = make_abs_path_relative_to_file(process_id_file_path, developer_settings_path)

if not os.path.exists(pid_path):
    print(f"[Info] No PID file found at {pid_path}.")
    print("This could mean it was already stopped via this script.")
    input("Press enter to exit")
    sys.exit(0)

try:
    with open(pid_path, encoding="utf-8") as f:
        pid = int(f.read().strip())
    try:
        stop_process_tree(pid)
        if os.path.exists(pid_path):
            os.remove(pid_path)
        print("[Success] Process stopped.")
        time.sleep(1)
        sys.exit(0)
    except PermissionError:
        print("PermissionError when trying to kill process. This could mean the program is no longer running anyway.")
        input("Press enter to exit.")
        sys.exit(0)
        
except Exception as e:
    print_traceback(f"[Error] Failed to stop process: {e}", add_press_enter_to_exit=True)
