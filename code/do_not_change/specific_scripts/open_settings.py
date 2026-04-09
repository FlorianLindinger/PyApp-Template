# ==========================================================================
# package imports

import os
import sys

# ==========================================================================
# import from common_code_and_variables.py

file_path = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.normpath(file_path + "\\..\\..")
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from do_not_change.specific_scripts.common_code import (
    make_abs_path_relative_to_file,
    open_in_editor,
)
from do_not_change.specific_scripts.common_variables import (
    developer_settings,
    developer_settings_path,
)

# ==========================================================================
# code execution

user_settings_path = make_abs_path_relative_to_file(developer_settings.user_settings_path, developer_settings_path)

try:
    open_in_editor(user_settings_path)
except Exception as e:
    print(f'[Error] Failed to open settings file at "{user_settings_path}": {e}')
    input("Press Enter to close this window...")
    sys.exit(1)
