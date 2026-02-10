import os
import sys
import time
import traceback

# Import propsys and shellcon for flags
import win32com.propsys.propsys as propsys
import win32com.propsys.pscon as pscon
from win32com.client import Dispatch
from win32com.shell import shellcon

def create_shortcut_with_appid(args, output, app_id, icon_path=None, exe=sys.executable, wdir=""):
    # Convert relative paths to absolute for WScript
    # (Windows Shortcuts require absolute paths internally to function reliably)
    if exe and not os.path.isabs(exe):
        exe = os.path.abspath(exe)
    
    if icon_path and not os.path.isabs(icon_path):
        icon_path = os.path.abspath(icon_path)
        
    if output and not os.path.isabs(output):
        output = os.path.abspath(output)

    # 1. Create the shortcut file
    shell = Dispatch("WScript.Shell")
    shortcut = shell.CreateShortcut(output)
    
    shortcut.TargetPath = exe
    shortcut.Arguments = args
    shortcut.WorkingDirectory = wdir
    
    if icon_path:
        shortcut.IconLocation = icon_path
        
    shortcut.Save()

    # CRITICAL FIX: Wait for Windows to release the file lock
    print("Waiting for file release...")
    time.sleep(1.5)

    # 2. Add the AppID
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

    print(f"Success! Shortcut created at: {output}")


if __name__ == "__main__":
    try:
        # --- CONFIGURATION (Relative Paths Allowed) ---
        # The script will automatically convert these to absolute paths
        # based on where this script is located.
        
        # current_dir = os.path.dirname(os.path.abspath(__file__))

        # wdir= os.path.dirname(os.path.abspath(__file__))+r"\code\do_not_change\specific_scripts"
        wdir=os.getcwd()
        print(wdir)

        # script_to_run = r"run_batch.py"
        script_to_run="pyqt5_terminal.py"
        icon_file = "icon.ico"  # Relative path is fine now

        shortcut_location = "pyqt5.lnk"
        # shortcut_location_windowless = "MyApp Windowless.lnk"

        my_app_id = "test3"
        # my_app_id_windowless = "mycompany.myproduct.gui.v2"

        # You can now use relative paths here safely
        path_to_python = r"code\do_not_change\python_runtime\pyqt5 runtime\python.exe"
        # path_to_pythonw = r"code\do_not_change\python_runtime\pythonw.exe"
        
        internal_python_exe_path=r"code\py_env\virt_env\portable_Scripts\python.bat"
        
        args=f'"{script_to_run}" "test2.py" "--python" "{internal_python_exe_path}" "--app_id" "{my_app_id}"'

        # --- CREATE SHORTCUTS ---

        # 1. Console Version
        create_shortcut_with_appid(
            # We assume main.py is in the Working Directory, so we just pass the filename
            args=args,
            output=shortcut_location,
            app_id=my_app_id,
            icon_path=icon_file,
            exe=path_to_python,
            wdir=wdir,
        )
        
        my_app_id = "test4"
        script_to_run="pyside6_terminal.py"
        shortcut_location="pyside6.lnk"
        path_to_python = r"code\do_not_change\python_runtime\python.exe"
        
        args=f'"{script_to_run}" "test2.py" "--python" "{internal_python_exe_path}" "--app_id" "{my_app_id}"'
        
        create_shortcut_with_appid(
            # We assume main.py is in the Working Directory, so we just pass the filename
            args=args,
            output=shortcut_location,
            app_id=my_app_id,
            icon_path=icon_file,
            exe=path_to_python,
            wdir=wdir,
        )


        # 2. Windowless Version
        # create_shortcut_with_appid(
        #     args=f'"{script_to_run}" "{my_app_id_windowless}"',
        #     output=shortcut_location_windowless,
        #     app_id=my_app_id_windowless,
        #     icon_path=icon_file,
        #     exe=path_to_pythonw,
        #     wdir=wdir,
        # )

        input("Press Enter to exit...")
    except Exception as e:
        print(f"Failed to create shortcuts: {e}")
        print(traceback.format_exc())
        input("Press Enter to exit...")