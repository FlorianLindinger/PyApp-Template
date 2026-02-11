import os
import pathlib
import sys

import launcher_utilities as utils


def main():
    script_dir = pathlib.Path(__file__).parent.resolve()
    settings_path = (script_dir / "../../non-user_settings.ini").resolve()
    settings = utils.get_settings(settings_path)

    py_env_dir = (settings_path.parent / "py_env").resolve()
    python_dist = py_env_dir / "py_dist"
    python_exe = python_dist / ("python.exe" if os.name == "nt" else "bin/python3")
    venv_dir = py_env_dir / "virt_env"

    target_v = settings.get("python_version", "3.13")

    # 1. Check Python Distribution
    if not python_exe.exists():
        utils.run_python(sys.executable, str(script_dir / "env_install_python.py"), [])
        if not python_exe.exists():
            sys.exit(1)

    # 2. Check Version & Venv
    try:
        curr_v = utils.run_command(
            [str(python_exe), "-c", "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"],
            capture_output=True,
        ).stdout.strip()

        if curr_v != target_v:
            print(f"\n[Warning] Version mismatch ({curr_v} vs {target_v}).")
            if utils.prompt_user("Reinstall Python?"):
                utils.run_python(sys.executable, str(script_dir / "env_install_python.py"), [])
                utils.run_python(sys.executable, str(script_dir / "env_install_venv.py"), [])
        elif not venv_dir.exists():
            utils.run_python(sys.executable, str(script_dir / "env_install_venv.py"), [])

    except Exception as e:
        print(f"[Error] Environment check failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
