import configparser
import ctypes
import os
import pathlib
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import traceback
import unicodedata
import urllib.request

# ============================


# ==== Core Utility Funcs ====


# ============================



def setting_is_true(settings_dict, key, default):

    if key in settings_dict:
        if settings_dict[key].lower() in ("y", "yes", "true", "1"):
            return True

        else:
            return False

    else:
        return default



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



def format_path(path: str) -> str:
    """Ensures drive letters are capitalized for a more premium look on Windows."""

    abs_path = os.path.abspath(path)

    drive, rest = os.path.splitdrive(abs_path)

    if drive:
        return drive.upper() + rest

    return abs_path

def get_file_dir(__file__):
    """get directory of file that calls this with \\ at end."""

    return os.path.dirname(os.path.abspath(__file__)) + "\\"


def make_abs_relative_to_file(path, file):
    """makes a path absolute if relative with respect to the file (as if the file defined it)"""

    if not os.path.isabs(path):
        return os.path.normpath(os.path.dirname(file) + "\\" + path)

    else:
        return path


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


def sanitize_app_id(input_string):

    # 1. Convert to lowercase and normalize unicode (e.g., convert 'é' to 'e')

    name = unicodedata.normalize("NFKD", input_string).encode("ascii", "ignore").decode("ascii").lower()

    # 2. Replace spaces and underscores with hyphens

    name = re.sub(r"[\s_]+", "-", name)

    # 3. Remove any character that isn't lowercase a-z, 0-9, a hyphen, or a dot

    name = re.sub(r"[^a-z0-9\-\.]", "", name)

    # 4. Remove duplicate hyphens or dots (e.g., "my--app" becomes "my-app")

    name = re.sub(r"-+", "-", name)

    name = re.sub(r"\.+", ".", name)

    # 5. Trim hyphens/dots from the start and end

    name = name.strip("-.")

    return name


def sanitize_filename(filename, replacement="_"):

    # 1. Characters illegal in Windows: < > : " / \ | ? *

    # Also handles control characters (0-31)

    illegal_chars = r'[<>:"/\\|?*\x00-\x1f]'

    filename = re.sub(illegal_chars, replacement, filename)

    # 2. Windows reserved filenames (CON, PRN, AUX, NUL, COM1-9, LPT1-9)

    # These cannot be filenames even with an extension (e.g., CON.txt is bad)

    reserved_names = {
        "CON",
        "PRN",
        "AUX",
        "NUL",
        "COM1",
        "COM2",
        "COM3",
        "COM4",
        "COM5",
        "COM6",
        "COM7",
        "COM8",
        "COM9",
        "LPT1",
        "LPT2",
        "LPT3",
        "LPT4",
        "LPT5",
        "LPT6",
        "LPT7",
        "LPT8",
        "LPT9",
    }

    # Check the "stem" (name before the dot)

    base_name = os.path.splitext(filename)[0].upper()

    if base_name in reserved_names:
        filename = f"{replacement}{filename}"

    # 3. Strip trailing dots and spaces (Windows ignores/removes these)
    filename = filename.rstrip(". ")

    # 4. Enforce length limit (255 characters for the filename itself)

    if len(filename) > 255:
        filename = filename[:255]

    # 5. Handle empty strings (if sanitization removed everything)
    return filename if filename else "unnamed_file"


def get_settings(settings_path: str) -> dict:

    if not os.path.exists(settings_path):
        raise FileNotFoundError(f"[Error] Settings file not found at: {settings_path}")

    config = configparser.ConfigParser(interpolation=None)

    try:
        with open(settings_path, encoding="utf-8") as f:
            config.read_string("[DEFAULT]\n" + f.read())

        return dict(config["DEFAULT"])

    except Exception as e:
        raise ValueError(f"[Error] Failed to parse settings: {e}") from e


def apply_terminal_settings(settings: dict):

    name = settings.get("program_name", "App")

    if os.name == "nt":
        ctypes.windll.kernel32.SetConsoleTitleW(name)

        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(name)

        except Exception:
            pass

        bg = settings.get("terminal_bg_color", "")

        txt = settings.get("terminal_text_color", "")

        if bg or txt:
            os.system(f"color {bg}{txt}")  # noqa:S605

    else:
        sys.stdout.write(f"\x1b]2;{name}\x07")

        sys.stdout.flush()


def prompt_user(message: str) -> bool:

    while True:
        ans = input(f"{message} (y/n): ").lower().strip()

        if ans == "y":
            return True

        if ans == "n":
            return False

        print("Invalid input. Please enter y or n.")


def run_python(python_exe: str, script_path: str, args: list, use_faulthandler: bool = True) -> int:

    cmd = [python_exe]

    if use_faulthandler:
        cmd += ["-X", "faulthandler"]

    cmd += [script_path] + args

    try:
        return subprocess.run(cmd).returncode  # noqa:S603

    except Exception as e:
        print(f"[Error] Python execution failed: {e}")

        return 1


def run_command(cmd: list, shell: bool = False, capture_output: bool = False) -> subprocess.CompletedProcess:

    try:
        return subprocess.run(cmd, shell=shell, capture_output=capture_output, text=True)  # noqa:S603

    except Exception as e:
        print(f"[Error] Command failed: {e}")

        return subprocess.CompletedProcess(cmd, 1)


# ============================


# ==== Domain Logic Funcs ====


# ============================


def stop_program(settings: dict, settings_path: pathlib.Path):

    pid_rel = settings.get("process_id_file_path", "../program.pid")

    pid_path = (settings_path.parent / pid_rel).resolve()

    if not pid_path.exists():
        print(f"[Info] No PID file found at {pid_path}.")
        return

    try:
        with open(pid_path, encoding="utf-8") as f:
            pid = int(f.read().strip())

        print(f"[Info] Stopping process {pid}...")

        if os.name == "nt":
            run_command(["taskkill", "/F", "/T", "/PID", str(pid)], capture_output=True)

        else:
            os.kill(pid, signal.SIGTERM)

        pid_path.unlink(missing_ok=True)

        print("[Success] Process stopped.")

    except Exception as e:
        print(f"[Error] Failed to stop process: {e}")


def launch_background(settings: dict, settings_path: pathlib.Path, launcher_py: pathlib.Path):

    log_rel = settings.get("log_path", "../log.txt")

    pid_rel = settings.get("process_id_file_path", "../program.pid")
    settings_dir = settings_path.parent

    log_path, pid_path = (settings_dir / log_rel).resolve(), (settings_dir / pid_rel).resolve()

    log_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"[Info] Launching {launcher_py.name} in background (Log: {log_path})")

    try:
        with open(log_path, "a", encoding="utf-8") as log_file:
            proc = subprocess.Popen(  # noqa:S603
                [sys.executable, str(launcher_py)],
                stdout=log_file,
                stderr=subprocess.STDOUT,
                cwd=str(launcher_py.parent),
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                start_new_session=True,
            )

            with open(pid_path, "w", encoding="utf-8") as f:
                f.write(str(proc.pid))

        print(f"[Success] Started with PID {proc.pid}")

    except Exception as e:
        print(f"[Error] Background launch failed: {e}")


def activate_and_or_create_venv():

    script_dir = pathlib.Path(__file__).parent.resolve()

    settings_path = (script_dir / "../../non-user_settings.ini").resolve()
    settings = get_settings(settings_path)

    py_env_dir = (settings_path.parent / "py_env").resolve()

    python_dist = py_env_dir / "py_dist"

    python_exe = python_dist / ("python.exe" if os.name == "nt" else "bin/python3")

    venv_dir = py_env_dir / "virt_env"

    target_v = settings.get("python_version", "3.13")

    # 1. Check Python Distribution

    if not python_exe.exists():
        run_python(sys.executable, str(script_dir / "env_install_python.py"), [])

        if not python_exe.exists():
            sys.exit(1)

    # 2. Check Version & Venv

    try:
        print(python_exe)

        curr_v = run_command(
            [str(python_exe), "-c", "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"],
            capture_output=True,
        ).stdout.strip()

        if curr_v != target_v:
            if curr_v == "":
                print("[Warning] Could not determine installed Python version.")

            else:
                print(f"\n[Warning] Version mismatch (current: {curr_v} vs target: {target_v}).")

            if prompt_user("Reinstall Python?"):
                run_python(sys.executable, str(script_dir / "env_install_python.py"), [])

                run_python(sys.executable, str(script_dir / "env_install_venv.py"), [])

        elif not venv_dir.exists():
            run_python(sys.executable, str(script_dir / "env_install_venv.py"), [])

    except Exception as e:
        print(f"[Error] Environment check failed: {e}")

        sys.exit(1)


def find_latest_full_version(ver_input):
    base_url = "https://www.python.org/ftp/python/"
    try:
        req = urllib.request.Request(base_url, headers={"User-Agent": "Mozilla/5.0"})  # noqa:S310
        with urllib.request.urlopen(req) as response:  # noqa:S310
            html = response.read().decode("utf-8")

        pattern = r'href="(\d+\.\d+\.\d+)/"'
        versions = re.findall(pattern, html)

        if ver_input:
            versions = [v for v in versions if v.startswith(ver_input)]

        if not versions:
            return None

        versions.sort(key=lambda s: list(map(int, s.split("."))), reverse=True)

        for v in versions:
            amd64_url = f"{base_url}{v}/amd64/"
            try:
                req_v = urllib.request.Request(amd64_url, headers={"User-Agent": "Mozilla/5.0"})  # noqa:S310
                with urllib.request.urlopen(req_v) as resp:  # noqa:S310
                    if resp.status == 200:
                        return v
            except Exception:
                continue
        return None
    except Exception as e:
        print(f"[Error] Version lookup failed: {e}")
        return None


def download_msi_files(full_ver, download_dir, exclude_pattern):
    base_url = f"https://www.python.org/ftp/python/{full_ver}/amd64/"
    try:
        req = urllib.request.Request(base_url, headers={"User-Agent": "Mozilla/5.0"})  # noqa:S310
        with urllib.request.urlopen(req) as response:  # noqa:S310
            html = response.read().decode("utf-8")

        msi_links = re.findall(r'href="([^"]+\.msi)"', html)
        downloaded = []

        for link in msi_links:
            if link.endswith(("_d.msi", "_pdb.msi")):
                continue

            component_name = link.split(".")[0]
            if re.search(exclude_pattern, component_name, re.I):
                continue

            out_path = download_dir / link
            print(f"Downloading {link}...")
            urllib.request.urlretrieve(base_url + link, out_path)  # noqa:S310
            downloaded.append(out_path)
        return downloaded
    except Exception as e:
        print(f"[Error] Download failed: {e}")
        return []


def extract_msi_files(msi_files, target_dir):
    for msi in msi_files:
        print(f"Extracting {msi.name}...")
        # msiexec is picky about TARGETDIR quoting.
        # Using shell=True and manual quoting for maximum reliability on Windows.
        cmd = f'msiexec /a "{msi}" TARGETDIR="{target_dir}" /qn'
        subprocess.run(cmd, check=True, shell=True)  # noqa:S602
        copied_msi = target_dir / msi.name
        if copied_msi.exists():
            copied_msi.unlink()


def install_portable_python():
    script_dir = pathlib.Path(__file__).parent.resolve()
    settings_path = (script_dir / "../../non-user_settings.ini").resolve()
    settings = get_settings(settings_path)

    py_env_dir = (settings_path.parent / "py_env").resolve()
    python_dist = py_env_dir / "py_dist"

    requested_v = settings.get("python_version", "3.13")
    print(f"[Info] Identifying latest compatible Python for '{requested_v}'...")
    full_v = find_latest_full_version(requested_v)

    if not full_v:
        print("[Error] Could not find compatible Python version. Check internet connection.")
        input("Press enter to exit.")
        sys.exit(1)

    print(f"[Info] Found Python {full_v}. Preparing installation...")

    excludes = ["path", "appendpath", "pip", "launcher", "freethreaded"]
    if settings.get("install_tkinter", "false").lower() != "true":
        excludes.append("tcltk")
    if settings.get("install_tests", "false").lower() != "true":
        excludes.append("test")
    if settings.get("install_tools", "false").lower() != "true":
        excludes.append("tools")
    if settings.get("install_docs", "false").lower() != "true":
        excludes.append("doc")
    exclude_pattern = "^(" + "|".join(excludes) + r")$"

    if python_dist.exists():
        if (python_dist / "python.exe").exists() or not any(python_dist.iterdir()):
            shutil.rmtree(python_dist)
        else:
            print(f"[Error] {python_dist} exists but isn't a Python folder. Aborting.")
            input("Press enter to exit.")
            sys.exit(2)

    python_dist.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = pathlib.Path(tmp_dir)
        msi_list = download_msi_files(full_v, tmp_path, exclude_pattern)
        if not msi_list:
            print("[Error] No MSI files downloaded.")
            input("Press enter to exit.")
            sys.exit(3)

        print(f"\n==== Installing Python {full_v} locally ====\n")
        extract_msi_files(msi_list, python_dist)

    with open(python_dist / ".gitignore", "w", encoding="utf-8") as f:
        f.write("# Auto added to prevent sync\n*\n")

    ruff_cfg = python_dist / "Lib/test/.ruff.toml"
    if ruff_cfg.exists():
        content = ruff_cfg.read_text(encoding="utf-8")
        content = re.sub(r"(?m)^(\s*extend\s*=)", r"# \1", content)
        ruff_cfg.write_text(content, encoding="utf-8")

    with open(python_dist / "pip.ini", "w", encoding="utf-8") as f:
        f.write("[global]\nno-warn-script-location = false\n")

    print("[Info] Setting up pip...")
    py_exe = str(python_dist / "python.exe")
    subprocess.run([py_exe, "-m", "ensurepip", "--upgrade"], capture_output=True)  # noqa:S603
    subprocess.run([py_exe, "-m", "pip", "install", "--upgrade", "pip"], capture_output=True)  # noqa:S603
    subprocess.run([py_exe, "-m", "pip", "install", "--upgrade", "pip"], capture_output=True)  # noqa:S603

    print(f"\n[Success] Portable Python {full_v} created at {python_dist}")


def generate_portable_wrappers(venv_dir, venv_to_python_rel):
    portable_scripts = venv_dir / "portable_Scripts"
    portable_scripts.mkdir(parents=True, exist_ok=True)

    # python.bat
    py_bat_content = f"""@echo off
setlocal
set "venv_path=%~dp0.."
set "python_exe_folder=%venv_path%\\{venv_to_python_rel}"
call :make_absolute_path_if_relative "%python_exe_folder%"
set "python_exe_folder=%OUTPUT%"

:: Repair pyvenv.cfg if moved
for /f "tokens=1,* delims==" %%A in ('findstr /I /C:"home =" "%venv_path%\\pyvenv.cfg" 2^>nul') do (
  for /f "tokens=* delims= " %%Z in ("%%B") do set "CURRENT_HOME=%%~Z"
)
if /I not "%CURRENT_HOME%"=="%python_exe_folder%" (
    powershell -NoProfile -Command "$cfg='%venv_path%\\pyvenv.cfg'; $newHome=(Resolve-Path '%python_exe_folder%').Path; $txt=Get-Content -Raw $cfg; if($txt -match '(?m)^home\\s*='){{ $txt=[regex]::Replace($txt,'(?m)^(home\\s*=\\s*).+$','${{1}}'+$newHome) }} else {{ $nl=if($txt -and $txt[-1]-ne [char]10){{[environment]::NewLine}}else{{''}}; $txt+=$nl+'home = '+$newHome+[environment]::NewLine }}; $utf8NoBom=New-Object System.Text.UTF8Encoding $false; [System.IO.File]::WriteAllText($cfg,$txt,$utf8NoBom)"
)

if "%~1"=="" (
  "%venv_path%\\Scripts\\python.exe"
) else (
  "%venv_path%\\Scripts\\python.exe" %*
)
endlocal & exit /b %ERRORLEVEL%

:make_absolute_path_if_relative
if "%~1"=="" ( set "OUTPUT=%CD%" ) else ( set "OUTPUT=%~f1" )
goto :EOF
"""
    with open(portable_scripts / "python.bat", "w", encoding="utf-8") as f:
        f.write(py_bat_content)

    # pip.bat
    with open(portable_scripts / "pip.bat", "w", encoding="utf-8") as f:
        f.write('@echo off\n"%~dp0python.bat" -m pip %*\n')

    # activate.bat (Modified version of standard venv activate)
    orig_activate = venv_dir / "Scripts/activate.bat"
    if orig_activate.exists():
        content = orig_activate.read_text(encoding="utf-8")
        content = re.sub(r'(?m)^set\s+"VIRTUAL_ENV=.*"', r'set "VIRTUAL_ENV=%~dp0..\\"', content)
        content = content.replace(
            'set "PATH=%VIRTUAL_ENV%\\Scripts;%PATH%"',
            'set "PATH=%VIRTUAL_ENV%\\portable_Scripts;%VIRTUAL_ENV%\\Scripts;%PATH%"',
        )
        with open(orig_activate, "w", encoding="utf-8") as f:
            f.write(content)


def create_portable_venv():
    script_dir = pathlib.Path(__file__).parent.resolve()
    settings_path = (script_dir / "../../non-user_settings.ini").resolve()
    get_settings(settings_path)

    py_env_dir = (settings_path.parent / "py_env").resolve()
    python_dist = py_env_dir / "py_dist"
    python_exe = python_dist / "python.exe"

    if not python_exe.exists():
        print("[Info] Base Python missing. Triggering installer...")
        run_python(sys.executable, str(script_dir / "env_install_python.py"), [])
        if not python_exe.exists():
            print("[Error] Base Python still missing after installation attempt.")
            input("Press Enter to exit.")
            sys.exit(1)

    venv_dir = py_env_dir / "virt_env"

    if venv_dir.exists():
        if (venv_dir / "Scripts/activate.bat").exists():
            shutil.rmtree(venv_dir)
        else:
            print(f"[Error] {venv_dir} exists but isn't a venv. Aborting.")
            input("Press Enter to exit.")
            sys.exit(2)

    print("\n==== Creating Virtual Environment ====\n")
    subprocess.run([str(python_exe), "-m", "venv", str(venv_dir)], check=True)  # noqa:S603

    try:
        venv_python = venv_dir / "Scripts/python.exe"
        subprocess.run([str(venv_python), "-m", "pip", "install", "--upgrade", "pip"])  # noqa:S603

        rel_path = os.path.relpath(python_dist, venv_dir)
        print("[Info] Generating portable wrappers...")
        generate_portable_wrappers(venv_dir, rel_path)

        packages_list = py_env_dir / "default_python_packages.txt"
        if packages_list.exists():
            print("\n[Info] Installing default packages...")

            subprocess.run(  # noqa:S603
                [str(venv_python), "-m", "pip", "install", "-r", str(packages_list), "--upgrade", "--no-cache-dir"]
            )

        print("[Success] Virtual environment prepared.")
    except Exception as e:
        print(f"[Error] Post-creation setup failed: {e}")
        input("Press Enter to exit.")
        sys.exit(3)
