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


uncompiled_terminal_path = os.path.normpath(file_dir + r"..\terminal_emulator\terminal_emulator.py")


if python_scripts_folder_path != "" and python_scripts_folder_path[-1] != "\\":
    python_scripts_folder_path += "\\"


# =============================


#      Terminal Appearance


# =============================


# ANSI Color Codes


RED = "\033[91m"


GREEN = "\033[92m"


RESET = "\033[0m"


# =============================


#      Imports


# =============================


import ctypes
import shutil
import subprocess
import sys
import tempfile
import traceback

# =============================


#      Definitions


# =============================


# path related


def format_path(path: str) -> str:
    """Ensures drive letters are capitalized for a more premium look on Windows."""

    abs_path = os.path.abspath(path)

    drive, rest = os.path.splitdrive(abs_path)

    if drive:
        return drive.upper() + rest

    return abs_path


# =============================


# file reading related


def setting_is_true(settings_dict, key, default):

    if key in settings_dict:
        if settings_dict[key].lower() in ("y", "yes", "true", "1"):
            return True

        else:
            return False

    else:
        return default


def read_key_value_file(file_path, key_val_separator="=", comment_chars=("#", ";")):

    key_val_dict = {}

    with open(file_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()

            # Skip empty lines and comments

            if not line or line.startswith(comment_chars):
                continue

            key, value = line.split(key_val_separator, 1)

            key_val_dict[key.strip()] = value.strip()

    return key_val_dict


# =============================


# print related


def wrap_print(msg: str, wrap_character: str = "=", max_len=100):

    size = len(msg)

    if max_len not in [False, None] and size > max_len:
        size = max_len

    print(wrap_character * size)

    print(msg * size)

    print(wrap_character * size)

    return size


def get_python_interpreter() -> str | None:
    """Returns a valid Python executable path or command."""

    interpreters = []

    # If compiled, check global paths defined during setup

    if "__compiled__" in globals():
        # These are usually defined at the top level of this module

        # Note: We use globals() access because they might not be passed as args

        potential_runtime = globals().get("python_exe_for_setup_path")

        if potential_runtime and os.path.exists(potential_runtime):
            interpreters.append(potential_runtime)

    else:
        # In source mode, current executable is fine

        interpreters.append(sys.executable)

    # Fallback to common system names

    interpreters.extend(["py", "python", "python3"])

    for interp in interpreters:
        if os.path.isabs(interp):
            if os.path.exists(interp):
                return interp

        else:
            if shutil.which(interp):
                return interp

    return None


def print_error_in_new_terminal(
    exception,
    key_press_prompt_message="[Error] Press Enter to exit",
    window_title="Error",
    bg_color="4",  # Default: Red
    font_color="E",  # Default: Light Yellow
    wrapping_character="=",
    max_wrapping_length=100,
):

    size = len(str(exception))

    if max_wrapping_length not in [False, None] and size > max_wrapping_length:
        size = max_wrapping_length

    msg = wrapping_character * size + "\n"

    msg += str(exception) + "\n"

    msg += wrapping_character * size + "\n"

    msg += traceback.format_exc()

    msg += wrapping_character * size + "\n"

    print_msg_in_new_terminal(
        msg=msg,
        key_press_prompt_message=key_press_prompt_message,
        window_title=window_title,
        bg_color=bg_color,
        font_color=font_color,
    )


def print_msg_in_new_terminal(
    msg: str,
    key_press_prompt_message="Press Enter to exit",
    window_title="Message",
    bg_color="0",  # Default: Black
    font_color="7",  # Default: White
) -> None:
    """


    Spawns a new terminal.


    bg_color/fg_color use Windows CMD hex codes (0-f).
    """

    with tempfile.NamedTemporaryFile("w", delete=False, suffix=".txt", encoding="utf-8") as f:
        path = f.name

        f.write(msg)

    # Combine hex codes for the 'color' command

    color_code = f"{bg_color}{font_color}"

    child_code = f"""


import sys, pathlib, os, ctypes


# Set Window Title


ctypes.windll.kernel32.SetConsoleTitleW("{window_title}")



# Set Global Colors and Refresh Screen


os.system('color {color_code}')


os.system('cls')



p = pathlib.Path(sys.argv[1])


try:


    print(p.read_text(encoding="utf-8", errors="replace"))


finally:


    try: os.remove(p)


    except OSError: pass

print()


input("{key_press_prompt_message}")
"""

    python_exe = get_python_interpreter()

    if python_exe:
        subprocess.Popen(  # noqa:S603
            [python_exe, "-c", child_code, path],
            creationflags=subprocess.CREATE_NEW_CONSOLE,
            close_fds=True,
        )

    else:
        # Fallback if no Python is found - create a batch file to show the message

        bat_content = f'@echo off\ntitle {window_title}\ncolor {color_code}\ncls\ntype "{path}"\necho.\npause'

        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".bat", encoding="utf-8") as bf:
            bat_path = bf.name

            bf.write(bat_content)

        subprocess.Popen(  # noqa:S603
            [bat_path],
            creationflags=subprocess.CREATE_NEW_CONSOLE,
            close_fds=True,
        )

        # We can't easily auto-delete the .bat file while it's running,

        # but it's in temp and small.


# =============================


# Windows terminal related


def set_terminal_name(name: str) -> None:
    """Safely set the terminal title using Windows API."""

    try:
        # Clean the name

        safe_name = name.replace("\n", "").replace("\r", "")

        if os.name == "nt":
            ctypes.windll.kernel32.SetConsoleTitleW(safe_name)

        elif sys.stdout.isatty():
            sys.stdout.write(f"\033]0;{safe_name}\007")

            sys.stdout.flush()

    except Exception:
        pass


def get_terminal_name():

    # Create a buffer to hold the text

    buffer = ctypes.create_unicode_buffer(1024)

    # Get the title

    ctypes.windll.kernel32.GetConsoleTitleW(buffer, len(buffer))

    return buffer.value


# =============================


# wrapper code


error_catcher_wrapper_template = r"""


import subprocess, sys, ctypes, traceback, os



RED = {RED}


GREEN = {GREEN}


RESET = {RESET}


python_exe_for_script_path = r"{python_exe_for_script_path}"


script_path = r"{script_path}"


args = {remaining_args}


close_on_crash = {close_on_crash}


close_on_failure = {close_on_failure}


close_on_success = {close_on_success}


wdir_is_script_dir = {wdir_is_script_dir}



def print_red(msg):


    print(f"{{RED}}{{msg}}{{RESET}}")


def input_red(msg):


    input(f"{{RED}}{{msg}}{{RESET}}")


def input_green(msg):


    input(f"{{GREEN}}{{msg}}{{RESET}}")



def set_terminal_name(name: str) -> None:


    try:


        #Clean the name


        safe_name = name.replace("\n", "").replace("\r", "")
        


        if os.name == "nt":


            ctypes.windll.kernel32.SetConsoleTitleW(safe_name)


        elif sys.stdout.isatty():


            sys.stdout.write(f"\033]0;{{safe_name}}\007")


            sys.stdout.flush()


    except Exception:
        pass



def get_terminal_name():


    try:


        buffer = ctypes.create_unicode_buffer(1024)


        ctypes.windll.kernel32.GetConsoleTitleW(buffer, len(buffer))


        return buffer.value


    except Exception:


        return "Terminal"



try:


    if wdir_is_script_dir == True:


        cwd=os.path.dirname(script_path)


    else:


        cwd=None
    


    result = subprocess.run(


        [python_exe_for_script_path, script_path] + args,


        cwd=cwd
    )
    


    if result.returncode == 0:


        if close_on_success:


            sys.exit(0)


        else:


            set_terminal_name(f"[Success] {{get_terminal_name()}}")
            print()


            input_green("[Success] Press Enter to exit.")


    else:


        if close_on_failure:


            sys.exit(result.returncode)


        else:


            set_terminal_name(f"[Failure] {{get_terminal_name()}}")
            print()


            print_red(f"[Failure] Script exited with code: {{result.returncode}}")


            input_red("[Python Failure Return] Press Enter to exit.")
            


except Exception as e:


    if close_on_crash:


        sys.exit(1)


    else:


        set_terminal_name(f"[Crash] {{get_terminal_name()}}")
        print()


        print_red("="*40)


        print_red(f"CRITICAL LAUNCH ERROR: {{e}}")


        print_red("="*40)


        traceback.print_exc()


        print_red("="*40)


        print(f"[Info] Python Exe/Command: {{python_exe_for_script_path}}")


        print(f"[Info] Script: {{script_path}}")
        print()


        input_red("[Python Crash] See above. Press Enter to exit.")
"""


# =============================


# miscellaneous


def set_app_id(app_id) -> None:
    """Needed for grouping behavor in taskbar. Seems to only work for QT Windows"""

    if not app_id:
        return

    if os.name != "nt":
        return

    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)

    except Exception:
        pass


# ====================================


#    definition of main function


# ====================================


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
