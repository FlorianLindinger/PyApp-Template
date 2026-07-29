"""WIP"""

try:
    # ==========================================================================
    # package imports

    import os
    import sys

    # ==========================================================================
    # add root dir for debug cases where this script is called on its own

    root_dir = os.path.dirname(__file__) + "\\..\\..\\..\\.."
    if root_dir not in sys.path:
        sys.path.insert(0, root_dir)

    # ==========================================================================
    # import from common variables and developer settings

    from backend.DONT_CHANGE.scripts.common_code import (
        close_terminal,
        input_warn,
        open_in_editor,
        print_traceback,
        print_warn,
        set_terminal_colors,
        set_unminimize_and_foreground_on_first_print,
    )
    from backend.DONT_CHANGE.settings.backend_settings import MAIN_PY_SCRIPT_PATH

    # =============================
    # script is inteded to be launched minimized and will un minimize on frist print/error

    set_terminal_colors()
    set_unminimize_and_foreground_on_first_print()

    # =============================

    if not os.path.exists(MAIN_PY_SCRIPT_PATH):
        print_warn(f'[Error] main.py file ("{MAIN_PY_SCRIPT_PATH}") does not exist.')
        input_warn("Press enter to exit.")
    else:
        try:
            open_in_editor(MAIN_PY_SCRIPT_PATH)
        except Exception:
            print_traceback(f'[Error] Failed to open main.py file "{MAIN_PY_SCRIPT_PATH}".')
            input_warn("Press enter to exit.")

    close_terminal()

    # =============================

except Exception as e:
    import os
    import traceback

    print()
    print()
    print("=" * 20)
    print(f"[Error] Failed to open main.py file: {e}")
    print("-" * 20)
    print(traceback.format_exc())
    print("=" * 20)
    input("[Error (see above)] Press enter to exit")
    os._exit(1)  # instead of sys.exit(1) to prevent exception by script calling this script
