import configparser
import ctypes
import os
import pathlib
import re
import shutil
import signal
import subprocess
import sys
import traceback
import unicodedata

# ============================
# ==== Core Utility Funcs ====
# ============================

def get_file_dir(__file__):
    """get directory of file that calls this with \\ at end."""
    return os.path.dirname(os.path.abspath(__file__)) + "\\"

def make_abs_relative_to_file(path,file):
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
    except Exception as m:
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
        with open(settings_path, "r", encoding="utf-8") as f:
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
            os.system(f"color {bg}{txt}")
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
        return subprocess.run(cmd).returncode
    except Exception as e:
        print(f"[Error] Python execution failed: {e}")
        return 1


def run_command(cmd: list, shell: bool = False, capture_output: bool = False) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(cmd, shell=shell, capture_output=capture_output, text=True)
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
        with open(pid_path, "r", encoding="utf-8") as f:
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
            proc = subprocess.Popen(
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


def prepare_environment(_settings: dict, _settings_path: pathlib.Path, script_dir: pathlib.Path):
    env_setup_script = (script_dir / "env_setup.py").resolve()
    if env_setup_script.exists():
        print("[Info] Running environment setup...")
        # Use sys.executable (base python) to run the setup script
        run_python(sys.executable, str(env_setup_script), [])
    else:
        print("[Error] Environment setup script missing.")
