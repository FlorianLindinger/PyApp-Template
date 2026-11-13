"""Run the launcher's regression tests on the oldest supported and the newest Python.

    test_all_pythons.bat                     Python 3.8 and the newest stable Python
    test_all_pythons.bat 3.10 3.12           these versions instead
    test_all_pythons.bat --pattern test_wrapper.py
    test_all_pythons.bat --pattern browser       one group of tests/src/groups.py

The Pythons are kept in a folder in your temporary directory, so they are downloaded once and
neither the project nor your installed Pythons change.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import _ui
from _paths import DONT_CHANGE_DIR

PYTHONS_DIR = Path(tempfile.gettempdir()) / "pyapp_test_pythons"
RUNNER = DONT_CHANGE_DIR / "tests" / "src" / "run_regressions.py"
OLDEST_SUPPORTED = "3.8"
NEWEST = "newest"
TIMEOUT_SECONDS = 600
SHOWN_FAILURE_LINES = 60


def find_uv() -> str:
    """The uv the launcher's bootstrap chose, else the one on PATH."""
    chosen = os.environ.get("PYAPP_UV", "")
    if chosen and Path(chosen).is_file():
        return chosen
    found = shutil.which("uv")
    if found:
        return found
    raise RuntimeError("uv was not found. Start the app or run Setup once, so the launcher can install it.")


def uv_environment() -> Dict[str, str]:
    """Pythons go into PYTHONS_DIR only: not on PATH and not into the Windows registry."""
    env = {key: value for key, value in os.environ.items() if key.upper() != "UV_PYTHON"}
    env.update(
        UV_PYTHON_INSTALL_DIR=str(PYTHONS_DIR),
        UV_MANAGED_PYTHON="1",
        UV_PYTHON_INSTALL_BIN="0",
        UV_PYTHON_INSTALL_REGISTRY="0",
    )
    return env


def uv_output(uv: str, arguments: List[str]) -> Optional[str]:
    """Output of a uv command, or None if it failed. Outside the project: uv would prefer its environment."""
    # The launcher's uv with fixed arguments and version numbers.
    completed = subprocess.run(  # noqa: S603
        [uv, *arguments],
        cwd=tempfile.gettempdir(),
        env=uv_environment(),
        capture_output=True,
        check=False,
    )
    return completed.stdout.decode("utf-8", "replace") if completed.returncode == 0 else None


def newest_stable(downloads: List[Dict[str, str]]) -> str:
    """ "X.Y" of the newest stable CPython in uv's list of downloads."""
    versions = [
        tuple(int(part) for part in entry["version"].split("."))
        for entry in downloads
        if entry.get("implementation") == "cpython"
        and entry.get("variant") == "default"
        and re.fullmatch(r"\d+\.\d+\.\d+", entry.get("version", ""))
    ]
    if not versions:
        raise RuntimeError("uv could not list the downloadable Pythons (no internet?). Name the versions to test.")
    newest = max(versions)
    return f"{newest[0]}.{newest[1]}"


def resolve_requests(uv: str, requests: List[str]) -> List[str]:
    """Replace "newest" with a version number and drop duplicates, keeping the order."""
    resolved: List[str] = []
    for requested in requests:
        request = requested
        if requested == NEWEST:
            listing = uv_output(uv, ["python", "list", "--only-downloads", "--output-format", "json"])
            request = newest_stable(json.loads(listing or "[]"))
        if request not in resolved:
            resolved.append(request)
    return resolved


def python_for(uv: str, request: str) -> str:
    """The interpreter for a version, downloaded the first time."""

    def find() -> str:
        lines = (uv_output(uv, ["python", "find", "--no-project", request]) or "").split()
        return " ".join(lines)

    found = find()
    if not found:
        _ui.step(f"Downloading Python {request} ...")
        uv_output(uv, ["python", "install", request])
        found = find()
    if not found:
        raise RuntimeError(f"uv could not provide Python {request}.")
    return found


def summary_of(output: str) -> Tuple[str, str]:
    """(number of tests, unittest's result line) of the runner's output."""
    ran = re.search(r"^Ran (\d+) tests? in", output, flags=re.MULTILINE)
    results = re.findall(r"^(?:OK|FAILED)\b.*$", output, flags=re.MULTILINE)
    return (ran.group(1) if ran else "?"), (results[-1].strip() if results else "no result")


def failure_details(output: str) -> List[str]:
    """unittest's failure reports, without the messages printed while the tests ran."""
    lines = output.splitlines()
    start = next((index for index, line in enumerate(lines) if line.startswith("=====")), 0)
    return lines[start:][:SHOWN_FAILURE_LINES]


def run_tests(python: str, pattern: Optional[str]) -> Tuple[bool, str]:
    """Run the suite with one interpreter; (passed, combined output)."""
    env = {key: value for key, value in os.environ.items() if not key.upper().startswith("PYAPP_")}
    command = [python, "-B", "-X", "utf8", str(RUNNER), "-q", *([pattern] if pattern else [])]
    try:
        # The chosen interpreter runs this checkout's fixed test runner.
        completed = subprocess.run(  # noqa: S603
            command,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return False, f"The tests did not finish within {TIMEOUT_SECONDS} seconds."
    return completed.returncode == 0, completed.stdout.decode("utf-8", "replace")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("versions", nargs="*", help='Python versions, or "newest" (default: 3.8 and newest)')
    parser.add_argument("--pattern", help="test file pattern or group, e.g. test_wrapper.py or browser")
    arguments = parser.parse_args()

    _ui.heading("Launcher tests on several Pythons")
    uv = find_uv()
    requests = resolve_requests(uv, arguments.versions or [OLDEST_SUPPORTED, NEWEST])
    _ui.fields([("Pythons", ", ".join(requests)), ("Kept in", PYTHONS_DIR)])
    rows = []
    failures: List[Tuple[str, str]] = []
    for request in requests:
        python = python_for(uv, request)
        _ui.step(f"Testing on Python {request} ...")
        started = time.monotonic()
        passed, output = run_tests(python, arguments.pattern)
        tests, result = summary_of(output)
        rows.append((request, tests, f"{time.monotonic() - started:.0f} s", result))
        if not passed:
            failures.append((request, output))

    _ui.heading("Result")
    _ui.table(("Python", "tests", "time", "result"), rows)
    for request, output in failures:
        _ui.heading(f"Failures on Python {request}")
        for line in failure_details(output):
            _ui.info(line)
    _ui.blank_line()
    if failures:
        _ui.error(f"Tests failed on: {', '.join(request for request, _ in failures)}.")
        return 1
    _ui.success(f"All tests passed on {len(rows)} Python version(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(_ui.run(main))
