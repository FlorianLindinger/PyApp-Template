import os
import re
import signal
import time
import unicodedata

import win32com.propsys.propsys as propsys  # type:ignore #noqa
import win32com.propsys.pscon as pscon  # type:ignore #noqa
from win32com.client import Dispatch  # type:ignore
from win32com.shell import shellcon  # type:ignore

# move to folder of this file for correct relative paths and ensure it's in path
file_dir = os.path.dirname(os.path.abspath(__file__)) + "\\"

# =============================
# import from common_code_and_variables.py
# =============================

import developer_settings
from do_not_change.specific_scripts.common_variables import (
    backend_python_exe_path,
    developer_settings_path,
)

# =============================

# local settings:

python_exe = backend_python_exe_path

output_path = os.path.normpath(file_dir + "..\\..\\..") + "\\"

launcher_py = os.path.normpath(file_dir + "..\\T.py")
settings_py = os.path.normpath(file_dir + "..\\S.py")
launcher_no_terminl_py = os.path.normpath(file_dir + "..\\N.py")
stop_no_terminal_py = os.path.normpath(file_dir + "..\\Q.py")

launcher_icon_path = os.path.normpath(file_dir + "..\\..\\icons\\icon.ico")
settings_icon_path = os.path.normpath(file_dir + "..\\..\\icons\\settings.ico")
launcher_no_terminl_icon_path = os.path.normpath(file_dir + "..\\..\\icons\\icon.ico")
stop_no_terminal_icon_path = os.path.normpath(file_dir + "..\\..\\icons\\stop.ico")

# ====================


def make_abs_path_relative_to_file(path, file):
    """makes a path absolute if relative with respect to the file (as if the file defined it)"""
    if not os.path.isabs(path):
        return os.path.normpath(os.path.dirname(file) + "\\" + path)
    else:
        return path


def sanitize_filename(filename, replacement="_"):
    # 1. Characters illegal in Windows: < > : " / \ | ? *
    # Also handles control characters (0-31)
    illegal_chars = r'[<>:"/\\|?*\x00-\x1f]'
    filename = re.sub(illegal_chars, replacement, filename)
    # 2. Windows reserved filenames (CON, PRN, AUX, NUL, COM1-9, LPT1-9)
    # These cannot be filenames even with an extension (e.g., CON.txt is bad)
    reserved_names = {
        "CON",
        "PRN",
        "AUX",
        "NUL",
        "COM1",
        "COM2",
        "COM3",
        "COM4",
        "COM5",
        "COM6",
        "COM7",
        "COM8",
        "COM9",
        "LPT1",
        "LPT2",
        "LPT3",
        "LPT4",
        "LPT5",
        "LPT6",
        "LPT7",
        "LPT8",
        "LPT9",
    }
    # Check the "stem" (name before the dot)
    base_name = os.path.splitext(filename)[0].upper()
    if base_name in reserved_names:
        filename = f"{replacement}{filename}"
    # 3. Strip trailing dots and spaces (Windows ignores/removes these)
    filename = filename.rstrip(". ")
    # 4. Enforce length limit (255 characters for the filename itself)
    if len(filename) > 255:
        filename = filename[:255]
    # 5. Handle empty strings (if sanitization removed everything)
    return filename if filename else "unnamed_file"


def sanitize_app_id(input_string):
    # 1. Convert to lowercase and normalize unicode (e.g., convert 'é' to 'e')
    name = unicodedata.normalize("NFKD", input_string).encode("ascii", "ignore").decode("ascii").lower()
    # 2. Replace spaces and underscores with hyphens
    name = re.sub(r"[\s_]+", "-", name)
    # 3. Remove any character that isn't lowercase a-z, 0-9, a hyphen, or a dot
    name = re.sub(r"[^a-z0-9\-\.]", "", name)
    # 4. Remove duplicate hyphens or dots (e.g., "my--app" becomes "my-app")
    name = re.sub(r"-+", "-", name)
    name = re.sub(r"\.+", ".", name)
    # 5. Trim hyphens/dots from the start and end
    name = name.strip("-.")
    return name


def create_shortcut_with_appid(args, output, target=None, icon_path=None, wdir="", app_id=None, description=""):

    if (icon_path is not None) and (not os.path.exists(icon_path)):
        print('[Warning] icon not existing at "{icon_path}"')
        icon_path = None

    if icon_path and not os.path.isabs(icon_path):
        icon_path = os.path.abspath(icon_path)
    if output and not os.path.isabs(output):
        output = os.path.abspath(output)
    if wdir != "" and not os.path.isabs(wdir):
        wdir = os.path.abspath(wdir)

    # delete existing shortcut if it exists
    if os.path.exists(output):
        os.remove(output)
    while os.path.exists(output):
        time.sleep(0.1)

    # 1. Create the shortcut file via WScript.Shell (Standard)
    shell = Dispatch("WScript.Shell")
    shortcut = shell.CreateShortcut(output)
    shortcut.TargetPath = target
    shortcut.Arguments = args
    shortcut.WorkingDirectory = wdir
    shortcut.Description = description
    if icon_path:
        shortcut.IconLocation = icon_path
    shortcut.Save()

    # 2. Add AppUserModelID via IPropertyStore (Advanced)
    if app_id is not None:
        # Wait for Windows to release file lock before property store access
        time.sleep(1.0)
        try:
            pStore = propsys.SHGetPropertyStoreFromParsingName(
                output, None, shellcon.GPS_READWRITE, propsys.IID_IPropertyStore
            )
            key = pscon.PKEY_AppUserModel_ID
            prop_var = propsys.PROPVARIANTType(app_id)
            pStore.SetValue(key, prop_var)
            pStore.Commit()
        except Exception:
            # try again
            time.sleep(1.0)
            try:
                pStore = propsys.SHGetPropertyStoreFromParsingName(
                    output, None, shellcon.GPS_READWRITE, propsys.IID_IPropertyStore
                )
                key = pscon.PKEY_AppUserModel_ID
                prop_var = propsys.PROPVARIANTType(app_id)
                pStore.SetValue(key, prop_var)
                pStore.Commit()
            except Exception as e:
                print(f"[Warning] Failed to set AppID: {e}")


def make_lnk(output_path, icon_path, script_path, args=None, appid=None, description=""):

    print(f"[Info] Generating: {output_path}")

    if args is not None:
        shortcut_args = f'"{script_path}" {args}'
    else:
        shortcut_args = f'"{script_path}"'

    create_shortcut_with_appid(
        args=shortcut_args,
        output=output_path,
        app_id=appid,
        icon_path=icon_path,
        target=python_exe,
        wdir="",
        description=description,
    )


def main():

    # generate app-id
    appid = sanitize_app_id(developer_settings.program_name)
    # replace and shorten if too long which might cause path length limit problems (10 is arbitrary)
    if len(appid) > 15:
        appid.replace("-", "").replace(".", "")
    if len(appid) > 15:
        appid = appid[:7] + appid[-7:]

    # Shortcut: normal start
    if hasattr(developer_settings, "start_name") and developer_settings.start_name != "":
        out = output_path + sanitize_filename(developer_settings.start_name) + ".lnk"
        make_lnk(out, launcher_icon_path, launcher_py, args=appid, appid=appid, description="WIP")

    # Shortcut: start without terminal
    if hasattr(developer_settings, "start_no_terminal_name") and developer_settings.start_no_terminal_name != "":
        out = (
            output_path + sanitize_filename(developer_settings.start_no_terminal_name) + ".lnk"
        )
        make_lnk(
            out,
            launcher_no_terminl_icon_path,
            launcher_no_terminl_py,
            args=appid,
            appid=appid
            + "W",  # add "W" for windowless to allow both launchers to pin to taskbar because different app-id (for same shortcut target)
            description="WIP",
        )

    # Shortcut: stop program (that is started without terminal)
    if hasattr(developer_settings, "stop_no_terminal_name") and developer_settings.stop_no_terminal_name != "":
        out = output_path + sanitize_filename(developer_settings.stop_no_terminal_name) + ".lnk"
        make_lnk(out, stop_no_terminal_icon_path, stop_no_terminal_py, description="WIP")

    # Shortcut: open settings
    if (
        hasattr(developer_settings, "user_settings_path")
        and hasattr(developer_settings, "settings_name")
        and developer_settings.settings_name != ""
        and os.path.exists(make_abs_path_relative_to_file(developer_settings.user_settings_path, developer_settings_path))
    ):
        out = output_path + sanitize_filename(developer_settings.settings_name) + ".lnk"
        make_lnk(out, settings_icon_path, settings_py, description="WIP")

    print()
    print(f"[Success] Shortcut(s) created in: {output_path}")


if __name__ == "__main__":
    main()
    print()
    input("Press enter to exit")
    # force close terminal
    os.kill(os.getppid(), signal.SIGTERM)
