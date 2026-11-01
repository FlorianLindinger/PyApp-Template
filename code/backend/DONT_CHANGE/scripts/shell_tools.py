"""Editor launch and network reachability helpers."""

import os


def can_reach_url(url: str, timeout_s: float = 5.0) -> bool:
    """Return True if the given URL can be reached."""
    import urllib.request

    try:
        request = urllib.request.Request(
            url,
            headers={"User-Agent": "url-reachable-check/1.0"},
        )

        with urllib.request.urlopen(request, timeout=timeout_s):
            return True

    except OSError:
        return False


def open_in_editor(path: str) -> None:
    """Open a file preferably in vscode with fallback in Windows notepad. Lazily imports shutil and subprocess."""

    import shutil
    import subprocess

    if not os.path.exists(path):
        raise FileNotFoundError(path)
    vscode_exe_path = shutil.which("code")
    if vscode_exe_path is not None:
        subprocess.Popen([vscode_exe_path, path])
    else:
        # Fallback
        subprocess.Popen(["notepad.exe", path])
