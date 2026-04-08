import os
import shutil
import subprocess
import sys
import traceback
from pathlib import Path

#############################


#############################
# local variables (might also be imported by callers)

file_dir = os.path.dirname(os.path.abspath(__file__)) + "\\"

developer_settings_path = os.path.normpath(file_dir + "..\\..\\developer_settings.py")

portable_python_installer_path = os.path.normpath(file_dir + "..\\general_scripts\\create_portable_python.bat")
portable_venv_creator_path = os.path.normpath(file_dir + "..\\general_scripts\\create_portable_venv.bat")

py_env_folder_path = os.path.normpath(file_dir + "..\\..\\py_env")

backend_python_exe_path = os.path.normpath(file_dir + "..\\P\\P.exe")
backend_pythonw_exe_path = os.path.normpath(file_dir + "..\\P\\Pw.exe")

script_wrapper_path = file_dir + "script_wrapper.py"

#############################
# process local variables

sys.path.insert(0, os.path.dirname(developer_settings_path))
import developer_settings

python_dist_path = py_env_folder_path + "\\py_dist"
venv_dir_path = py_env_folder_path + "\\virt_env"
venv_exe_path = venv_dir_path + "\\Portable_Scripts\\python.bat"

#############################
# file related/path related


def delete_folder_safe(
    target: str | Path,
    *,
    prompt_message="Delete this folder? [y/n]: ",
    allowed_base: str | Path,
    prompt_for_confirmation=True,
):
    """
    Safely delete a folder after showing its size and prompting the user.

    Returns True if deleted, False if cancelled.

    Safety features:
    - resolves absolute paths
    - target must exist and be a directory
    - target must be inside allowed_base
    - refuses to delete allowed_base itself
    - refuses to delete filesystem roots
    - shows folder size before deletion
    - asks for confirmation
    """

    target_path = Path(target).resolve()
    base_path = Path(allowed_base).resolve()

    if not base_path.exists():
        raise FileNotFoundError(f"Allowed base does not exist: {base_path}")

    if not base_path.is_dir():
        raise NotADirectoryError(f"Allowed base is not a directory: {base_path}")

    if not target_path.exists():
        raise FileNotFoundError(f"Target does not exist: {target_path}")

    if not target_path.is_dir():
        raise NotADirectoryError(f"Target is not a directory: {target_path}")

    if target_path == target_path.anchor:
        raise ValueError(f"Refusing to delete filesystem root: {target_path}")

    if target_path == base_path:
        raise ValueError("Refusing to delete the allowed base directory itself")

    if base_path not in target_path.parents:
        raise ValueError(
            f"Refusing to delete directory outside allowed base.\nTarget: {target_path}\nAllowed base: {base_path}"
        )

    size_bytes = get_folder_size(target_path)
    size_text = format_bytes(size_bytes)

    if prompt_for_confirmation:
        print()
        print("Folder deletion request:")
        print(f"Folder: {target_path}")
        # print(f"Allowed base: {base_path}")
        print(f"Folder size: {size_text}")
        print()
        answer = input(prompt_message).strip().lower()
        if answer not in {"y", "yes"}:
            print("Cancelled folder deletion.")

    shutil.rmtree(target_path)


def get_folder_size(folder: Path) -> int:
    total = 0
    for p in folder.rglob("*"):
        try:
            if p.is_file():
                total += p.stat().st_size
        except (OSError, PermissionError):
            # Skip unreadable files when estimating size.
            pass
    return total


def format_path(path: str) -> str:
    """Ensures drive letters are capitalized for a more premium look on Windows."""
    abs_path = os.path.abspath(path)
    drive, rest = os.path.splitdrive(abs_path)
    if drive:
        return drive.upper() + rest
    return abs_path


def make_abs_path_relative_to_file(path, file):
    """makes a path absolute if relative with respect to the file (as if the file defined it)"""
    if not os.path.isabs(path):
        return os.path.normpath(os.path.dirname(file) + "\\" + path)
    else:
        return path


#############################
# string related
#############################


def format_bytes(num_bytes) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    size = float(num_bytes)
    for unit in units:
        if size < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{int(size)} {unit}"
            else:
                return f"{size:.2f} {unit}"
        size /= 1024
    return f"{num_bytes} B"


#############################
# print related functions
#############################


def error_print(message, max_wrapper_len=20, wrapper_symbol="=", red=False):
    msg_len = len(message)
    if msg_len > max_wrapper_len:
        msg_len = max_wrapper_len
    if red == True:
        print(f"\033[91m{wrapper_symbol * msg_len}")
    else:
        print(wrapper_symbol * msg_len)
    print(message)
    print(wrapper_symbol * msg_len)
    print(traceback.format_exc(), end="")
    if red == True:
        print(f"{wrapper_symbol * msg_len}\033[0m")
    else:
        print(wrapper_symbol * msg_len)


#############################
# settings related functions
#############################


# def val_is_true(dictionay, key, default=None):
#     """Returns True if the key exists in dictionay and its value is a truthy string, otherwise returns False or the default."""
#     if key in dictionay:
#         if dictionay[key].lower() in ("y", "yes", "true", "1"):
#             return True
#         else:
#             return False
#     else:
#         return default


# def get_settings(settings_path: str) -> dict:
#     if not os.path.exists(settings_path):
#         raise FileNotFoundError(f"[Error] Settings file not found at: {settings_path}")
#     config = configparser.ConfigParser(interpolation=None)
#     try:
#         with open(settings_path, encoding="utf-8") as f:
#             config.read_string("[DEFAULT]\n" + f.read())
#         return dict(config["DEFAULT"])
#     except Exception as e:
#         raise ValueError(f"[Error] Failed to parse settings: {e}") from e


# def get_value(dictionary: dict, key: str, default: str) -> str:
#     if key in dictionary:
#         return dictionary[key]
#     else:
#         return default


#############################
# user interaction related functions
#############################


def input_red(msg):
    input(f"\033[91m{msg}\033[0m")


def open_in_editor(path):
    try:
        if not os.path.exists(path):
            print(f"Could not find file at path: {path}")
        vscode_exe_path = shutil.which("code")
        if vscode_exe_path is not None:
            subprocess.Popen([vscode_exe_path, path])  # noqa:S603
        else:
            # Fallback
            subprocess.Popen(["notepad.exe", path])  # noqa:S603
    except Exception as _e:
        print(traceback.format_exc())


#############################
# python related functions
#############################


def check_python_version(target_version: str | float, exe_path: str = "py") -> bool:
    """
    Return whether the Python executable at ``exe_path`` matches ``target_version``.

    Matching is prefix-based on proven version components:
    - If ``target_version`` is ``"3"``, any Python 3.x matches.
    - If ``target_version`` is ``"3.13"``, any Python 3.13.x matches.
    - If ``target_version`` is ``"3.13.2"``, only Python 3.13.2 matches.

    In other words, the executable's version only needs to match as far as
    ``target_version`` specifies.

    Returns:
    - ``True`` if ``exe_path`` is a valid Python executable and its version matches
      ``target_version`` up to the precision provided there.
    - ``False`` if ``exe_path`` is a valid Python executable but its version does not match.

    By default, ``exe_path="py"`` uses the global Python launcher that would also be
    chosen when running ``py`` in Command Prompt.
    """
    if isinstance(target_version, (float, int)):
        target_version = str(target_version)

    output = subprocess.check_output(  # noqa: S603
        [
            exe_path,
            "-c",
            "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')",
        ],
        stderr=subprocess.STDOUT,
        text=True,
    ).strip()

    actual_parts = output.split(".")
    target_parts = target_version.strip().split(".")

    if (len(actual_parts) != 3) or (any(not part.isdigit() for part in actual_parts)):
        raise ValueError(f"Could not determine Python version from output: {output}. Expected format like '3.13.2'.")

    if not target_parts or any(not part.isdigit() for part in target_parts):
        raise ValueError(
            f"Invalid target_version format: {target_version}. Must be a string like '3', '3.13', or '3.13.2'."
        )

    return actual_parts[: len(target_parts)] == target_parts


#############################
# python/venv installing related
#############################


def delete_venv():
    if os.path.exists(venv_dir_path):
        try:
            delete_folder_safe(venv_dir_path, prompt_for_confirmation=False, allowed_base=Path(file_dir).parent.parent)
        except Exception as e:
            print(f"[Error] Failed to delete virtual environment: {e}.")
            print(f'Delete manually after confirming it is the correct one at "{venv_dir_path}" and restart.')
            print("Pressed Enter to exit.")
            input()


def delete_python_dist():
    if os.path.exists(python_dist_path):
        try:
            delete_folder_safe(
                python_dist_path, prompt_for_confirmation=False, allowed_base=Path(file_dir).parent.parent
            )
        except Exception as e:
            print(f"[Error] Failed to delete Python distribution: {e}.")
            print(f'Delete manually after confirming it is the correct one at "{python_dist_path}" and restart.')
            print("Pressed Enter to exit.")
            input()


def create_portable_python():

    python_version = getattr(developer_settings, "python_version", "") or ""

    # find what optional subparts of full python to install
    install_tkinter = "1" if getattr(developer_settings, "install_tkinter", True) else "0"
    install_tests = "1" if getattr(developer_settings, "install_tests", False) else "0"
    install_tools = "1" if getattr(developer_settings, "install_tools", False) else "0"
    install_docs = "0"

    # run a batch file to install portable python and wait for finish
    try:
        subprocess.run(  # noqa:S603
            [
                "cmd",
                "/c",
                "call",
                portable_python_installer_path,
                python_version,
                py_env_folder_path,  # scripts adds py_dist
                install_tkinter,
                install_tests,
                install_tools,
                install_docs,
            ],
            check=True,
        )
    except Exception as e:
        error_print(f"[Error] Portable Python installation failed: {e}")
        input("Press Enter to exit.")
        sys.exit(1)

    if not os.path.exists(python_exe_path):
        error_print(f'[Error] Portable Python installation did not produce expected file at "{python_exe_path}"')
        input("Press Enter to exit.")
        sys.exit(1)


def create_portable_venv():
    try:
        # run a batch file to install portable python and wait for finish
        subprocess.run(  # noqa:S603
            [
                "cmd",
                "/c",
                "call",
                portable_venv_creator_path,
                py_env_folder_path,  # scripts adds py_venv
                relative_venv_to_python_dist,
            ],
            check=True,
        )
    except Exception as e:
        error_print(f"[Error] Creation of portable virtual environment failed: {e}")
        input("Press Enter to exit.")
        sys.exit(1)

    if not os.path.exists(venv_exe_path):
        error_print(
            f'[Error] Creation of portable virtual environment did not produce expected file at "{venv_exe_path}"'
        )
        input("Press Enter to exit.")
        sys.exit(1)


def setup_venv():
    """Makes sure the venv exists and has correct version, if not it creates it. It does not activate it as one is expected to run the venv exe"""
    
    wanted_python_version=getattr(developer_settings,"python_version","")

    if not os.path.exists(python_exe_path):
        # python distribution not found case -> install python and delete venv if exists to renew it

        print(
            "\n" * 3
        )  # because the batch called in create_portable_python() hides the top of the terminal in between.
        print("[Info] Python distribution not found. Installing portable Python and creating virtual environment:")

        delete_python_dist()
        create_portable_python()
        delete_venv()
        print("[Info] Creating virtual environment:")
        create_portable_venv()

    else:  # python distribution existing case
        match = check_python_version(target_version=wanted_python_version, exe_path=python_exe_path)

        if match:
            if not os.path.exists(venv_exe_path):
                print("[Info] Virtual environment not found. Creating portable virtual environment:")
                delete_venv()
                create_portable_venv()
        else:
            print(
                "\n" * 3
            )  # because the batch called in create_portable_python() hides the top of the terminal in between.
            print(
                "Installed Python version does not match target version. Reinstalling Python distribution and recreating virtual environment:"
            )
            delete_python_dist()
            create_portable_python()
            delete_venv()
            print("[Info] (Re)Creating virtual environment:")
            create_portable_venv()


#############################
# process local variables that are also imported by callers

python_exe_path = os.path.normpath(python_dist_path + "\\python.exe")
relative_venv_to_python_dist = os.path.relpath(python_dist_path, os.path.dirname(venv_dir_path))
