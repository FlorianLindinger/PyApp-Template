import os
import sys
import time
import traceback

import win32com.propsys.propsys as propsys
import win32com.propsys.pscon as pscon
from win32com.client import Dispatch
from win32com.shell import shellcon

# =============================


def create_shortcut_with_appid(args, output, app_id, icon_path=None, target=sys.executable, wdir=""):

    if icon_path and not os.path.isabs(icon_path):
        icon_path = os.path.abspath(icon_path)

    if output and not os.path.isabs(output):
        output = os.path.abspath(output)

    if wdir != "" and not os.path.isabs(wdir):
        wdir = os.path.abspath(wdir)

    # delete shorctut
    if os.path.exists(output):
        os.remove(output)
    while os.path.exists(output):
        print(f"Waiting for {output} to be deleted...")
        time.sleep(0.1)

    # 1. Create the shortcut file
    shell = Dispatch("WScript.Shell")
    shortcut = shell.CreateShortcut(output)

    shortcut.TargetPath = target
    shortcut.Arguments = args
    shortcut.WorkingDirectory = wdir

    if icon_path:
        shortcut.IconLocation = icon_path

    shortcut.Save()

    # Wait for Windows to release the file lock. Otherwise the next step will/might fail.
    print("Waiting for file release...")
    time.sleep(1.5)

    # change shortcut app-id
    try:
        pStore = propsys.SHGetPropertyStoreFromParsingName(
            output, None, shellcon.GPS_READWRITE, propsys.IID_IPropertyStore
        )
    except Exception as e:
        print(f"Error opening Property Store: {e}")
        return
    key = pscon.PKEY_AppUserModel_ID
    prop_var = propsys.PROPVARIANTType(app_id)
    pStore.SetValue(key, prop_var)
    pStore.Commit()


# =============================

if __name__ == "__main__":
    try:
        shortcut_location = sys.argv[1]
        wdir = sys.argv[2]
        path_to_terminal_emulator_exe = sys.argv[3]
        icon_file = sys.argv[4]
        use_qt_terminal=sys.argv[5]
        app_id = sys.argv[6]
        args_for_target = sys.argv[7]
        args_for_script = sys.argv[8]

        args_for_shortcut = ""
        if args_for_target:
            args_for_shortcut += args_for_target.strip() + " "

        args_for_shortcut += f'{use_qt_terminal} "{app_id}"'

        if args_for_script:
            args_for_shortcut += " " + args_for_script.strip()


        create_shortcut_with_appid(
            output=shortcut_location,
            wdir=wdir,
            target=path_to_terminal_emulator_exe,
            app_id=app_id,
            icon_path=icon_file,
            args=args_for_shortcut,
        )

        print()
        print("Success!")
        print()
    except Exception as e:
        print(f"[Error] Failed to create shortcuts: {e}")
        print(traceback.format_exc())
        input("[Error] Press Enter to exit...")
