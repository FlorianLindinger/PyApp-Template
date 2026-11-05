"""Native-exit classification."""

from __future__ import annotations

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
