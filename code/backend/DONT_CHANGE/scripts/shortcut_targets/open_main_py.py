"""Open the project's main.py file in the configured editor."""

# ==============================
# settings

fail_message: str = "[Error] Failed to open main.py file: {e}"
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

    from backend.DONT_CHANGE.scripts.common_code import (
        input_warn,
        print_traceback,
        print_warn,
        set_terminal_colors,
    )
    from backend.DONT_CHANGE.scripts.generic_helpers import (
        close_terminal,
        enable_unminimize_and_foreground_terminal_on_first_print,
        open_in_editor,
    )
    from backend.DONT_CHANGE.settings.backend_settings import MAIN_PY_SCRIPT_PATH

    # ==============================
    # local variables

    # ==============================
    # local functions/classes

    # ==============================
    # main function

    def main() -> None:
        """Open main.py or explain why it cannot be opened."""
        set_terminal_colors()
        enable_unminimize_and_foreground_terminal_on_first_print()

        if not os.path.exists(MAIN_PY_SCRIPT_PATH):
            print_warn(
                f'[Error] main.py file ("{MAIN_PY_SCRIPT_PATH}") does not exist.'
            )
            input_warn("Press enter to exit.")
            return

        open_in_editor(MAIN_PY_SCRIPT_PATH)

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
