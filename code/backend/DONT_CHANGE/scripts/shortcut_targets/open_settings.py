"""Open the configured user settings file."""

# ==============================
# settings

fail_message: str = "[Error] Failed to open settings file: {e}"
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

    from backend.developer_settings import user_settings_path
    from backend.DONT_CHANGE.scripts.common_code import (
        input_warn,
        print_traceback,
        print_warn,
        set_terminal_colors,
    )
    from backend.DONT_CHANGE.scripts.generic_helpers import (
        close_terminal,
        enable_unminimize_and_foreground_terminal_on_first_print,
        make_abs_path_relative_to_file,
        open_in_editor,
    )
    from backend.DONT_CHANGE.settings.backend_settings import DEV_SETTINGS_PATH

    # ==============================
    # local variables

    # ==============================
    # local functions/classes

    # ==============================
    # main function

    def main() -> None:
        """Open the optional settings file after resolving its configured path."""
        set_terminal_colors()
        enable_unminimize_and_foreground_terminal_on_first_print()

        if not user_settings_path:
            print_warn(
                f'[Info] Can\'t open settings file because user_settings_path is disabled in "{DEV_SETTINGS_PATH}".'
            )
            input_warn("Press enter to exit.")
            return

        path = make_abs_path_relative_to_file(user_settings_path, DEV_SETTINGS_PATH)
        if not os.path.exists(path):
            print_warn(f'[Error] User settings file ("{path}") does not exist.')
            input_warn("Press enter to exit.")
            return

        open_in_editor(path)

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
