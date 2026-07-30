"""WIP"""

# ==============================
# settings

fail_message: str = "[Error] Failed WIP: {e}"  # {e} will be formatted to exception
close_terminal_on_finish: bool = True
# path to pyproject.json folder:
import os

root_dir: str = os.path.dirname(__file__) + "\\..\\..\\.."

# ==============================

try:
    # ==============================
    # import Python packages
    # ==============================

    import sys

    # ==============================
    # import third-party packages
    # ==============================

    # ==============================
    # imports from files
    # ==============================

    # add root dir to resolve file imports for debug cases where this script is called on its own:
    if root_dir not in sys.path:
        sys.path.insert(0, root_dir)

    from backend.DONT_CHANGE.scripts.common_code import (
        close_terminal,
        input_warn,
        print_traceback,
    )

    # ==============================
    # define local variables
    # ==============================

    # ==============================
    # define local functions/classes
    # ==============================

    # ==============================
    # define main function
    # ==============================

    def main() -> None:
        # ==============================
        # code block description

        ...

    # ==============================
    # execute main function
    # ==============================

    if __name__ == "__main__":
        try:
            main()
        except Exception as e:
            print_traceback(fail_message.format(e=e))
            input_warn("[Error] Press enter to exit")
        if close_terminal_on_finish:
            close_terminal()

    # ==============================

except Exception as e:
    import os
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
        os._exit(1)  # instead of sys.exit(1) to prevent exception by script calling this script -> closing terminal
