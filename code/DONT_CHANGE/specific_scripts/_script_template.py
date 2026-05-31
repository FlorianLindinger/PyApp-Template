"""WIP"""

# {e} will be formatted to exception:
fail_message = "[Error] Failed to open current log file: {e}"

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
    root_dir = os.path.dirname(__file__) + "\\..\\.."
    if root_dir not in sys.path:
        sys.path.insert(0, root_dir)

    from DONT_CHANGE.specific_scripts.common_code import (
        close_terminal,
        input_warn,
        print_traceback,
        setup_terminal_colors,
        setup_unminimize_and_foreground_on_first_print,
    )

    # ==============================
    # define local variables
    # ==============================

    # ==============================
    # define local functions
    # ==============================

    # ==============================
    # define main function
    # ==============================

    def main() -> None:

        # ==============================
        # code block description

        pass

    # ==============================
    # execute main function
    # ==============================

    if __name__ == "__main__":
        try:
            setup_terminal_colors()
            setup_unminimize_and_foreground_on_first_print()
            main()
        except Exception as e:
            print_traceback(fail_message.format(e=e))
            input_warn("[Error] Press enter to exit")
        close_terminal()

    # ==============================

except Exception as e:
    import os
    import traceback

    print()
    print()
    print("=" * 20)
    print(fail_message.format(e=e))
    print("-" * 20)
    print(traceback.format_exc())
    print("=" * 20)
    input("[Error] Press enter to exit")
    os._exit(1)  # instead of sys.exit(1) to prevent exception by script calling this script
