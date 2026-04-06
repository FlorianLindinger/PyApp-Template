# ==========================================================================
# package imports

import os
import sys

# ==========================================================================
# import from helper_functions

file_path = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.normpath(file_path + "\\..\\..")
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from do_not_change.specific_scripts.helper_functions import (
    make_abs_path_relative_to_file,
    open_in_editor,
    settings,
    settings_file_path,
)

# ==========================================================================
# code execution

user_settings_path = make_abs_path_relative_to_file(settings["user_settings_path"], settings_file_path)

try:
    open_in_editor(user_settings_path)
except Exception as e:
    print(f'[Error] Failed to open settings file at "{user_settings_path}": {e}')
    input("Press Enter to close this window...")
    sys.exit(1)
