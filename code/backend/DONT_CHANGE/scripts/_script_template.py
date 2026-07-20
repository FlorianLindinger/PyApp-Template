"""WIP"""

# {e} will be formatted to exception:
fail_message = "[Error] Failed WIP: {e}"

try:
    # ==============================
    # import Python packages
    # ==============================

    import os
    import sys

    # ==============================
    # import third-party packages
    # ==============================

    # ==============================
    # imports from files
    # ==============================

    # add root dir to resolve file imports for debug cases where this script is called on its own:
    root_dir = os.path.dirname(__file__) + "\\..\\..\\.."
    if root_dir not in sys.path:
        sys.path.insert(0, root_dir)

    from backend.DONT_CHANGE.scripts._common_code import (
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
            print_traceback(fail_message.format(e=e))  # WIP function to be in new terminal?
            input_warn("[Error] Press enter to exit")
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
    os._exit(1)  # instead of sys.exit(1) to prevent exception by script calling this script
