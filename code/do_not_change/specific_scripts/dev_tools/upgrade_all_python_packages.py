import subprocess

from do_not_change.specific_scripts.common_variables import input_success, print_traceback, venv_exe_path
from do_not_change.specific_scripts.dev_tools._common_code import ensure_venv

ensure_venv()

try:
    subprocess.run([venv_exe_path, "-m", "pip", "install", "pip", "--upgrade", "--disable-pip-version-check"])  # noqa
    subprocess.run([venv_exe_path, "-m", "pip", "install", "--upgrade", "--disable-pip-version-check"])  # noqa
    print()
    input_success("[Success] Press enter to exit")
except Exception as e:
    print_traceback(f"[Error] Failed during upgrad of all packages: {e}", add_press_enter_to_exit=True)
