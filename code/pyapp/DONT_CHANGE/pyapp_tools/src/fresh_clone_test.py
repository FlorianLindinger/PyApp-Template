"""Check that a fresh clone of the last commit works: finds files that are missing from Git.

Clones the current commit into a temporary folder whose path has spaces, runs Setup there, starts
the launcher without a terminal and runs a dev tool. Then the smoke tests: the log without a
terminal (prints and native output), a Python error (crash log), a hard interpreter crash (crash
log and the last output kept), a start without internet, a start after moving the folder, and Setup
updating the shortcuts for the new place. main.py in the clone is replaced by a probe that writes a
marker file and does what the current scenario needs, so this tests the launcher and not the app.
The project itself is never touched, and the clone's settings keep Setup away from your Start Menu
and Desktop. A missing package is not tested here: its recovery menu waits for an answer.

Only committed files are tested. The tool lists what is not committed, because a new file that was
never added to Git is exactly what breaks a fresh clone.

Usage: fresh_clone_test.bat [--timeout 900] [--keep]   (takes a few minutes: two Setups, six starts)
"""

from __future__ import annotations

import argparse
import ast
import contextlib
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
# The probe's scenario comes from a file next to the marker: ok, error or hard_crash.
PROBE = """import os

mode = "ok"
if os.path.exists({mode!r}):
    with open({mode!r}) as stream:
        mode = stream.read().strip()
print("probe print")
os.write(1, b"probe native\\n")
with open({marker!r}, "w") as marker:
    marker.write(mode)
if mode == "error":
    raise RuntimeError("probe error")
if mode == "hard_crash":
    os.write(1, b"probe last words\\n")
    os._exit(3)
"""
# A port nothing listens on: every download fails at once, as without internet.
NO_INTERNET = {"UV_OFFLINE": "1", "HTTP_PROXY": "http://127.0.0.1:9", "HTTPS_PROXY": "http://127.0.0.1:9"}
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


def clone_main_script(clone: Path, value: str, project: Path = PROJECT_ROOT) -> Path:
    """The clone's copy of main_script_path; never a file outside the clone's code folder.

    An absolute setting names a file of the original project (the launcher accepts any path inside
    its code folder), so it is mapped to the same place in the clone. Writing the probe to it
    directly would overwrite the real app.
    """
    clone_code = (clone / "code").resolve()
    # Keep os.path.isabs: it matches the launcher's own check in config._resolve_main_script.
    if os.path.isabs(value):  # noqa: PTH117
        try:
            relative = Path(value).resolve().relative_to((project / "code").resolve())
        except ValueError:
            raise RuntimeError(f'main_script_path "{value}" is not inside the project\'s code folder.') from None
        script = clone_code / relative
    else:
        script = clone / "code" / "pyapp" / value
    # resolve() also follows links, so a link that leads out of the clone is caught here.
    script = script.resolve()
    try:
        script.relative_to(clone_code)
    except ValueError:
        raise RuntimeError(f'main_script_path "{value}" leads outside the clone; the test would change it.') from None
    return script


def prepare_clone(clone: Path, marker: Path, project: Path = PROJECT_ROOT) -> None:
    settings = clone / "code" / "pyapp" / "developer_settings.py"
    text = settings.read_text(encoding="utf-8")
    script = clone_main_script(clone, main_script_value(text), project)
    script.write_text(PROBE.format(marker=str(marker), mode=str(mode_file(marker))), encoding="utf-8")
    # The clone must run its probe, also when the setting is an absolute path into the original project.
    relative = os.path.relpath(str(script), str(settings.parent.resolve()))
    settings.write_text(text + TEST_SETTINGS + f"main_script_path = {relative!r}\n", encoding="utf-8")


def mode_file(marker: Path) -> Path:
    """Where the probe reads its scenario."""
    return marker.with_suffix(".mode")


def files_in(folder: Path, pattern: str) -> List[Path]:
    """Matching files, oldest first."""
    return sorted(folder.glob(pattern), key=lambda path: path.stat().st_mtime) if folder.is_dir() else []


def newest_text(folder: Path, pattern: str) -> str:
    found = files_in(folder, pattern)
    return found[-1].read_text(encoding="utf-8", errors="replace") if found else ""


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
    launcher = clone / "code" / "pyapp" / "DONT_CHANGE" / "B" / "N.bat"
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


def move_when_free(source: Path, target: Path, seconds: float = 30) -> bool:
    """Rename a folder; True once it worked.

    The launcher's completion step still runs for a moment after the app unregistered, and Windows
    cannot rename a folder while a process uses a file in it (or has it as its working folder).
    """

    def attempt() -> bool:
        try:
            source.rename(target)
        except OSError:
            return False
        return True

    return wait_until(attempt, seconds)


def no_instance_left(clone: Path) -> bool:
    return not any((clone / "code" / "pyapp" / "DONT_CHANGE" / "tmp" / "running").glob("*.json"))


def remove_clone(clone: Path) -> None:
    """Git marks its object files read-only, which would stop the deletion on Windows."""
    for folder, _, names in os.walk(str(clone)):
        for name in names:
            with contextlib.suppress(OSError):
                (Path(folder) / name).chmod(stat.S_IWRITE | stat.S_IREAD)
    shutil.rmtree(clone, ignore_errors=True)


def run_checks(clone: Path, marker: Path, log: Path, timeout: float, moved: Path) -> List[Tuple[str, bool]]:
    """The checks in order; stops at the first failure, because the later ones build on it.

    The clone is moved to `moved` for the last checks.
    """
    env = clean_environment()
    results: List[Tuple[str, bool]] = []

    def check(name: str, passed: bool) -> bool:
        results.append((name, passed))
        return passed

    _ui.step("Running Setup in the clone (installs the environment, this can take a few minutes) ...")
    if not check("Setup", run_quietly(batch_command(clone / SETUP_FILE), env, clone, log, timeout)):
        return results
    venv_python = clone / "code" / "pyapp" / "generated" / ".venv" / "Scripts" / "python.exe"
    if not check("Environment created", venv_python.is_file()):
        return results
    if not check("Shortcuts created", any(clone.glob("*.lnk"))):
        return results
    _ui.step("Starting the launcher without a terminal ...")
    if not check("App started", start_without_terminal(clone, marker, env, log)):
        return results
    if not check("App ended cleanly", wait_until(lambda: no_instance_left(clone), 30)):
        return results
    logs, crash_logs = clone / "logs", clone / "crash logs"
    log_text = newest_text(logs, "log_*.txt")
    if not check("Log without a terminal", "probe print" in log_text and "probe native" in log_text):
        return results
    _ui.step("Running a dev tool ...")
    status_tool = clone / "code" / "pyapp" / "dev_tools" / "status.cmd"
    if not check("Dev tool (status)", run_quietly(batch_command(status_tool), env, clone, log, 120)):
        return results

    def run_app(mode: str, folder: Path, start_env: Dict[str, str]) -> bool:
        """Start the probe in a scenario; True once it ran and its instance has ended."""
        mode_file(marker).write_text(mode, encoding="utf-8")
        if marker.exists():
            marker.unlink()
        return start_without_terminal(folder, marker, start_env, log) and wait_until(
            lambda: no_instance_left(folder), 60
        )

    def crash_log_after(mode: str) -> str:
        """Run a failing scenario; the text of the crash log it wrote ("" if none appeared)."""
        before = len(files_in(crash_logs, "*.txt"))
        if not run_app(mode, clone, env):
            return ""
        wait_until(lambda: len(files_in(crash_logs, "*.txt")) > before, 60)
        return newest_text(crash_logs, "*.txt") if len(files_in(crash_logs, "*.txt")) > before else ""

    _ui.step("Smoke tests: a Python error and a hard crash ...")
    if not check("Python error: crash log", "probe error" in crash_log_after("error")):
        return results
    hard_crash = crash_log_after("hard_crash")
    raw_output = newest_text(logs, "*.output.log")
    if not check("Hard crash: last output kept", bool(hard_crash) and "probe last words" in raw_output):
        return results
    _ui.step("Smoke tests: starting without internet ...")
    if not check("Starts without internet", run_app("ok", clone, {**env, **NO_INTERNET})):
        return results
    _ui.step("Smoke tests: moving the folder ...")
    if not check("Folder moved", move_when_free(clone, moved)):
        return results
    if not check("Starts after moving the folder", run_app("ok", moved, env)):
        return results
    _ui.step("Running Setup again for the new place ...")
    if not check("Setup after moving", run_quietly(batch_command(moved / SETUP_FILE), env, moved, log, timeout)):
        return results
    # A shortcut stores its target folder as UTF-16 text.
    shortcuts = [path.read_bytes() for path in moved.glob("*.lnk")]
    check(
        "Shortcuts point to the new place",
        bool(shortcuts)
        and all(
            moved.name.encode("utf-16-le") in data and clone.name.encode("utf-16-le") not in data for data in shortcuts
        ),
    )
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--timeout", type=float, default=900.0, help="seconds Setup may take (default 900)")
    parser.add_argument("--keep", action="store_true", help="keep the temporary clone")
    arguments = parser.parse_args()

    WORK_DIR.mkdir(parents=True, exist_ok=True)
    # Spaces in both folder names: the launcher must quote every path it builds.
    clone = WORK_DIR / f"fresh clone {os.getpid()}"
    moved = WORK_DIR / f"moved clone {os.getpid()}"
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
        results = run_checks(clone, marker, log, arguments.timeout, moved)
        _ui.heading("Result")
        _ui.fields((name, "passed" if ok else "FAILED") for name, ok in results)
        passed = all(ok for _, ok in results)
        if not passed and log.is_file():
            _ui.heading("Last output of the launcher")
            for line in log.read_text(encoding="utf-8", errors="replace").splitlines()[-SHOWN_LOG_LINES:]:
                _ui.info(line)
    finally:
        for path in (marker, mode_file(marker), log):
            if path.exists():
                path.unlink()
        if not arguments.keep:
            remove_clone(clone)
            remove_clone(moved)

    _ui.blank_line()
    if passed:
        _ui.success("A fresh clone of this commit works.")
        return 0
    _ui.error("A fresh clone of this commit does not work. See the output above.")
    return 1


if __name__ == "__main__":
    raise SystemExit(_ui.run(main))
