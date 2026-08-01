"""Run backend lint, formatting, and type-check verification."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

CODE_DIR = Path(__file__).resolve().parents[3]
if str(CODE_DIR) not in sys.path:
    sys.path.insert(0, str(CODE_DIR))

from backend.DONT_CHANGE.settings.backend_settings import (
    BACKEND_VERIFICATION_DEFAULT_PRESET,
    BACKEND_VERIFICATION_EXCLUDED_FILES,
    BACKEND_VERIFICATION_EXCLUDED_FOLDERS,
    BACKEND_VERIFICATION_TARGETS,
    BACKEND_VERIFICATION_VALID_PRESETS,
)


def tool_command(tool: str) -> list[str]:
    """Use an installed tool directly, falling back to an ephemeral uv tool."""
    installed_tool = shutil.which(tool)
    if installed_tool:
        return [installed_tool]

    uvx = shutil.which("uvx")
    if uvx:
        return [uvx, tool]

    raise FileNotFoundError(f'Neither "{tool}" nor "uvx" was found on PATH.')


def exclusion_patterns() -> tuple[str, ...]:
    """Return file and recursive folder patterns understood by both tools."""
    folder_patterns = tuple(f"{folder.rstrip('/')}/**" for folder in BACKEND_VERIFICATION_EXCLUDED_FOLDERS)
    return BACKEND_VERIFICATION_EXCLUDED_FILES + folder_patterns


def run_check(label: str, command: list[str]) -> bool:
    """Run one check and return whether it succeeded."""
    print(f"\n[Info] {label}", flush=True)
    result = subprocess.run(command, cwd=CODE_DIR, check=False)  # noqa: S603
    return result.returncode == 0


def verify(preset: str) -> int:
    """Run every backend verification gate for a Pyrefly preset."""
    try:
        ruff = tool_command("ruff")
        pyrefly = tool_command("pyrefly")
    except FileNotFoundError as error:
        print(f"[Error] {error}")
        return 2

    ruff_patterns = BACKEND_VERIFICATION_EXCLUDED_FILES + BACKEND_VERIFICATION_EXCLUDED_FOLDERS
    ruff_exclusions = ["--exclude", ",".join(ruff_patterns)] if ruff_patterns else []
    pyrefly_exclusions = [argument for pattern in exclusion_patterns() for argument in ("--project-excludes", pattern)]

    checks = (
        ("Ruff lint: backend", [*ruff, "check", *BACKEND_VERIFICATION_TARGETS, *ruff_exclusions]),
        (
            "Ruff format: backend",
            [*ruff, "format", "--check", *BACKEND_VERIFICATION_TARGETS, *ruff_exclusions],
        ),
        (
            f"Pyrefly {preset}: backend",
            [
                *pyrefly,
                "check",
                "--preset",
                preset,
                *pyrefly_exclusions,
                *BACKEND_VERIFICATION_TARGETS,
            ],
        ),
    )

    succeeded = True
    for label, command in checks:
        if not run_check(label, command):
            succeeded = False
    if succeeded:
        print(f"\n[Success] The backend passed {preset} verification.")
        return 0

    print(f"\n[Error] The backend failed {preset} verification.")
    return 1


def main() -> int:
    """Parse the requested preset and run verification."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "preset",
        choices=BACKEND_VERIFICATION_VALID_PRESETS,
        nargs="?",
        default=BACKEND_VERIFICATION_DEFAULT_PRESET,
        help=f"Pyrefly preset to use (default: {BACKEND_VERIFICATION_DEFAULT_PRESET}).",
    )
    return verify(parser.parse_args().preset)


if __name__ == "__main__":
    raise SystemExit(main())
