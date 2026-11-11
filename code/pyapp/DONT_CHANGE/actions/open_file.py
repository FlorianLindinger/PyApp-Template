"""Open the main script or the user settings file in the editor: open_file.py open_code|settings.

B\\M.bat and B\\S.bat normally open the file Setup passed them without Python; this action
runs when that file is missing (or the shortcut has no target) and reports why.
"""

from __future__ import annotations

import sys
from pathlib import Path

from pyapp.DONT_CHANGE.backend_settings import DEV_SETTINGS_PATH
from pyapp.DONT_CHANGE.scripts.config import main_script_path, settings
from pyapp.DONT_CHANGE.scripts.console_tools import open_in_editor
from pyapp.DONT_CHANGE.scripts.errors import SettingsError
from pyapp.DONT_CHANGE.scripts.file_tools import make_abs_path_relative_to_file

fail_message = "Failed to open the file: {e}"


def main() -> None:
    """Resolve the file, check that it exists and open it (VS Code if installed, else Notepad)."""
    kind = sys.argv[1] if len(sys.argv) > 1 else "open_code"
    if kind == "settings":
        user_settings_path = settings().user_settings_path
        if not user_settings_path:
            raise SettingsError(f'There is no settings file: user_settings_path is "" in "{DEV_SETTINGS_PATH}".')
        path = make_abs_path_relative_to_file(user_settings_path, DEV_SETTINGS_PATH)
    else:
        path = main_script_path()
    if not Path(path).is_file():
        raise SettingsError(f'The file does not exist: "{path}"')
    open_in_editor(path)
