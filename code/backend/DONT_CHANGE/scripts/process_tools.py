"""Process-state and native-exit classification."""

from typing import Any


def exit_code_looks_like_interpreter_crash(exit_code: Any) -> bool:
    """
    Return whether a process return code matches a common Windows crash code.
    """
    if isinstance(exit_code, bool) or not isinstance(exit_code, int):
        return False

    # NTSTATUS values can arrive as signed or unsigned integers.
    windows_crash_codes = {
        0xC0000005,  # access violation
        0xC00000FD,  # stack overflow
        0xC000001D,  # illegal instruction
        0xC0000096,  # privileged instruction
        0xC0000409,  # stack buffer overrun
    }
    return exit_code & 0xFFFFFFFF in windows_crash_codes


def is_process_running(pid: int) -> bool:
    if pid <= 0:
        return False

    try:
        import ctypes
        from ctypes import wintypes

        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        STILL_ACTIVE = 259

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel32.OpenProcess.restype = wintypes.HANDLE
        kernel32.GetExitCodeProcess.argtypes = [
            wintypes.HANDLE,
            ctypes.POINTER(wintypes.DWORD),
        ]
        kernel32.GetExitCodeProcess.restype = wintypes.BOOL
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel32.CloseHandle.restype = wintypes.BOOL

        process_handle = kernel32.OpenProcess(
            PROCESS_QUERY_LIMITED_INFORMATION, False, pid
        )
        if not process_handle:
            return (
                ctypes.get_last_error() == 5
            )  # ERROR_ACCESS_DENIED means the process still exists.
        try:
            exit_code = wintypes.DWORD()
            if not kernel32.GetExitCodeProcess(process_handle, ctypes.byref(exit_code)):
                return False
            return exit_code.value == STILL_ACTIVE
        finally:
            kernel32.CloseHandle(process_handle)
    except Exception:
        return False
