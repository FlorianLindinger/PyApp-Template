"""Windows bridge to isolated native Linux builds in WSL Ubuntu."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import List

from pyapp.DONT_CHANGE import pyapp_settings as paths
from pyapp.DONT_CHANGE.scripts.config import (
    main_script_path,
    package_entries,
    requirements_file_path,
    settings,
    validate,
)
from pyapp.DONT_CHANGE.scripts.console_tools import print_heading, print_info
from pyapp.DONT_CHANGE.scripts.dev_tools import compilation
from pyapp.DONT_CHANGE.scripts.errors import SetupError


def wsl(distribution: str, arguments: List[str], capture: bool = False) -> str:
    """Pass arguments directly to WSL; never interpolate project paths into shell code."""
    try:
        executable = shutil.which("wsl.exe")
        if executable is None:
            raise SetupError("WSL is required. Install it with: wsl --install -d Ubuntu")
        result = subprocess.run(  # noqa: S603 - explicit WSL executable/argv, no Windows shell
            [executable, "--distribution", distribution, "--exec", *arguments],
            capture_output=capture,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
    except OSError as error:
        raise SetupError("WSL is required. Install it with: wsl --install -d Ubuntu") from error
    if result.returncode:
        raise SetupError(
            "Linux command failed. Run setup-linux first; WSL installation may require a restart.\n"
            + (result.stderr.strip() if capture else "See Linux output above.")
        )
    return result.stdout.strip() if capture else ""


def linux_path(distribution: str, path: Path) -> str:
    return wsl(distribution, ["wslpath", "-a", "-u", str(path.resolve())], capture=True)


def cmd_setup_linux(arguments: List[str]) -> None:
    """Install what a Linux build needs in WSL Ubuntu, once (may ask for your Linux password)."""
    parser = argparse.ArgumentParser(description=cmd_setup_linux.__doc__)
    parser.add_argument("--distribution", default="Ubuntu")
    parser.add_argument(
        "--install-wsl", action="store_true", help="install WSL/distro; run from an administrator terminal"
    )
    options = parser.parse_args(arguments)
    print_heading("Set up Linux compilation")
    if options.install_wsl:
        executable = shutil.which("wsl.exe")
        if executable is None:
            raise SetupError("WSL is unavailable. Enable Windows Subsystem for Linux in Windows Features first.")
        result = subprocess.run(  # noqa: S603 - explicit user-requested WSL installation
            [executable, "--install", "--distribution", options.distribution], check=False
        )
        if result.returncode:
            raise SetupError("WSL installation failed. Use an administrator terminal and see the Windows output above.")
        print_info("Restart Windows if requested, finish Ubuntu's first-run user setup, then run setup-linux again.")
        return
    print_info("Installing Ubuntu packages: build-essential, patchelf, python3, curl, ca-certificates, git.")
    wsl(options.distribution, ["sudo", "apt-get", "update"])
    wsl(
        options.distribution,
        [
            "sudo",
            "apt-get",
            "install",
            "-y",
            "build-essential",
            "patchelf",
            "python3",
            "curl",
            "ca-certificates",
            "git",
        ],
    )
    print_info("Linux prerequisites ready. compile-linux installs the requested Linux Python and app packages.")


def _wsl_succeeds(distribution: str, arguments: List[str]) -> bool:
    """True when the Linux command runs and exits with 0; nothing is printed."""
    executable = shutil.which("wsl.exe")
    if executable is None:
        return False
    try:
        # Explicit WSL executable and argument list, no Windows shell.
        result = subprocess.run(  # noqa: S603
            [executable, "--distribution", distribution, "--exec", *arguments],
            capture_output=True,
            check=False,
            timeout=120,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0


def _ask_yes(question: str) -> bool:
    from pyapp.DONT_CHANGE.scripts.console_tools import ask

    try:
        return ask(question + " [y/N]").strip().lower() in ("y", "yes")
    except (EOFError, KeyboardInterrupt):
        return False


def cmd_test_linux(arguments: List[str]) -> None:
    """Start the app on Linux in WSL (Windows' built-in Linux) to see it run; offers to set WSL up."""
    parser = argparse.ArgumentParser(description=cmd_test_linux.__doc__)
    parser.add_argument("--distribution", default="Ubuntu")
    options = parser.parse_args(arguments)
    distribution = options.distribution
    print_heading("Test the app on Linux (WSL)")
    # 1. WSL and the Linux distribution.
    if not _wsl_succeeds(distribution, ["true"]):
        print_info(
            f"WSL with {distribution} is not ready on this PC. Installing it needs administrator rights,\n"
            "may need a restart, and then asks you once for a Linux user name and password."
        )
        if not _ask_yes(f"Install WSL with {distribution} now?"):
            print_info(f'Nothing was changed. Later: run "wsl --install -d {distribution}" as administrator.')
            return
        executable = shutil.which("wsl.exe")
        if executable is None:
            raise SetupError("WSL is unavailable. Turn on 'Windows Subsystem for Linux' in Windows Features first.")
        # The user asked for this installation; Windows asks for administrator rights itself.
        subprocess.run([executable, "--install", "--distribution", distribution], check=False)  # noqa: S603
        print_info("When the installation has finished (and Windows has restarted, if it asked), run test-linux again.")
        return
    # 2. Python with tkinter inside Linux (the example app is a Tkinter window).
    if not _wsl_succeeds(distribution, ["python3", "-c", "import tkinter"]):
        print_info("Linux needs Python 3 with tkinter: sudo apt-get install python3 python3-tk")
        if not _ask_yes("Install them now (asks for your Linux password)?"):
            print_info("Nothing was changed.")
            return
        wsl(distribution, ["sudo", "apt-get", "update"])
        wsl(distribution, ["sudo", "apt-get", "install", "-y", "python3", "python3-tk"])
    s = settings()
    validate(s)
    if package_entries(s) or requirements_file_path(s):
        print_info(
            "Note: the app's packages are not installed in Linux. The fallback start uses Linux's own Python;\n"
            "install them there yourself (e.g. with pip or apt) if the app needs them."
        )
    # 3. The Linux start script, run inside WSL. On Windows 11, Linux windows show up like Windows ones.
    script = Path(paths.BACKEND_DIR) / "fallback_start" / "Start without launcher --LINUX.sh"
    print_info("Starting the app in Linux. Close its window (or press Ctrl+C here) to come back.")
    wsl(distribution, ["sh", linux_path(distribution, script)])
    print_info("The app ended in Linux.")


def cmd_compile_linux(arguments: List[str]) -> None:
    """Build a Linux version of the app in WSL; the result is an archive to copy to Linux."""
    parser = argparse.ArgumentParser(description=cmd_compile_linux.__doc__)
    parser.add_argument("--distribution", default="Ubuntu")
    parser.add_argument("--preset")
    parser.add_argument("--mode", choices=("standalone", "onefile"))
    parser.add_argument("--dry-run", action="store_true")
    options = parser.parse_args(arguments)
    build = compilation.load_options(options.preset, options.mode, None, compilation.LINUX_CONFIG)
    if build.variant != "terminal":
        raise SetupError("Linux builds use terminal mode. Launch GUI apps from your Linux desktop as appropriate.")
    if any(arg.startswith(("--windows-", "--msvc", "--mingw")) for arg in build.extra_args):
        raise SetupError("Remove Windows-only options from linux_settings.json / the selected preset.")
    app = settings()
    validate(app)
    print_heading("Compile Linux app")
    print_info(f"WSL: {options.distribution}; Python: {app.python_version}; preset: {build.preset}; mode: {build.mode}")
    print_info("Linux settings: " + str(compilation.LINUX_CONFIG))
    if options.dry_run:
        print_info("Nuitka options: " + subprocess.list2cmdline(build.extra_args))
        return
    root = compilation.OUTPUT
    target = compilation.output_folder(build, platform="linux")
    compilation.reserve_output(target)
    distribution = options.distribution
    extra = []
    for argument in build.extra_args:
        mapped_argument = argument
        if argument.startswith(("--include-data-files=", "--include-data-dir=")):
            flag, source, destination = argument.split("=", 2)
            data = Path(source)
            if not data.is_absolute():
                data = Path(paths.PYTHON_SCRIPTS_DIR) / data
            mapped_argument = flag + "=" + linux_path(distribution, data) + "=" + destination
        extra.append(mapped_argument)
    requirements = requirements_file_path(app)
    job = {
        "python": app.python_version,
        "script": linux_path(distribution, Path(main_script_path(app))),
        "code": linux_path(distribution, Path(paths.PYTHON_SCRIPTS_DIR)),
        "output": linux_path(distribution, target),
        "mode": build.mode,
        "packages": package_entries(app),
        "requirements": linux_path(distribution, Path(requirements)) if requirements else "",
        "extra": extra,
    }
    worker = Path(__file__).with_name("linux_worker.py")
    # WSL cannot access Windows TEMP reliably on all installations; use marked project output.
    with tempfile.TemporaryDirectory(prefix=".linux-job-", dir=root) as temporary:
        job_path = Path(temporary) / "job.json"
        job_path.write_text(json.dumps(job), encoding="utf-8")
        wsl(distribution, ["python3", linux_path(distribution, worker), linux_path(distribution, job_path)])
    print_info(f"Linux archive and compilation report: {target}")
