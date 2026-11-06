"""Open files in an editor."""

from __future__ import annotations

import os

# Editors whose "code" command on PATH is a batch file next to the real executable.
_VSCODE_EXECUTABLES = ("Code.exe", "Code - Insiders.exe", "VSCodium.exe", "Cursor.exe")


def _editor_executable() -> str | None:
    """VS Code (or a fork) found via the "code" command, preferring the .exe over bin\\code.cmd."""
    import shutil

    found = shutil.which("code")
    if not found:
        return None
    if found.lower().endswith((".cmd", ".bat")):
        # bin\code.cmd sits one folder below Code.exe. Starting the .exe directly avoids
        # cmd.exe parsing the file path (a folder like "R&D" would otherwise break it).
        install_dir = os.path.dirname(os.path.dirname(os.path.abspath(found)))
        for name in _VSCODE_EXECUTABLES:
            candidate = os.path.join(install_dir, name)
            if os.path.isfile(candidate):
                return candidate
    return found


def open_in_editor(path: str) -> None:
    """Open a file preferably in VS Code with fallback in Windows notepad. Lazily imports subprocess."""
    import subprocess

    if not os.path.exists(path):
        raise FileNotFoundError(path)
    # The editor keeps running after the launcher; do not hand it the launcher's variables
    # (they would leak into its integrated terminals), or one that makes Code.exe act as Node.
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.upper().startswith("PYAPP_") and key.upper() != "ELECTRON_RUN_AS_NODE"
    }
    editor = _editor_executable()
    if editor is None:
        subprocess.Popen(["notepad.exe", path], env=env)
    elif editor.lower().endswith((".cmd", ".bat")):
        # Batch files run through cmd.exe: always quote, so & ( ) ^ in the path stay literal.
        subprocess.Popen(f'"{editor}" "{path}"', env=env)
    else:
        subprocess.Popen([editor, path], env=env)
