"""Define optional end-user settings; access them in main.py with ``import settings``."""

# Open this file in an editor when run directly (e.g. double-clicked in Explorer).
if __name__ == "__main__":
    import os
    import shutil
    import subprocess

    # VS Code if it is on PATH, otherwise Notepad. "code" is a .cmd file, so the command is one quoted string.
    editor = shutil.which("code") or "notepad.exe"
    subprocess.Popen(f'"{editor}" "{os.path.abspath(__file__)}"')  # noqa: S603 PTH100 RUF100
