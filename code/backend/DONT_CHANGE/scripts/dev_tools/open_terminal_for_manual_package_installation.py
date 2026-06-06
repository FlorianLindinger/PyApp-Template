"""WIP"""

import os
import subprocess
import sys

# add root dir for imports:
root_dir = os.path.dirname(__file__) + "\\..\\..\\..\\.."
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from backend.DONT_CHANGE.scripts._common_code import (
    create_frontend_python_tool_scripts,
    ensure_python_distro,
    print_traceback,
)
from backend.DONT_CHANGE.scripts._common_variables import (
    frontend_launcher_for_pip_install_terminal,
    frontend_python_exe,
)

try:
    ensure_python_distro()
    create_frontend_python_tool_scripts()

    # upgrade pip
    try:
        subprocess.run(  # noqa
            (
                frontend_python_exe,
                "-m",
                "pip",
                "install",
                "--upgrade",
                "pip",
                "--disable-pip-version-check",
            ),
            check=True,
        )
        subprocess.run("cls", shell=True)  # noqa
    except subprocess.CalledProcessError:
        print("[Warning] pip upgrade failed. Opening the terminal anyway.")

    print('Install packages with "pip install package_name"')
    print()

    subprocess.run(["cmd", "/k", "call", frontend_launcher_for_pip_install_terminal])  # noqa
except Exception as e:
    print_traceback(
        f"[Error] Failed to open terminal for manual package installation: {e}", add_press_enter_to_exit=True
    )
