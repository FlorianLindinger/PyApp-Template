"""Send Ctrl+C to every process attached to another process's console.

Usage: python -I -S send_ctrl_c.py <pid>. Started by the Stop tool with DETACHED_PROCESS (no
console of its own), because a process can only send console control events to the console it
is attached to. Standard library only; exit code 0 = sent.
"""

import ctypes
import signal
import sys


def main() -> int:
    pid = int(sys.argv[1])
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    kernel.FreeConsole()
    if not kernel.AttachConsole(pid):
        return 2
    try:
        kernel.SetConsoleCtrlHandler(None, True)  # this helper ignores the event itself
        return 0 if kernel.GenerateConsoleCtrlEvent(0, 0) else 3  # CTRL_C_EVENT to the whole console
    finally:
        kernel.FreeConsole()


if __name__ == "__main__":
    sys.exit(main())
