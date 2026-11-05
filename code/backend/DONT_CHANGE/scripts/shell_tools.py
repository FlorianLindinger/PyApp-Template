"""Open files in an editor."""

from __future__ import annotations

import os


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
