"""WIP"""

try:
    # =============================
    # import Python packages

    import os
    import sys

    # =============================
    # add root dir for debug cases where this script is called on its own

    root_dir = os.path.dirname(__file__) + "\\..\\..\\..\\.."
    if root_dir not in sys.path:
        sys.path.insert(0, root_dir)

    # =============================
    # import from files

    from backend.developer_settings import (
        log_path,
        log_path_is_relative_to_start_folder_if_relative,
    )
    from backend.DONT_CHANGE.scripts._common_code import (
        close_terminal,
        get_log_folder_path,
        input_warn,
        print_traceback,
        print_warn,
        set_terminal_colors,
        set_unminimize_and_foreground_on_first_print,
    )
    from backend.DONT_CHANGE.scripts._common_variables import (
        developer_settings_path,
    )

    # =============================
    # script is inteded to be launched minimized and will un minimize on frist print/error

    set_terminal_colors()
    set_unminimize_and_foreground_on_first_print()

    # =============================

    folder_path = get_log_folder_path(log_path, log_path_is_relative_to_start_folder_if_relative)

    if folder_path is None:
        print_warn(f'[Info] Can\'t open log folder because log_path is disabled in "{developer_settings_path}".')
        input_warn("Press enter to exit.")
    else:
        if not os.path.exists(folder_path):
            print_warn(f'[Error] Log folder ("{folder_path}") does not exist.')
            input_warn("Press enter to exit.")
        else:
            try:
                os.startfile(folder_path)  # noqa:S606
            except Exception:
                print_traceback(f'[Error] Failed to open log folder "{folder_path}".')
                input_warn("Press enter to exit.")

    close_terminal()

    # =============================

except Exception as e:
    import os
    import traceback

    print()
    print()
    print("=" * 20)
    print(f"[Error] Failed to open log folder: {e}")
    print("-" * 20)
    print(traceback.format_exc())
    print("=" * 20)
    input("[Error (see above)] Press enter to exit")
    os._exit(1)  # instead of sys.exit(1) to prevent exception by script calling this script
