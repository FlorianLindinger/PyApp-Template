import os
import pathlib
import re
import shutil
import subprocess
import sys

import launcher_utilities as utils


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


def main():
    script_dir = pathlib.Path(__file__).parent.resolve()
    settings_path = (script_dir / "../../non-user_settings.ini").resolve()
    utils.get_settings(settings_path)

    py_env_dir = (settings_path.parent / "py_env").resolve()
    python_dist = py_env_dir / "py_dist"
    python_exe = python_dist / "python.exe"

    if not python_exe.exists():
        print("[Info] Base Python missing. Triggering installer...")
        utils.run_python(sys.executable, str(script_dir / "env_install_python.py"), [])
        if not python_exe.exists():
            print("[Error] Base Python still missing after installation attempt.")
            sys.exit(1)

    venv_dir = py_env_dir / "virt_env"

    if venv_dir.exists():
        if (venv_dir / "Scripts/activate.bat").exists():
            shutil.rmtree(venv_dir)
        else:
            print(f"[Error] {venv_dir} exists but isn't a venv. Aborting.")
            sys.exit(2)

    print("\n==== Creating Virtual Environment ====\n")
    subprocess.run([str(python_exe), "-m", "venv", str(venv_dir)], check=True)

    try:
        rel_path = os.path.relpath(python_dist, venv_dir)
        print("[Info] Generating portable wrappers...")
        generate_portable_wrappers(venv_dir, rel_path)

        packages_list = py_env_dir / "default_python_packages.txt"
        if packages_list.exists():
            print("\n[Info] Installing default packages...")
            venv_python = venv_dir / "Scripts/python.exe"
            subprocess.run(
                [str(venv_python), "-m", "pip", "install", "-r", str(packages_list), "--upgrade", "--no-cache-dir"]
            )

        print("[Success] Virtual environment prepared.")
    except Exception as e:
        print(f"[Error] Post-creation setup failed: {e}")
        sys.exit(3)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n[FATAL ERROR] Venv installation failed: {e}")
        input("\nPress Enter to exit...")
        sys.exit(1)
