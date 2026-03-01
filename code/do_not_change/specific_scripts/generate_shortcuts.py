import os
import pathlib
import signal
import sys
import time

import win32com.propsys.propsys as propsys  # type:ignore #noqa
import win32com.propsys.pscon as pscon  # type:ignore #noqa
from win32com.client import Dispatch  # type:ignore
from win32com.shell import shellcon  # type:ignore

# move to folder of this file for correct relative paths and ensure it's in path
script_dir = pathlib.Path(__file__).parent.resolve()
os.chdir(script_dir)
if str(script_dir) not in sys.path:
    sys.path.insert(0, str(script_dir))

import launcher_utilities as utils  # type:ignore

# local settings:

settings_path = (script_dir / "../../non-user_settings.ini").resolve()
python_exe = str((script_dir / ".." / "P" / "P.exe").resolve())
output_path = (script_dir / ".." / ".." / "..").resolve()

launcher_py = (script_dir / ".." / "T.py").resolve()
settings_py = (script_dir / ".." / "set.py").resolve()
launcher_no_terminl_py = (script_dir / ".." / "noT.py").resolve()
stop_no_terminal_py = (script_dir / ".." / "q_T.py").resolve()

launcher_icon_path = str((script_dir / ".." / ".." / "icons" / "icon.ico").resolve())
settings_icon_path = str((script_dir / ".." / ".." / "icons" / "settings.ico").resolve())
launcher_no_terminl_icon_path = str((script_dir / ".." / ".." / "icons" / "icon.ico").resolve())
stop_no_terminal_icon_path = str((script_dir / ".." / ".." / "icons" / "stop.ico").resolve())

settings = utils.get_settings(settings_path)
if "program_name" not in settings:
    input(f'[Error] Missing "program_name" setting in "{settings_path}". Press enter to exit.')
    os.kill(os.getppid(), signal.SIGTERM)
if "start_name" not in settings:
    input(f'[Error] Missing "start_name" setting in "{settings_path}". Press enter to exit.')
    os.kill(os.getppid(), signal.SIGTERM)
if "start_no_terminal_name" not in settings:
    input(f'[Error] Missing "start_no_terminal_name" setting in "{settings_path}". Press enter to exit.')
    os.kill(os.getppid(), signal.SIGTERM)
if "settings_name" not in settings:
    input(f'[Error] Missing "settings_name" setting in "{settings_path}". Press enter to exit.')
    os.kill(os.getppid(), signal.SIGTERM)
if "stop_no_terminal_name" not in settings:
    input(f'[Error] Missing "stop_no_terminal_name" setting in "{settings_path}". Press enter to exit.')
    os.kill(os.getppid(), signal.SIGTERM)
program_name = settings["program_name"]

launcher_lnk_name = (
    str(output_path / utils.sanitize_filename(settings["start_name"].replace("program_name", program_name))) + ".lnk"
)
settings_lnk_name = (
    str(output_path / utils.sanitize_filename(settings["settings_name"].replace("program_name", program_name))) + ".lnk"
)
launcher_no_terminl_lnk_name = (
    str(output_path / utils.sanitize_filename(settings["start_no_terminal_name"].replace("program_name", program_name)))
    + ".lnk"
)
stop_no_terminal_lnk_name = (
    str(output_path / utils.sanitize_filename(settings["stop_no_terminal_name"].replace("program_name", program_name)))
    + ".lnk"
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


def make_lnk(output_path, icon_path, script_path, args=None, appid=None, description=""):

    print(f"[Info] Generating: {output_path}")

    if args is not None:
        shortcut_args = f'"{script_path}" {args}'
    else:
        shortcut_args = '"script_path"'

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

    # Generate the 4 shortcuts
    appid = utils.sanitize_app_id(program_name)
    # replace and shorten if too long which might cause path length limit problems (10 is arbitrary)
    if len(appid) > 15:
        appid.replace(["-", "."], "")
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
