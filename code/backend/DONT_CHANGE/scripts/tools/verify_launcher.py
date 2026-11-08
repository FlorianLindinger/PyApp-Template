"""Lint, format-check and type-check the launcher (code/backend/DONT_CHANGE).

Uses the launcher's own ruff.toml and pyrefly.toml (Python 3.8, 120 columns). Usage:

    verify_launcher.bat            check only
    verify_launcher.bat --fix      apply Ruff's safe fixes and formatting first
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
from typing import List

import _ui
from _paths import DONT_CHANGE_DIR


def tool_command(tool: str) -> List[str]:
    """The tool from PATH, else run it through uvx."""
    installed = shutil.which(tool)
    if installed:
        return [installed]
    uvx = shutil.which("uvx")
    if uvx:
        return [uvx, tool]
    raise FileNotFoundError(f'Neither "{tool}" nor "uvx" was found on PATH.')


def run_check(label: str, command: List[str]) -> bool:
    _ui.heading(label)
    # Execute the Ruff/Pyrefly command resolved from local PATH or uvx.
    code = subprocess.run(command, cwd=DONT_CHANGE_DIR, check=False).returncode  # noqa: S603
    if code == 1:
        _ui.warn(f"{label} reported problems; see the diagnostics above.")
    elif code != 0:
        _ui.error(f"{label} could not complete (exit code {code}).")
    return code == 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--fix", action="store_true", help="apply safe Ruff fixes and formatting before checking")
    parser.add_argument("--unsafe-fixes", action="store_true", help="also apply Ruff's unsafe fixes")
    arguments = parser.parse_args()
    fix = arguments.fix or arguments.unsafe_fixes
    try:
        ruff = tool_command("ruff")
        pyrefly = tool_command("pyrefly")
    except FileNotFoundError as error:
        _ui.error(error)
        return 2

    checks = [
        (
            "Ruff lint",
            [*ruff, "check", *(["--fix"] if fix else []), *(["--unsafe-fixes"] if arguments.unsafe_fixes else []), "."],
        ),
        ("Ruff format", [*ruff, "format", *([] if fix else ["--check"]), "."]),
        ("Pyrefly", [*pyrefly, "check"]),
    ]
    _ui.heading("Verify the launcher")
    _ui.fields(
        [
            ("Folder", DONT_CHANGE_DIR),
            ("Ruff config", DONT_CHANGE_DIR / "ruff.toml"),  # the closest one to the checked folder
            ("Pyrefly config", DONT_CHANGE_DIR / "pyrefly.toml"),
        ]
    )
    results = [run_check(label, command) for label, command in checks]
    _ui.heading("Result")
    _ui.fields((label, "passed" if passed else "FAILED") for (label, _), passed in zip(checks, results))
    _ui.blank_line()
    if all(results):
        _ui.success("The launcher passed verification.")
        return 0
    _ui.error("The launcher failed verification.")
    return 1


if __name__ == "__main__":
    raise SystemExit(_ui.run(main))
