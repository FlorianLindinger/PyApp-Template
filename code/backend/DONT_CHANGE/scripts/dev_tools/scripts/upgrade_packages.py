"""WIP"""

import os
import subprocess
import sys

# add root dir for imports:
root_dir = os.path.dirname(__file__) + "\\..\\..\\..\\.."
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from backend.DONT_CHANGE.scripts._common_code import (
    ensure_python_distro,
    input_success,
    print_traceback,
    save_current_packages,
)
from backend.DONT_CHANGE.scripts._common_variables import FRONTEND_PACKAGES_DIR, FRONTEND_PYTHON_EXE

ensure_python_distro()

try:
    path = save_current_packages(with_version=False)

    subprocess.run(  # noqa
        [
            FRONTEND_PYTHON_EXE,
            "-m",
            "pip",
            "install",
            "pip",
            "--upgrade",
            "--disable-pip-version-check",
            "--no-warn-script-location",
        ],
        check=True,
    )
    subprocess.run(  # noqa
        [
            FRONTEND_PYTHON_EXE,
            "-m",
            "pip",
            "install",
            "-r",
            path,
            "--target",
            FRONTEND_PACKAGES_DIR,
            "--upgrade",
            "--disable-pip-version-check",
        ],
        check=True,
    )
    print()
    input_success("[Success] Press enter to exit")
except Exception as e:
    print_traceback(f"[Error] Failed during upgrad of all packages: {e}", add_press_enter_to_exit=True)
