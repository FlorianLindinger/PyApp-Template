"""{Template for python scripts that are run by the backend python exe. The empty segments are meant to be included even if empty.

This is NOT meant to apply to:
- {python and packages}
- /common_code.py
- /generic_helpers.py
- /shortcut_targets/child_scripts/frontend_scripts/*.py
- /../backend_tools/standin_main_script.py
- /../settings/backend_settings.py
- /../future/**/*.py
- /backend_tools/start_time_dummy_main_script.py"
- /../../developer_settings.py
- /../../../main.py
- /../../../settings.py

}"""

# =========================
# settings

fail_message: str = "[Error] Failed to run {script_name}: {error}"  # "{error}" will be replaced with the error, "{script_name}" with script name
close_terminal_on_finish: bool = True
rel_path_to_root_dir: str = "\\..\\..\\.."  # path to pyproject.json containing folder

# =========================

try:
    # =========================
    # import Python packages

    import os
    import sys

    # =========================
    # import third-party packages

    # =========================
    # import from files

    # add root dir to resolve file imports for debug cases where this script is called on its own:
    ROOT_DIR = os.path.normpath(os.path.dirname(__file__) + rel_path_to_root_dir)
    if ROOT_DIR not in sys.path:
        sys.path.insert(0, ROOT_DIR)

    from backend.DONT_CHANGE.scripts.common_code import (
        print_traceback,
    )
    from backend.DONT_CHANGE.scripts.generic_helpers import close_terminal, get_script_name, input_warn

    # =========================
    # local variables
    # =========================

    # =========================
    # local functions/classes
    # =========================

    # =========================
    # main function
    # =========================

    def main() -> None:
        # =========================
        # {code block description}

        ...

    # =========================
    # execute main function
    # =========================

    if __name__ == "__main__":
        try:
            main()
        except Exception as error:
            print_traceback(fail_message.format(error=error, script_name=get_script_name()))
            if sys.stdin.isatty() and sys.stdout.isatty():  # check if interactive terminal
                input_warn("[Error] Press enter to exit")
        if close_terminal_on_finish:
            close_terminal()

    # =========================

except Exception as error:
    import os
    import sys
    import traceback

    print()
    print()
    print("=" * 30)
    print(fail_message.format(error=error, script_name=__file__.replace("\\", "/").rsplit("/", 1)[-1]))
    print("-" * 30)
    print(traceback.format_exc())
    print("=" * 30)
    if sys.stdin.isatty() and sys.stdout.isatty():  # check if interactive terminal
        input("[Error] Press enter to exit")
    if close_terminal_on_finish:
        os._exit(1)  # instead of sys.exit(1) to prevent exception by script calling this script -> closing terminal
