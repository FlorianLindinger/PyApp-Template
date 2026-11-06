"""Open main.py or the user settings file in the editor: open_file.py main_py|settings.

B\\M.bat and B\\S.bat normally open the file Setup passed them without Python; this action
runs when that file is missing (or the shortcut has no target) and reports why.
"""

from __future__ import annotations

import os
import sys

from backend.DONT_CHANGE.backend_settings import DEV_SETTINGS_PATH, MAIN_PY_SCRIPT_PATH
from backend.DONT_CHANGE.scripts.config import settings
from backend.DONT_CHANGE.scripts.errors import SettingsError
from backend.DONT_CHANGE.scripts.filesystem_tools import make_abs_path_relative_to_file
from backend.DONT_CHANGE.scripts.shell_tools import open_in_editor

fail_message = "[Error] Failed to open the file: {e}"


def main() -> None:
    """Resolve the file, check that it exists and open it (VS Code if installed, else Notepad)."""
    kind = sys.argv[1] if len(sys.argv) > 1 else "main_py"
    if kind == "settings":
        user_settings_path = settings().user_settings_path
        if not user_settings_path:
            raise SettingsError(f'There is no settings file: user_settings_path is None in "{DEV_SETTINGS_PATH}".')
        path = make_abs_path_relative_to_file(user_settings_path, DEV_SETTINGS_PATH)
    else:
        path = MAIN_PY_SCRIPT_PATH
    if not os.path.isfile(path):
        raise SettingsError(f'The file does not exist: "{path}"')
    open_in_editor(path)
