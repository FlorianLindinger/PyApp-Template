"""WIP"""

try:
    # =============================
    # import Python packages

    import os
    import sys
    from datetime import datetime
    from urllib.request import pathname2url

    # =============================
    # add root dir for debug cases where this script is called on its own

    root_dir = os.path.dirname(__file__) + "\\..\\.."
    if root_dir not in sys.path:
        sys.path.insert(0, root_dir)

    # =============================
    # import from files

    import developer_settings
    from DONT_CHANGE.specific_scripts.common_code import (
        close_terminal,
        input_warn,
        print_warn,
        setup_terminal_colors_and_unminimize_plus_foreground_on_first_print,
    )
    from DONT_CHANGE.specific_scripts.common_variables import python_script_path, shortcut_output_dir

    # =============================
    # define local functions

    def clickable_path(path: str) -> str:
        abs_path = os.path.abspath(path)

        uri = "file:" + pathname2url(abs_path)
        return f"\033]8;;{uri}\033\\{abs_path}\033]8;;\033\\"

    def current_log_path() -> str:
        """Resolve the log path the app would use for a launch right now."""
        log_path_rel_to_start_folder = getattr(developer_settings, "log_path_rel_to_start_folder", None)
        if log_path_rel_to_start_folder in [None, False, ""]:
            return ""

        if getattr(developer_settings, "start_in_shortcut_folder", False):
            base_folder = shortcut_output_dir
        else:
            base_folder = os.path.dirname(python_script_path)

        log_path = os.path.normpath(os.path.join(base_folder, log_path_rel_to_start_folder))
        return datetime.now().astimezone().strftime(log_path)

    # =============================
    # script is inteded to be launched minimized and will un minimize on frist print/error

    setup_terminal_colors_and_unminimize_plus_foreground_on_first_print()

    # =============================

    log_path = current_log_path()
    if log_path == "":
        print("[Info] Log path is disabled in developer_settings.py.")
        input("Press enter to exit.")
        close_terminal()

    if not os.path.exists(log_path):
        print("[Info] Current log file does not exist yet.")
        print(f"[Info] Current log file: {log_path}")
        print(f"[Info] Log folder: {clickable_path(os.path.dirname(log_path))}")
        input("Press enter to exit.")
        close_terminal()

    try:
        os.startfile(log_path)  # type: ignore[attr-defined]  # noqa:S606
        close_terminal()
    except Exception as e:
        print_warn(f"[Error] Failed to open log file: {e}")
        input_warn("Press enter to exit")
        close_terminal()

    # =============================

except Exception as e:
    import os
    import traceback

    print()
    print()
    print("=" * 20)
    print(f"[Error] Failed to open current log file: {e}")
    print("-" * 20)
    print(traceback.format_exc())
    print("=" * 20)
    input("[Error (see above)] Press enter to exit")
    os._exit(1)  # instead of sys.exit(1) to prevent exception by script calling this script
