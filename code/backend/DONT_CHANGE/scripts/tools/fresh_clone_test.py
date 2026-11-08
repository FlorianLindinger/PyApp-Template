"""Check that a fresh clone of the last commit works: finds files that are missing from Git.

Clones the current commit into a temporary folder, runs Setup there, starts the launcher without a
terminal and runs a dev tool. main.py in the clone is replaced by a probe that only writes a marker
file, so this tests the launcher and not the app. The project itself is never touched, and the
clone's settings keep Setup away from your Start Menu and Desktop.

Only committed files are tested. The tool lists what is not committed, because a new file that was
never added to Git is exactly what breaks a fresh clone.

Usage: fresh_clone_test.bat [--timeout 900] [--keep]
"""

from __future__ import annotations

import argparse
import ast
import os
import shutil
import stat
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

import _ui
from _paths import PROJECT_ROOT

WORK_DIR = Path(tempfile.gettempdir()) / "pyapp_fresh_clone"
SETUP_FILE = "Setup - run first and after moving folder.cmd"
START_TIMEOUT_SECONDS = 180
SHOWN_LOG_LINES = 40
SHOWN_NEW_FILES = 15
PROBE = """with open({marker!r}, "w") as marker:
    marker.write("started")
"""
# Added to the end of the clone's settings; Python uses the last assignment.
TEST_SETTINGS = """

# Added by fresh_clone_test: no shortcuts outside the clone, and no window that waits for someone.
start_menu_shortcuts = False
desktop_shortcuts = []
close_after_success = True
close_after_failure = True
open_log_file_after_failure = False
open_crash_log_after_failure = False
play_sound_after_failure = False
"""


def clean_environment() -> Dict[str, str]:
    """This tool's bootstrap variables must not leak into the clone's launcher."""
    env = {key: value for key, value in os.environ.items() if not key.upper().startswith("PYAPP_")}
    env["PYAPP_ENTRYPOINT_NO_PAUSE"] = "1"
    return env


def batch_command(batch_file: Path, *arguments: str) -> str:
    """A cmd.exe command line that keeps a path with spaces intact."""
    joined = "".join(f' "{argument}"' for argument in arguments)
    return f'cmd.exe /d /s /c ""{batch_file}"{joined}"'


def git(*arguments: str) -> str:
    # Fixed Git commands in the project folder.
    completed = subprocess.run(  # noqa: S603
        ["git", "-C", str(PROJECT_ROOT), *arguments],  # noqa: S607
        capture_output=True,
        check=False,
    )
    if completed.returncode:
        raise RuntimeError(completed.stderr.decode("utf-8", "replace").strip() or "git failed")
    return completed.stdout.decode("utf-8", "replace")


def split_status(status: str) -> Tuple[List[str], List[str]]:
    """(changed files, new files) of a `git status --porcelain` output."""
    lines = [line for line in status.splitlines() if line.strip()]
    return [line[3:] for line in lines if not line.startswith("??")], [
        line[3:] for line in lines if line.startswith("??")
    ]


def report_uncommitted() -> None:
    changed, new = split_status(git("-c", "core.quotepath=off", "status", "--porcelain"))
    if changed or new:
        _ui.warn(f"Not part of this test: {len(changed)} changed and {len(new)} new file(s) that are not committed.")
    for name in new[:SHOWN_NEW_FILES]:
        _ui.info("  new: " + name)
    if len(new) > SHOWN_NEW_FILES:
        _ui.info(f"  ... and {len(new) - SHOWN_NEW_FILES} more.")


def main_script_value(settings_text: str) -> str:
    """The main_script_path of a developer_settings.py; the last assignment counts."""
    value: Optional[str] = None
    for node in ast.parse(settings_text).body:
        if isinstance(node, (ast.Assign, ast.AnnAssign)) and node.value is not None:
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            if any(isinstance(target, ast.Name) and target.id == "main_script_path" for target in targets):
                value = ast.literal_eval(node.value)
    if not value:
        raise RuntimeError("developer_settings.py does not set main_script_path.")
    return value


def prepare_clone(clone: Path, marker: Path) -> None:
    settings = clone / "code" / "backend" / "developer_settings.py"
    text = settings.read_text(encoding="utf-8")
    script = (settings.parent / main_script_value(text)).resolve()
    script.write_text(PROBE.format(marker=str(marker)), encoding="utf-8")
    settings.write_text(text + TEST_SETTINGS, encoding="utf-8")


def run_quietly(command: str, env: Dict[str, str], cwd: Path, log: Path, timeout: float) -> bool:
    """Run a command with its output in the log file; True if it succeeded in time."""
    with log.open("ab") as stream:
        try:
            # Fixed launcher files of the temporary clone.
            return (
                subprocess.run(  # noqa: S603
                    command,
                    cwd=str(cwd),
                    env=env,
                    stdin=subprocess.DEVNULL,
                    stdout=stream,
                    stderr=subprocess.STDOUT,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                    timeout=timeout,
                    check=False,
                ).returncode
                == 0
            )
        except subprocess.TimeoutExpired:
            return False


def wait_until(condition: Callable[[], bool], seconds: float) -> bool:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if condition():
            return True
        time.sleep(0.1)
    return condition()


def start_without_terminal(clone: Path, marker: Path, env: Dict[str, str], log: Path) -> bool:
    """Start the launcher like the "(no Terminal)" shortcut; True once the probe has run."""
    launcher = clone / "code" / "backend" / "DONT_CHANGE" / "B" / "N.bat"
    with log.open("ab") as stream:
        # Fixed launcher file of the temporary clone.
        process = subprocess.Popen(  # noqa: S603
            batch_command(launcher, "fresh-clone-test"),
            cwd=str(clone),
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=stream,
            stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        try:
            return wait_until(marker.exists, START_TIMEOUT_SECONDS)
        finally:
            try:
                process.wait(30)
            except subprocess.TimeoutExpired:
                process.kill()


def no_instance_left(clone: Path) -> bool:
    return not any((clone / "code" / "backend" / "DONT_CHANGE" / "tmp" / "running").glob("*.json"))


def remove_clone(clone: Path) -> None:
    """Git marks its object files read-only, which would stop the deletion on Windows."""
    for folder, _, names in os.walk(str(clone)):
        for name in names:
            try:
                (Path(folder) / name).chmod(stat.S_IWRITE | stat.S_IREAD)
            except OSError:
                pass
    shutil.rmtree(clone, ignore_errors=True)


def run_checks(clone: Path, marker: Path, log: Path, timeout: float) -> List[Tuple[str, bool]]:
    """The checks in order; stops at the first failure, because the later ones build on it."""
    env = clean_environment()
    results: List[Tuple[str, bool]] = []

    def check(name: str, passed: bool) -> bool:
        results.append((name, passed))
        return passed

    _ui.step("Running Setup in the clone (installs the environment, this can take a few minutes) ...")
    if not check("Setup", run_quietly(batch_command(clone / SETUP_FILE), env, clone, log, timeout)):
        return results
    venv_python = clone / "code" / "backend" / "generated" / ".venv" / "Scripts" / "python.exe"
    if not check("Environment created", venv_python.is_file()):
        return results
    if not check("Shortcuts created", any(clone.glob("*.lnk"))):
        return results
    _ui.step("Starting the launcher without a terminal ...")
    if not check("App started", start_without_terminal(clone, marker, env, log)):
        return results
    if not check("App ended cleanly", wait_until(lambda: no_instance_left(clone), 30)):
        return results
    _ui.step("Running a dev tool ...")
    status_tool = clone / "code" / "backend" / "dev_tools" / "status.cmd"
    check("Dev tool (status)", run_quietly(batch_command(status_tool), env, clone, log, 120))
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--timeout", type=float, default=900.0, help="seconds Setup may take (default 900)")
    parser.add_argument("--keep", action="store_true", help="keep the temporary clone")
    arguments = parser.parse_args()

    WORK_DIR.mkdir(parents=True, exist_ok=True)
    clone = WORK_DIR / f"clone_{os.getpid()}"
    marker = WORK_DIR / f"marker_{os.getpid()}.txt"
    log = WORK_DIR / f"log_{os.getpid()}.txt"
    _ui.heading("Fresh clone test")
    _ui.fields(
        [
            ("Repository", PROJECT_ROOT),
            ("Commit", git("log", "-1", "--format=%h %s").strip()),
            ("Temporary clone", clone),
        ]
    )
    report_uncommitted()

    passed = False
    try:
        _ui.step("Cloning the current commit ...")
        git("clone", "--quiet", "--no-local", "--depth", "1", str(PROJECT_ROOT), str(clone))
        prepare_clone(clone, marker)
        results = run_checks(clone, marker, log, arguments.timeout)
        _ui.heading("Result")
        _ui.fields((name, "passed" if ok else "FAILED") for name, ok in results)
        passed = all(ok for _, ok in results)
        if not passed and log.is_file():
            _ui.heading("Last output of the launcher")
            for line in log.read_text(encoding="utf-8", errors="replace").splitlines()[-SHOWN_LOG_LINES:]:
                _ui.info(line)
    finally:
        if marker.exists():
            marker.unlink()
        if log.exists():
            log.unlink()
        if not arguments.keep:
            remove_clone(clone)

    _ui.blank_line()
    if passed:
        _ui.success("A fresh clone of this commit works.")
        return 0
    _ui.error("A fresh clone of this commit does not work. See the output above.")
    return 1


if __name__ == "__main__":
    raise SystemExit(_ui.run(main))
