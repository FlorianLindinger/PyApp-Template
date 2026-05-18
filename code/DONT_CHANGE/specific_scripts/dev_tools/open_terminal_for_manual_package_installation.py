import os
import subprocess
import sys

# add root dir for imports:
root_dir = os.path.dirname(__file__) + "\\..\\..\\.."
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from DONT_CHANGE.specific_scripts.common_code import ensure_python_distro, print_traceback
from DONT_CHANGE.specific_scripts.common_variables import (
    frontend_python_exe,
    script_for_set_python_and_pip_target,
)

try:
    ensure_python_distro()

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

    subprocess.run(  # noqa
        ["cmd", "/k", "call", script_for_set_python_and_pip_target],
        shell=True,
    )
except Exception as e:
    print_traceback(
        f"[Error] Failed to open terminal for manual package installation: {e}", add_press_enter_to_exit=True
    )
