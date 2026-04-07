# todo: docstring


# =============================
# local variables
# =============================

try:
    import os

    file_dir = os.path.dirname(os.path.abspath(__file__)) + "\\"

    python_scripts_folder_path = os.path.normpath(file_dir + "..\\..\\")
    icon_path = os.path.normpath(file_dir + "..\\..\\icons\\icon.ico")
    stylesheet_path = os.path.normpath(file_dir + "..\\terminal_emulator\\terminal_style.qss")
    compiled_terminal_path = os.path.normpath(file_dir + "..\\terminal_emulator\\compiled\\run.exe")
    uncompiled_terminal_path = os.path.normpath(file_dir + "..\\terminal_emulator\\terminal_emulator.py")

    # =============================
    # imports
    # =============================

    import subprocess
    import sys

    # =============================
    # import from helper_functions
    # =============================

    file_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.normpath(file_dir + "\\..\\..")
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    from do_not_change.specific_scripts.helper_functions import (
        backend_python_exe_path,
        backend_pythonw_exe_path,
        error_print,
        format_path,
        get_value,
        input_red,
        script_wrapper_path,
        settings,
        settings_file_path,
        setup_venv,
        val_is_true,
        venv_exe_path,
    )

    # =============================
    # process local variables
    # =============================

    if python_scripts_folder_path != "" and python_scripts_folder_path[-1] != "\\":
        python_scripts_folder_path += "\\"

    # =============================
    # main function
    # =============================

    def main() -> None:

        # process args

        if len(sys.argv) > 1:
            app_id = sys.argv[1]
        else:
            app_id = ""

        if len(sys.argv) > 2:
            create_terminal = sys.argv[2] == "1"  # inputs are 0 or 1
        else:
            create_terminal = True

        # ======================
        # setup venv: install python distribution if not existatant and venv. Also recreate if the target python version is not dist version

        setup_venv()

        # =============================
        # import and process non-user_settings

        use_fancy_terminal = val_is_true(settings, "use_fancy_terminal", True)
        terminal_needs_input = val_is_true(settings, "terminal_needs_input", True)
        close_on_success = val_is_true(settings, "close_on_success", True)
        close_on_crash = val_is_true(settings, "close_on_crash", False)
        close_on_failure = val_is_true(settings, "close_on_failure", False)
        use_uncompiled_terminal_and_run_it_in_global = val_is_true(
            settings, "use_uncompiled_terminal_and_run_it_in_global", False
        )
        wdir_is_script_dir = not val_is_true(settings, "start_in_shortcut_folder", False)
        use_global_python = val_is_true(settings, "use_global_python", False)
        log_even_with_terminal = val_is_true(settings, "log_even_with_terminal", True)
        restart_main_code_on_crash = val_is_true(settings, "restart_main_code_on_crash", False)

        title = get_value(settings, "program_name", "Terminal")
        log_path_rel_to_wdir = get_value(settings, "log_path_rel_to_wdir", "..\\log.txt")
        terminal_bg_color = get_value(settings, "terminal_bg_color", "0")
        terminal_text_color = get_value(settings, "terminal_text_color", "F")
        terminal_colors = terminal_bg_color + terminal_text_color

        fancy_terminal_stylesheet_path = get_value(settings, "fancy_terminal_stylesheet_path", "")
        fancy_terminal_accent_color_hex = get_value(settings, "fancy_terminal_accent_color_hex", "")

        if "python_code_name" in settings:
            python_code_name = settings["python_code_name"]
        else:
            raise ValueError(f'[Error] Setting "python_code_name" not found in "{format_path(settings_file_path)}"')

        script_path = python_scripts_folder_path + python_code_name
        # raise error if script not found
        if not os.path.exists(script_path):
            raise FileNotFoundError(f'[Error] Python script not found at "{script_path}"')

        if use_global_python == True:
            python_exe_for_script_path = "py"
        else:
            # raise error if python or script or settings not found
            if not os.path.exists(venv_exe_path):
                raise FileNotFoundError(f'[Error] Python executable not found at "{venv_exe_path}"')
            python_exe_for_script_path = venv_exe_path

        after_python_crash_code_name = get_value(settings, "after_python_crash_code_name", "")
        if after_python_crash_code_name != "":
            after_python_crash_code_path = python_scripts_folder_path + after_python_crash_code_name
            if not os.path.exists(after_python_crash_code_path):
                after_python_crash_code_path = ""
        else:
            after_python_crash_code_path = ""

        # ======================
        # launch terminal

        args = [
            title,
            icon_path if icon_path else "",
            app_id,
            "1" if wdir_is_script_dir else "0",
            "1" if close_on_crash else "0",
            "1" if close_on_failure else "0",
            "1" if close_on_success else "0",
            log_path_rel_to_wdir,
            # restart_main_code_on_crash,
            # after_python_crash_code_path
        ]

        if (use_fancy_terminal == True) and (create_terminal == True):
            # run in termnial emulator

            # terminal emulator need additional arg python_exe_for_script_path
            args += [
                fancy_terminal_accent_color_hex,
                "1" if terminal_needs_input else "0",
                fancy_terminal_stylesheet_path,
            ]

            if use_uncompiled_terminal_and_run_it_in_global == True:
                subprocess.Popen(  # noqa:S603
                    ["pyw", uncompiled_terminal_path, script_path, python_exe_for_script_path, *args],
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
            else:
                # run and wait (using the compiled terminal emulator)
                subprocess.Popen(  # noqa:S603
                    [compiled_terminal_path, script_path, python_exe_for_script_path, *args],
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )

        else:
            # run in Windows terminal or no window

            # script_wrapper_path need addition args
            args += [terminal_colors, "1" if create_terminal else "0", backend_python_exe_path]

            # launch script in wrapper that handles:
            #   errors
            #   return
            #   icon setting
            #   terminal-renaming
            #   working dir setting
            #   app-id setting
            #   closer or keep open logic on finish/error/fail
            #   print in additional terminal for final print info if in no-terminal mode
            if create_terminal == True:  # run in windows terminal
                subprocess.Popen(  # noqa:S603
                    [python_exe_for_script_path, script_wrapper_path, script_path, *args],
                    creationflags=subprocess.CREATE_NEW_CONSOLE,
                )
            else:  # run without terminal but create one on crash.
                subprocess.Popen(  # noqa:S603
                    [python_exe_for_script_path, script_wrapper_path, script_path, *args],
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )

    # =============================
    # execution of main function
    # =============================

    if __name__ == "__main__":
        try:
            main()
            sys.exit(0)

        except Exception as e:
            error_print(f"[Error] Failed to launch the program: {e}", red=True)
            input_red("Press Enter to exit...")
            sys.exit(1)

except Exception as e:
    import sys
    import traceback

    print(f"[Error] Failed during start of program with error: {e}:")
    print("=" * 20)
    print(traceback.format_exc())
    print("=" * 20)
    input("Press enter to exit")
    sys.exit(1)
