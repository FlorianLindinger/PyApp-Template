import argparse
import os
import pathlib
import subprocess
import sys

import launcher_utilities as utils


def main():
    # 1. Paths & Initialization
    script_dir = pathlib.Path(__file__).parent.resolve()
    settings_path = (script_dir / "../../non-user_settings.ini").resolve()
    settings = utils.get_settings(settings_path)
    settings_dir = settings_path.parent

    # 2. Argument Parsing
    parser = argparse.ArgumentParser(description=f"Launcher for {settings.get('program_name', 'App')}")
    parser.add_argument("--background", action="store_true", help="Launch in background mode")
    parser.add_argument("--shortcuts", action="store_true", help="Generate Windows shortcuts")
    parser.add_argument("--prepare-env", action="store_true", help="Only prepare the Python environment")
    args, passthrough = parser.parse_known_args()

    # 3. Action Routing
    if args.shortcuts:
        utils.run_python(sys.executable, str(script_dir / "generate_shortcuts.py"), [])
        return

    if args.background:
        utils.launch_background(settings, settings_path, pathlib.Path(__file__).resolve())
        return

    # 4. Default behavior: Prepare Env & Launch
    utils.apply_terminal_settings(settings)
    utils.prepare_environment(settings, settings_path, script_dir)

    if args.prepare_env:
        print("[Info] Environment preparation complete.")
        return

    # 5. Execute Main Code
    python_code = (settings_dir / settings.get("python_code_name", "main_code.py")).resolve()
    crash_code = settings.get("after_python_crash_code_name")
    crash_code_path = (settings_dir / crash_code).resolve() if crash_code else None

    # Python Interpreter Selection
    if settings.get("use_global_python", "false").lower() == "true":
        python_exe = f"py -{settings.get('python_version', '3')}"
    else:
        venv_py = settings_dir / "py_env/virt_env/Scripts/python.exe"
        python_exe = str(venv_py) if venv_py.exists() else "python"

    # Background Icon Changer
    icon_path = (settings_dir / settings.get("icon_path", "")).resolve()
    icon_changer = (
        script_dir / "../general_utilities/window_icon_changer/change_icon.py_standalone_compiled/run.exe"
    ).resolve()
    if icon_changer.exists() and icon_path.exists():
        subprocess.Popen(
            [str(icon_changer), settings.get("program_name", "App"), str(icon_path)],
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )

    # Execution Loop
    restart_on_crash = settings.get("restart_main_code_on_crash", "false").lower() == "true"
    exit_code = utils.run_python(python_exe, str(python_code), passthrough)

    while exit_code != 0:
        if restart_on_crash:
            print(f"\n[Info] {python_code.name} crashed. Restarting...")
            exit_code = utils.run_python(python_exe, str(python_code), ["crashed"])
        elif crash_code_path and crash_code_path.exists():
            print(f"\n[Info] {python_code.name} crashed. Running crash handler...")
            utils.run_python(python_exe, str(crash_code_path), [])
            break
        else:
            print(f"\n[Info] Process finished with exit code {exit_code}.")
            break


if __name__ == "__main__":
    main()
