"""WIP"""

# ==============================
# settings

fail_message: str = "[Error] Failed to run reset_packages -default: {e}"
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
        delete_frontend_packages,
        ensure_python_distro,
        install_packages_from_file,
        print_traceback,
    )
    from backend.DONT_CHANGE.scripts.generic_helpers import (
        close_terminal,
        input_success,
        input_warn,
    )
    from backend.DONT_CHANGE.settings.backend_settings import DEFAULT_PACKAGES_PATH

    # ==============================
    # local variables

    # ==============================
    # local functions/classes

    # ==============================
    # main function

    def main() -> None:
        ensure_python_distro()
        delete_frontend_packages()
        install_packages_from_file(DEFAULT_PACKAGES_PATH)
        print()
        input_success("[Success] Press enter to exit")

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
