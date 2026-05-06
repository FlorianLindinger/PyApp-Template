import os
import subprocess
import sys

# add root dir for imports:
root_dir = os.path.dirname(__file__) + "\\..\\..\\.."
sys.path.insert(0, root_dir)

from DONT_CHANGE.specific_scripts.common_code import ensure_venv, print_traceback
from DONT_CHANGE.specific_scripts.common_variables import venv_dir_path, venv_exe_path

try:
    ensure_venv()
    try:
        subprocess.run(  # noqa
            (
                venv_exe_path,
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

    activate_bat = venv_dir_path + "\\Scripts\\activate.bat"

    print('Install packages with "pip install package_name"')
    print()

    subprocess.run(  # noqa
        f'cmd /k "call "{activate_bat}""',
        shell=True,
    )
except Exception as e:
    print_traceback(
        f"[Error] Failed to open terminal for manual package installation: {e}", add_press_enter_to_exit=True
    )
