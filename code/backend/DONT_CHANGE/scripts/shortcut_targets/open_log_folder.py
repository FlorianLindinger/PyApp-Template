"""Open the configured log folder."""

# ==============================
# settings

fail_message: str = "[Error] Failed to open log folder: {e}"
close_terminal_on_finish: bool = True

import os

root_dir: str = os.path.dirname(__file__) + "\\..\\..\\..\\.."

# ==============================

try:
    # ==============================
    # import Python packages

    import sys

    # ==============================
    # import third-party packages

    # ==============================
    # import from files

    if root_dir not in sys.path:
        sys.path.insert(0, root_dir)

    from backend.developer_settings import (
        log_path,
        log_path_is_relative_to_start_folder_if_relative,
    )
    from backend.DONT_CHANGE.scripts.common_code import (
        get_log_folder_path,
        input_warn,
        print_traceback,
        print_warn,
        set_terminal_colors,
    )
    from backend.DONT_CHANGE.scripts.generic_helpers import (
        close_terminal,
        enable_unminimize_and_foreground_terminal_on_first_print,
    )
    from backend.DONT_CHANGE.settings.backend_settings import DEV_SETTINGS_PATH

    # ==============================
    # local variables

    # ==============================
    # local functions/classes

    # ==============================
    # main function

    def main() -> None:
        """Open the configured log folder, reporting disabled or missing paths."""
        set_terminal_colors()
        enable_unminimize_and_foreground_terminal_on_first_print()

        folder_path = get_log_folder_path(
            log_path, log_path_is_relative_to_start_folder_if_relative
        )
        if folder_path is None:
            print_warn(
                f'[Info] Can\'t open log folder because log_path is disabled in "{DEV_SETTINGS_PATH}".'
            )
            input_warn("Press enter to exit.")
        elif not os.path.exists(folder_path):
            print_warn(f'[Error] Log folder ("{folder_path}") does not exist.')
            input_warn("Press enter to exit.")
        else:
            os.startfile(folder_path)

    # ==============================
    # execute main function

    if __name__ == "__main__":
        try:
            main()
        except Exception as e:
            print_traceback(fail_message.format(e=e))
            input_warn("[Error] Press enter to exit")
        if close_terminal_on_finish:
            close_terminal()

except Exception as e:
    import traceback

    print()
    print()
    print("=" * 30)
    print(fail_message.format(e=e))
    print("-" * 30)
    print(traceback.format_exc())
    print("=" * 30)
    input("[Error] Press enter to exit")
    if close_terminal_on_finish:
        os._exit(1)
