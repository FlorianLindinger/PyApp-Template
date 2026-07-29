"""Open the configured user settings file"""

try:
    # ==========================================================================
    # package imports

    import os
    import sys

    # ==========================================================================
    # add root dir for debug cases where this script is called on its own

    root_dir = os.path.dirname(__file__) + "\\..\\..\\..\\.."
    if root_dir not in sys.path:
        sys.path.insert(0, root_dir)

    # ==========================================================================
    # import from common variables and developer settings

    from backend.developer_settings import user_settings_path
    from backend.DONT_CHANGE.scripts.common_code import (
        close_terminal,
        input_warn,
        make_abs_path_relative_to_file,
        open_in_editor,
        print_traceback,
        print_warn,
        set_terminal_colors,
        set_unminimize_and_foreground_on_first_print,
    )
    from backend.DONT_CHANGE.settings.backend_settings import (
        DEV_SETTINGS_PATH,
    )

    # =============================
    # script is inteded to be launched minimized and will un minimize on frist print/error

    set_terminal_colors()
    set_unminimize_and_foreground_on_first_print()

    # =============================

    if not user_settings_path:
        print_warn(f'[Info] Can\'t open settings file because user_settings_path is disabled in "{DEV_SETTINGS_PATH}".')
        input_warn("Press enter to exit.")
        close_terminal()
    else:
        path = make_abs_path_relative_to_file(user_settings_path, DEV_SETTINGS_PATH)

        if not os.path.exists(path):
            print_warn(f'[Error] User settings file ("{path}") does not exist.')
            input_warn("Press enter to exit.")
            close_terminal()
        else:
            try:
                open_in_editor(path)
                close_terminal()
            except Exception:
                print_traceback(f'[Error] Failed to user-settings file "{path}".')
                input_warn("Press enter to exit.")
                close_terminal()

    # =============================

except Exception as e:
    import os
    import traceback

    print()
    print()
    print("=" * 20)
    print(f"[Error] Failed to open settings file: {e}")
    print("-" * 20)
    print(traceback.format_exc())
    print("=" * 20)
    input("[Error (see above)] Press enter to exit")
    os._exit(1)  # instead of sys.exit(1) to prevent exception by script calling this script
