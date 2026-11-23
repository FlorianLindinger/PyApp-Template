"""Keep automatic Windows idle timers awake only while the managed application runs.

Standalone: copy this file anywhere. Standard library only (ctypes); does nothing outside Windows.
"""

from __future__ import annotations

import ctypes
import os
from ctypes import wintypes

ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001
ES_DISPLAY_REQUIRED = 0x00000002


def set_awake(prevent_sleep: bool, keep_display_awake: bool) -> None:
    """Set/reset this thread's request; explicit Sleep, lid actions and policy still apply.

    Call from the same watchdog thread for acquisition and release. Thread/process exit also
    releases the request, including termination that cannot reach Python's finally blocks.
    """
    if os.name != "nt":
        return
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.SetThreadExecutionState.argtypes = [wintypes.DWORD]
    kernel.SetThreadExecutionState.restype = wintypes.DWORD
    flags = ES_CONTINUOUS
    if prevent_sleep:
        flags |= ES_SYSTEM_REQUIRED
    if keep_display_awake:
        flags |= ES_DISPLAY_REQUIRED
    if not kernel.SetThreadExecutionState(flags):
        raise ctypes.WinError(ctypes.get_last_error())
