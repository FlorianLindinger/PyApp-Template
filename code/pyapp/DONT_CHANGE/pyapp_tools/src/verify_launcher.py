"""Lint, format-check and type-check the launcher (code/pyapp/DONT_CHANGE).

Uses the launcher's own ruff.toml and pyrefly.toml (Python 3.8, 120 columns). Usage:

    verify_launcher.bat            check only
    verify_launcher.bat --fix      apply Ruff's safe fixes and formatting first
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
from typing import Dict, List, Optional, Tuple

import _ui
from _paths import DONT_CHANGE_DIR

# The oldest versions that pass with ruff.toml and pyrefly.toml (found by trying the releases):
# older Pyrefly stops at the error names in pyrefly.toml ("Fatal configuration error"), and older
# Ruff reports problems the configuration does not expect. ruff.toml also has required-version.
MINIMUM_VERSIONS: Dict[str, Tuple[int, ...]] = {"ruff": (0, 17, 0), "pyrefly": (1, 4, 0)}


def version_text(version: Tuple[int, ...]) -> str:
    return ".".join(map(str, version))


def tool_version(executable: str) -> Optional[Tuple[int, ...]]:
    """(0, 17, 4) from "ruff 0.17.4"; None if the program does not say."""
    try:
        # A tool found on PATH, asked for its version only.
        output = subprocess.run(  # noqa: S603
            [executable, "--version"], capture_output=True, text=True, check=False, timeout=60
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    match = re.search(r"(\d+)\.(\d+)\.(\d+)", output)
    return tuple(int(part) for part in match.groups()) if match else None


def tool_command(tool: str) -> List[str]:
    """The tool from PATH if it is new enough, else a new enough one through uvx."""
    minimum = MINIMUM_VERSIONS[tool]
    installed = shutil.which(tool)
    version = tool_version(installed) if installed else None
    if installed and version is not None and version >= minimum:
        return [installed]
    uvx = shutil.which("uvx")
    if uvx:
        return [uvx, "--from", f"{tool}>={version_text(minimum)}", tool]
    if installed:
        found = version_text(version) if version else "of unknown version"
        raise FileNotFoundError(
            f'"{tool}" on PATH is {found}; the launcher\'s checks need {version_text(minimum)} or newer '
            f"(update it, e.g. uv tool upgrade {tool}, or install uv for uvx)."
        )
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
