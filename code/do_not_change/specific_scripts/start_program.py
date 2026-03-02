# todo: docstring


# ==========================================================================
#   Local Variables
# ==========================================================================

import os

file_dir = os.path.dirname(os.path.abspath(__file__)) + "\\"
python_scripts_folder_path = os.path.normpath(file_dir + "..\\..\\")
local_python_exe_for_script_path = os.path.normpath(file_dir + "..\\..\\py_env\\virt_env\\portable_Scripts\\python.bat")
settings_file_path = os.path.normpath(file_dir + "..\\..\\non-user_settings.ini")
icon_path = os.path.normpath(file_dir + "..\\..\\icons\\icon.ico")
stylesheet_path = os.path.normpath(file_dir + "..\\terminal_emulator\\terminal_style.qss")
compiled_terminal_path = os.path.normpath(file_dir + "..\\terminal_emulator\\compiled\\run.exe")
uncompiled_terminal_path = os.path.normpath(file_dir + "..\\terminal_emulator\\terminal_emulator.py")
if python_scripts_folder_path != "" and python_scripts_folder_path[-1] != "\\":
    python_scripts_folder_path += "\\"

# =============================
# Terminal Appearance
# =============================

# ANSI Color Codes

RED = "\033[91m"
GREEN = "\033[92m"
RESET = "\033[0m"

# =============================
# Imports
# =============================

import subprocess
import sys

# move to dir of this file and add it to sys.path for import of helper_functions
file_path = os.path.dirname(os.path.abspath(__file__))
if file_path not in sys.path:
    sys.path.insert(0, str(file_path))
os.chdir(file_path)

from helper_functions import (
    error_catcher_wrapper_template,
    format_path,
    get_python_interpreter,
    print_error_in_new_terminal,
    read_key_value_file,
    set_app_id,
    set_terminal_name,
    setting_is_true,
)


# =============================
# Main Function
# =============================
def main() -> None:

    # process args

    if len(sys.argv) > 2:
        create_terminal = bool(sys.argv[2])

    else:
        create_terminal = True

    if len(sys.argv) > 1:
        app_id = sys.argv[1]

    else:
        app_id = ""

    # raise error if settings file not found

    if not os.path.exists(settings_file_path):
        raise FileNotFoundError(f'[Error] Settings file not found at "{format_path(settings_file_path)}"')

    # import and process non-user_settings

    s = read_key_value_file(settings_file_path)

    use_fancy_terminal = setting_is_true(s, "use_fancy_terminal", True)

    terminal_needs_input = setting_is_true(s, "terminal_needs_input", True)

    close_on_success = setting_is_true(s, "close_on_success", True)

    close_on_crash = setting_is_true(s, "close_on_crash", False)

    close_on_failure = setting_is_true(s, "close_on_failure", False)

    use_uncompiled_terminal_and_run_it_in_global = setting_is_true(
        s, "use_uncompiled_terminal_and_run_it_in_global", False
    )

    wdir_is_script_dir = not setting_is_true(s, "start_in_shortcut_folder", False)

    if "program_name" in s:
        title = s["program_name"]

    else:
        title = "Terminal"  # default value

    use_global_python = setting_is_true(s, "use_global_python", False)

    if use_global_python == True:
        python_exe_for_script_path = "py"

    else:
        python_exe_for_script_path = format_path(local_python_exe_for_script_path)

        # raise error if python or script or settings not found

        if not os.path.exists(python_exe_for_script_path):
            raise FileNotFoundError(f'[Error] Python executable/command not found at "{python_exe_for_script_path}"')

    if "python_code_name" in s:
        python_code_name = s["python_code_name"]

        script_path = python_scripts_folder_path + python_code_name

    else:
        raise ValueError(f'[Error] Setting "python_code_name" not found in "{format_path(settings_file_path)}"')

    # raise error if script not found

    if not os.path.exists(script_path):
        raise FileNotFoundError(f'[Error] Python script not found at "{script_path}"')

    # ======================

    # launch terminal

    # run main python script in windowless or termnial emulator or windows terminal

    if (use_fancy_terminal == True) and (create_terminal == True):  # run in termnial emulator
        try:
            if use_uncompiled_terminal_and_run_it_in_global == True:
                subprocess.Popen(  # noqa:S603
                    [
                        "pyw",
                        uncompiled_terminal_path,
                        script_path,
                        python_exe_for_script_path,
                        title,
                        icon_path,
                        app_id,
                    ],
                    creationflags=subprocess.CREATE_NEW_CONSOLE,
                )

            else:
                set_app_id(app_id)

                args = [
                    python_exe_for_script_path,
                    script_path,
                    "1" if wdir_is_script_dir else "0",
                    "1" if close_on_success else "0",
                    "1" if close_on_failure else "0",
                    "1" if close_on_crash else "0",
                    "1" if terminal_needs_input else "0",
                    title,
                    icon_path if icon_path else "",
                    stylesheet_path,
                ]

                # run and wait (using the compiled terminal emulator)

                subprocess.run([compiled_terminal_path, *args], check=True)  # noqa:S603

        except Exception as e:
            # dont use "close_on_crash" setting since this crash is not crash of python script

            print_error_in_new_terminal(e)

            sys.exit(1)

    else:
        # The 'error_catcher_wrapper' code to run inside the new window

        error_catcher_wrapper = error_catcher_wrapper_template.format(
            python_exe_for_script_path=python_exe_for_script_path,
            script_path=script_path,
            close_on_crash=close_on_crash,
            close_on_failure=close_on_failure,
            close_on_success=close_on_success,
            wdir_is_script_dir=wdir_is_script_dir,
            RED=repr(RED),
            GREEN=repr(GREEN),
            RESET=repr(RESET),
        )

        # launch this error_catcher_wrapper (handles exceptions/prints/prompts) in the new console

        python_exe = get_python_interpreter()

        if not python_exe:
            # If no python is found, we at least try to show the error in a box

            # or print it before failing.

            print("[Error] No Python interpreter found to launch the terminal wrapper.")

            sys.exit(1)

        if create_terminal == True:  # run in windows terminal
            p = subprocess.Popen([python_exe, "-c", error_catcher_wrapper], creationflags=subprocess.CREATE_NEW_CONSOLE)  # noqa:S603

        else:  # run without terminal but create one on crash.
            p = subprocess.Popen([python_exe, "-c", error_catcher_wrapper], creationflags=subprocess.CREATE_NEW_CONSOLE)  # noqa:S603

        set_terminal_name(title)  # change terminal title

        p.wait()  # wait for file to finish

        # return (SystemExit does not raise Exception)

        sys.exit(p.returncode)


# ====================================
#      execution of main function
# ====================================


if __name__ == "__main__":
    try:
        main()

    except Exception as e:
        # print error in new terminal (because this script might be launched without terminal)

        print_error_in_new_terminal(e)

        # return with errorcode 1

        sys.exit(1)
