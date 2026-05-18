import os
import subprocess
import sys

# add root dir for imports:
root_dir = os.path.dirname(__file__) + "\\..\\..\\.."
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from DONT_CHANGE.specific_scripts.common_code import (
    ensure_python_distro,
    input_success,
    print_traceback,
    save_current_packages,
)
from DONT_CHANGE.specific_scripts.common_variables import frontend_packages_dir, frontend_python_exe

ensure_python_distro()

try:
    path = save_current_packages(with_version=False)

    subprocess.run([frontend_python_exe, "-m", "pip", "install", "pip", "--upgrade", "--disable-pip-version-check"])  # noqa
    subprocess.run(  # noqa
        [
            frontend_python_exe,
            "-m",
            "pip",
            "install",
            path,
            "--target",
            frontend_packages_dir,
            "--upgrade",
            "--disable-pip-version-check",
        ]
    )
    print()
    input_success("[Success] Press enter to exit")
except Exception as e:
    print_traceback(f"[Error] Failed during upgrad of all packages: {e}", add_press_enter_to_exit=True)
