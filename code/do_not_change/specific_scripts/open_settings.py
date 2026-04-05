# ==========================================================================
#   Local Variables
# ==========================================================================

rel_path_to_settings_ini = "..\\..\\non-user_settings.ini"

# ==========================================================================
# package imports

import os
import sys

# ==========================================================================
# move to folder of this file and add project root to sys.path for package imports

file_path = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.normpath(file_path + "\\..\\..")
if project_root not in sys.path:
    sys.path.insert(0, project_root)
os.chdir(file_path)

# ==========================================================================
# import from helper_functions

from do_not_change.specific_scripts.helper_functions import get_settings, make_abs_path_relative_to_file, open_in_editor

# ==========================================================================
# code execution

settings = get_settings(rel_path_to_settings_ini)
user_settings_path = make_abs_path_relative_to_file(settings["user_settings_path"], rel_path_to_settings_ini)

open_in_editor(user_settings_path)
