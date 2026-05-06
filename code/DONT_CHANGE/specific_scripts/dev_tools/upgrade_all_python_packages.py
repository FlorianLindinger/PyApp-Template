import os
import subprocess
import sys

# add root dir for imports:
root_dir = os.path.dirname(__file__) + "\\..\\..\\.."
sys.path.insert(0, root_dir)

from DONT_CHANGE.specific_scripts.common_code import ensure_venv, input_success, print_traceback
from DONT_CHANGE.specific_scripts.common_variables import venv_exe_path

ensure_venv()

try:
    subprocess.run([venv_exe_path, "-m", "pip", "install", "pip", "--upgrade", "--disable-pip-version-check"])  # noqa
    subprocess.run([venv_exe_path, "-m", "pip", "install", "--upgrade", "--disable-pip-version-check"])  # noqa
    print()
    input_success("[Success] Press enter to exit")
except Exception as e:
    print_traceback(f"[Error] Failed during upgrad of all packages: {e}", add_press_enter_to_exit=True)
