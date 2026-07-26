"""Open the configured user settings file"""

try:
    # ==========================================================================
    # package imports

    import os
    import sys
    import traceback

    # ==========================================================================
    # add root dir for debug cases where this script is called on its own:
    root_dir = os.path.dirname(__file__) + "\\..\\..\\.."
    if root_dir not in sys.path:
        sys.path.insert(0, root_dir)

    # ==========================================================================
    # import from common variables and developer settings
    import backend.developer_settings
    from backend.DONT_CHANGE.scripts._common_code import (
        close_terminal,
        make_abs_path_relative_to_file,
        # setup_terminal_colors_and_unminimize_plus_foreground_on_first_print,
        open_in_editor,
    )
    from backend.DONT_CHANGE.scripts._common_variables import developer_settings_path

    # ==========================================================================
    # needed functions

    # ==========================================================================
    # code execution

    # =============================
    # script is inteded to be launched minimized and will un minimize on frist print/error

    # WIP setup_terminal_colors_and_unminimize_plus_foreground_on_first_print()

    # =============================

    if not hasattr(backend.developer_settings, "user_settings_path"):
        print("[Warning] Settings file is not implemented in program.")
        input("Press enter to exit.")
        sys.exit(0)
    elif backend.developer_settings.user_settings_path in [None, False, ""]:
        print("[Warning] Settings file disabled in program.")
        input("Press enter to exit.")
        sys.exit(0)
    else:
        user_settings_path = make_abs_path_relative_to_file(
            backend.developer_settings.user_settings_path, developer_settings_path
        )

        try:
            open_in_editor(user_settings_path)
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
