import os
import signal
import sys
import time

import win32com.propsys.propsys as propsys  # type:ignore #noqa
import win32com.propsys.pscon as pscon  # type:ignore #noqa
from win32com.client import Dispatch  # type:ignore
from win32com.shell import shellcon  # type:ignore

# move to folder of this file for correct relative paths and ensure it's in path
file_dir = os.path.dirname(os.path.abspath(__file__))+"\\"

# =============================
# import from common_code_and_variables.py
# =============================
project_root = os.path.normpath(file_dir + "..\\..")
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from do_not_change.specific_scripts.common_code_and_variables import (
    backend_python_exe_path,
    backend_pythonw_exe_path,
    sanitize_app_id,
    sanitize_filename,
    settings,
    settings_file_path,
)

# =============================

# local settings:

python_exe = backend_python_exe_path
pythonw_exe = backend_pythonw_exe_path

output_path = os.path.normpath(file_dir + "..\\..\\..")+"\\"

launcher_py = os.path.normpath(file_dir + "..\\T.py")
settings_py = os.path.normpath(file_dir + "..\\set.py")
launcher_no_terminl_py = os.path.normpath(file_dir + "..\\noT.py")
stop_no_terminal_py = os.path.normpath(file_dir + "..\\q_T.py")

launcher_icon_path = os.path.normpath(file_dir + "..\\..\\icons\\icon.ico")
settings_icon_path = os.path.normpath(file_dir + "..\\..\\icons\\settings.ico")
launcher_no_terminl_icon_path = os.path.normpath(file_dir + "..\\..\\icons\\icon.ico")
stop_no_terminal_icon_path = os.path.normpath(file_dir + "..\\..\\icons\\stop.ico")

if "program_name" not in settings:
    input(f'[Error] Missing "program_name" setting in "{settings_file_path}". Press enter to exit.')
    os.kill(os.getppid(), signal.SIGTERM)
if "start_name" not in settings:
    input(f'[Error] Missing "start_name" setting in "{settings_file_path}". Press enter to exit.')
    os.kill(os.getppid(), signal.SIGTERM)
if "start_no_terminal_name" not in settings:
    input(f'[Error] Missing "start_no_terminal_name" setting in "{settings_file_path}". Press enter to exit.')
    os.kill(os.getppid(), signal.SIGTERM)
if "settings_name" not in settings:
    input(f'[Error] Missing "settings_name" setting in "{settings_file_path}". Press enter to exit.')
    os.kill(os.getppid(), signal.SIGTERM)
if "stop_no_terminal_name" not in settings:
    input(f'[Error] Missing "stop_no_terminal_name" setting in "{settings_file_path}". Press enter to exit.')
    os.kill(os.getppid(), signal.SIGTERM)
program_name = settings["program_name"]

launcher_lnk_name = (
    output_path + sanitize_filename(settings["start_name"].replace("program_name", program_name)) + ".lnk"
)

settings_lnk_name = (
    output_path + sanitize_filename(settings["settings_name"].replace("program_name", program_name)) + ".lnk"
)

launcher_no_terminl_lnk_name = (
    output_path + sanitize_filename(settings["start_no_terminal_name"].replace("program_name", program_name)) + ".lnk"
)

stop_no_terminal_lnk_name = (
    output_path + sanitize_filename(settings["stop_no_terminal_name"].replace("program_name", program_name)) + ".lnk"
)


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


def make_lnk(output_path, icon_path, script_path, args=None, appid=None, description="", terminal=True):

    print(f"[Info] Generating: {output_path}")

    if args is not None:
        shortcut_args = f'"{script_path}" {args}'
    else:
        shortcut_args = f'"{script_path}"'

    if terminal == True:
        create_shortcut_with_appid(
            args=shortcut_args,
            output=output_path,
            app_id=appid,
            icon_path=icon_path,
            target=python_exe,
            wdir="",
            description=description,
        )
    else:
        create_shortcut_with_appid(
            args=shortcut_args,
            output=output_path,
            app_id=appid,
            icon_path=icon_path,
            target=pythonw_exe,
            wdir="",
            description=description,
        )


def main():

    # Generate the 4 shortcuts
    appid = sanitize_app_id(program_name)
    # replace and shorten if too long which might cause path length limit problems (10 is arbitrary)
    if len(appid) > 15:
        appid.replace("-", "").replace(".", "")
    if len(appid) > 15:
        appid = appid[:7] + appid[-7:]
    make_lnk(launcher_lnk_name, launcher_icon_path, launcher_py, args=appid, appid=appid, description="WIP")
    make_lnk(settings_lnk_name, settings_icon_path, settings_py, description="WIP")
    make_lnk(
        launcher_no_terminl_lnk_name,
        launcher_no_terminl_icon_path,
        launcher_no_terminl_py,
        args=appid,
        appid=appid,
        description="WIP",
    )
    make_lnk(stop_no_terminal_lnk_name, stop_no_terminal_icon_path, stop_no_terminal_py, description="WIP")

    print()
    print(f"[Success] Shortcuts created in: {output_path}")


if __name__ == "__main__":
    main()
    print()
    input("Press enter to exit")
    # force close terminal
    os.kill(os.getppid(), signal.SIGTERM)
