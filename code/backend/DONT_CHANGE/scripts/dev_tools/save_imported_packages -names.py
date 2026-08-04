"""WIP"""

# ==============================
# settings

fail_message: str = "[Error] Failed to run save_imported_packages -names: {e}"
close_terminal_on_finish: bool = False

import os

root_dir: str = os.path.dirname(__file__) + "\\..\\..\\..\\.."

# ==============================

try:
    # ==============================
    # import Python packages

    import os
    import sys

    # ==============================
    # import third-party packages

    # ==============================
    # import from files

    if root_dir not in sys.path:
        sys.path.insert(0, root_dir)

    from backend.DONT_CHANGE.scripts.common_code import (
        print_traceback,
        save_requirements_of_root_folder_noVersion,
    )
    from backend.DONT_CHANGE.scripts.generic_helpers import (
        close_terminal,
        input_success,
        input_warn,
    )

    # ==============================
    # local variables

    # ==============================
    # local functions/classes

    # ==============================
    # main function

    def main() -> None:
        success, _output_path = save_requirements_of_root_folder_noVersion()
        if success:
            print()
            input_success("[Success] Press enter to exit")
        else:
            raise RuntimeError("Failed to determine needed packages.")

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
