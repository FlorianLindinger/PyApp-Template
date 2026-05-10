try:
    # ==========================================================================
    # package imports

    import os
    import shutil
    import subprocess
    import sys
    import traceback

    # ==========================================================================
    # import from common variables and developer settings
    import developer_settings
    from DONT_CHANGE.specific_scripts.common_code import close_terminal
    from DONT_CHANGE.specific_scripts.common_variables import developer_settings_path

    # ==========================================================================
    # needed functions

    def open_settings_in_editor(path):
        if not os.path.exists(path):
            print(f"[Error] Could not find settings file at path: {path}")
            input("Press enter to exit.")
            sys.exit(0)
        vscode_exe_path = shutil.which("code")
        if vscode_exe_path is not None:
            subprocess.Popen([vscode_exe_path, path])  # noqa:S603
        else:
            # Fallback
            subprocess.Popen(["notepad.exe", path])  # noqa:S603

    def make_abs_path_relative_to_file(path, file):
        """makes a path absolute if relative with respect to the file (as if the file defined it)"""
        if not os.path.isabs(path):
            return os.path.normpath(os.path.dirname(file) + "\\" + path)
        else:
            return path

    # ==========================================================================
    # code execution

    if not hasattr(developer_settings, "user_settings_path"):
        print("[Warning] Settings file is not implemented in program.")
        input("Press enter to exit.")
        sys.exit(0)
    elif developer_settings.user_settings_path in [None, False, ""]:
        print("[Warning] Settings file disabled in program.")
        input("Press enter to exit.")
        sys.exit(0)
    else:
        user_settings_path = make_abs_path_relative_to_file(
            developer_settings.user_settings_path, developer_settings_path
        )

        try:
            open_settings_in_editor(user_settings_path)
            close_terminal()
        except Exception as e:
            print(f'[Error] Failed to open settings file at "{user_settings_path}": {e}')
            print("=" * 20)
            print(traceback.format_exc())
            print("=" * 20)
            input("Press Enter to close this window...")
            sys.exit(1)

except Exception as e:
    import sys
    import traceback

    print(f"[Error] Failed to start open settings file script: {e}")
    print("=" * 20)
    print(traceback.format_exc())
    print("=" * 20)
    input("Press Enter to close this window...")
    sys.exit(1)
