# ==========================================================================
# package imports

import os
import shutil
import subprocess
import sys
import traceback

# ==========================================================================
# import from common variables and developer settings
from do_not_change.specific_scripts.common_variables import (
    developer_settings_dir,
    developer_settings_path,
)

sys.path.insert(0, developer_settings_dir)
import developer_settings

# ==========================================================================
# needed functions


def open_in_editor(path):
    try:
        if not os.path.exists(path):
            print(f"Could not find file at path: {path}")
        vscode_exe_path = shutil.which("code")
        if vscode_exe_path is not None:
            subprocess.Popen([vscode_exe_path, path])  # noqa:S603
        else:
            # Fallback
            subprocess.Popen(["notepad.exe", path])  # noqa:S603
    except Exception as _e:
        print(traceback.format_exc())


def make_abs_path_relative_to_file(path, file):
    """makes a path absolute if relative with respect to the file (as if the file defined it)"""
    if not os.path.isabs(path):
        return os.path.normpath(os.path.dirname(file) + "\\" + path)
    else:
        return path


# ==========================================================================
# code execution

user_settings_path = make_abs_path_relative_to_file(developer_settings.user_settings_path, developer_settings_path)

try:
    open_in_editor(user_settings_path)
except Exception as e:
    print(f'[Error] Failed to open settings file at "{user_settings_path}": {e}')
    input("Press Enter to close this window...")
    sys.exit(1)
