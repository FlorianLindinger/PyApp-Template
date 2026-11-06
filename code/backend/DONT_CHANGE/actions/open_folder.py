"""Open the log or crash-log folder: open_folder.py logs|crash_logs.

B\\L.bat and B\\C.bat normally open the folder Setup passed them without Python; this action
runs when the folder can only be resolved now (relative to the start folder, or with date codes).
"""

from __future__ import annotations

import os
import sys

from backend.DONT_CHANGE.backend_settings import DEV_SETTINGS_PATH
from backend.DONT_CHANGE.scripts.config import settings
from backend.DONT_CHANGE.scripts.errors import SettingsError
from backend.DONT_CHANGE.scripts.launcher_ui import get_log_folder_path

fail_message = "Failed to open the folder: {e}"

# kind: (path setting, description)
FOLDERS = {
    "logs": ("log_path", "log folder"),
    "crash_logs": ("crash_log_path", "crash log folder"),
}


def main() -> None:
    """Resolve the configured folder, create it if needed and open it in Explorer."""
    setting, description = FOLDERS[sys.argv[1] if len(sys.argv) > 1 else "logs"]
    s = settings()
    folder = get_log_folder_path(getattr(s, setting), getattr(s, setting + "_is_relative_to_start_folder_if_relative"))
    if folder is None:
        raise SettingsError(f'There is no {description}: {setting} is None in "{DEV_SETTINGS_PATH}".')
    os.makedirs(folder, exist_ok=True)
    os.startfile(folder)
