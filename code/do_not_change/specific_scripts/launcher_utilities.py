import configparser
import ctypes
import os
import pathlib
import signal
import subprocess
import sys

# ============================
# ==== Core Utility Funcs ====
# ============================


def get_settings(settings_path: pathlib.Path) -> dict:
    if not settings_path.exists():
        print(f"[Error] Settings file not found: {settings_path}")
        return {}
    config = configparser.ConfigParser(interpolation=None)
    try:
        with open(settings_path, "r", encoding="utf-8") as f:
            config.read_string("[DEFAULT]\n" + f.read())
        return dict(config["DEFAULT"])
    except Exception as e:
        print(f"[Error] Failed to parse settings: {e}")
        return {}


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


def open_settings(settings_path: pathlib.Path, settings: dict):
    user_settings_rel = settings.get("user_settings_path")
    if not user_settings_rel:
        print(f"[Error] 'user_settings_path' not defined.")
        return
    user_settings_abs = (settings_path.parent / user_settings_rel).resolve()
    if not user_settings_abs.exists():
        print(f"[Error] Settings file not found: {user_settings_abs}")
        return
    print(f"[Info] Opening {user_settings_abs.name}...")
    if os.name == "nt":
        os.startfile(user_settings_abs)
    else:
        opener = "open" if sys.platform == "darwin" else "xdg-open"
        run_command([opener, str(user_settings_abs)])


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
