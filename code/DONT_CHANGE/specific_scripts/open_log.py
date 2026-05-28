"""Open the current configured log file from a launcher shortcut."""

try:
    import os
    import sys
    from datetime import datetime
    from urllib.request import pathname2url

    # add root dir for debug cases where this script is called on its own:
    root_dir = os.path.dirname(__file__) + "\\..\\.."
    if root_dir not in sys.path:
        sys.path.insert(0, root_dir)

    import developer_settings
    from DONT_CHANGE.specific_scripts.common_code import close_terminal, input_warn, print_warn
    from DONT_CHANGE.specific_scripts.common_variables import python_script_path, shortcut_output_dir

    def clickable_path(path: str) -> str:
        """Return an OSC-8 clickable file hyperlink for terminals that support it."""
        try:
            uri = "file:" + pathname2url(os.path.abspath(path))
        except Exception:
            return path
        return f"\033]8;;{uri}\033\\{path}\033]8;;\033\\"

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

    log_path = current_log_path()
    if log_path == "":
        print("[Info] Log path is disabled in developer_settings.py.")
        input("Press enter to exit.")
        close_terminal()

    log_folder = os.path.dirname(log_path)
    print(f"[Info] Current log file: {log_path}")
    print(f"[Info] Log folder: {clickable_path(log_folder)}")

    if not os.path.exists(log_path):
        print()
        print("[Info] Current log file does not exist yet.")
        input("Press enter to exit.")
        close_terminal()

    try:
        os.startfile(log_path)  # type: ignore[attr-defined]  # noqa:S606
        close_terminal()
    except Exception as e:
        print_warn(f"[Error] Failed to open log file: {e}")
        input_warn("Press enter to exit")
        close_terminal()


except Exception as e:
    import sys
    import traceback

    print(f"[Error] Failed to open current log file: {e}")
    print("=" * 20)
    print(traceback.format_exc())
    print("=" * 20)
    input("Press Enter to close this window...")
    sys.exit(1)
