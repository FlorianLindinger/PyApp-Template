import os
import pathlib
import sys

# move to folder of this file for correct relative paths and ensure it's in path
script_dir = pathlib.Path(__file__).parent.resolve()
os.chdir(script_dir)
if str(script_dir) not in sys.path:
    sys.path.insert(0, str(script_dir))

import time

import launcher_utilities as utils
import win32com.propsys.propsys as propsys
import win32com.propsys.pscon as pscon
from win32com.client import Dispatch
from win32com.shell import shellcon


def create_shortcut_with_appid(args, output, app_id, icon_path=None, target=sys.executable, wdir=""):
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
    if icon_path:
        shortcut.IconLocation = icon_path
    shortcut.Save()

    # Wait for Windows to release file lock before property store access
    time.sleep(1.0)

    # 2. Add AppUserModelID via IPropertyStore (Advanced)
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


def main():
    settings_path = (script_dir / "../../non-user_settings.ini").resolve()
    settings = utils.get_settings(settings_path)
    if not settings:
        sys.exit(1)

    prog_name = settings.get("program_name", "App")
    dest_dir = (settings_path.parent / settings.get("shortcut_destination_path", "..")).resolve()
    icon_dir = settings_path.parent
    python_exe = sys.executable

    # Target scripts
    launcher_py = (script_dir / "start_program.py").resolve()
    settings_py = (script_dir / "open_settings.py").resolve()
    stop_py = (script_dir / "stop_program.py").resolve()

    def clean(name):
        return name.replace("!program_name!", prog_name)

    def make_lnk(name_key, icon_key, target, args, _desc, appid):
        name = clean(settings.get(name_key, prog_name))
        icon = (icon_dir / settings.get(icon_key, "")).resolve()
        output_path = dest_dir / f"{name}.lnk"

        print(f"[Info] Generating: {name}")
        create_shortcut_with_appid(
            args=f'"{target}" {args}',
            output=str(output_path),
            app_id=f"{appid}",
            icon_path=str(icon) if icon.exists() else None,
            target=python_exe,
            wdir=str(script_dir),
        )

    # Generate the 4 standard shortcuts
    make_lnk("start_name", "icon_path", launcher_py, "", prog_name, "5")
    make_lnk("settings_name", "settings_icon_path", settings_py, "", "Settings", "6")
    make_lnk("start_no_terminal_name", "icon_path", launcher_py, "--background", "Background", "7")
    make_lnk("stop_no_terminal_name", "stop_icon_path", stop_py, "", "Stop", "8")

    print(f"\n[Success] Shortcuts created in: {dest_dir}")


if __name__ == "__main__":
    main()
