"""Run main.py lint, formatting, and type-check verification."""

from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path

# =============================================================================
# Verification settings
# Paths are relative to the code folder. Use forward slashes.

TARGETS = ("main.py",)

# Files and folders listed here are skipped by both Ruff and Pyrefly.
EXCLUDED_FILES: tuple[str, ...] = ()
EXCLUDED_FOLDERS: tuple[str, ...] = ()

# =============================================================================

VALID_PRESETS = ("basic", "default", "strict")
CODE_DIR = Path(__file__).resolve().parents[4]


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
    folder_patterns = tuple(f"{folder.rstrip('/')}/**" for folder in EXCLUDED_FOLDERS)
    return EXCLUDED_FILES + folder_patterns


def run_check(label: str, command: list[str]) -> bool:
    """Run one check and return whether it succeeded."""
    print(f"\n[Info] {label}", flush=True)
    result = subprocess.run(command, cwd=CODE_DIR, check=False)  # noqa: S603
    return result.returncode == 0


def verify(preset: str) -> int:
    """Run every main.py verification gate for a Pyrefly preset."""
    try:
        ruff = tool_command("ruff")
        pyrefly = tool_command("pyrefly")
    except FileNotFoundError as error:
        print(f"[Error] {error}")
        return 2

    ruff_patterns = EXCLUDED_FILES + EXCLUDED_FOLDERS
    ruff_exclusions = ["--exclude", ",".join(ruff_patterns)] if ruff_patterns else []
    pyrefly_exclusions = [argument for pattern in exclusion_patterns() for argument in ("--project-excludes", pattern)]

    checks = (
        ("Ruff lint: main.py", [*ruff, "check", *TARGETS, *ruff_exclusions]),
        (
            "Ruff format: main.py",
            [*ruff, "format", "--check", *TARGETS, *ruff_exclusions],
        ),
        (
            f"Pyrefly {preset}: main.py",
            [
                *pyrefly,
                "check",
                "--preset",
                preset,
                *pyrefly_exclusions,
                *TARGETS,
            ],
        ),
    )

    succeeded = True
    for label, command in checks:
        if not run_check(label, command):
            succeeded = False
    if succeeded:
        print(f"\n[Success] main.py passed {preset} verification.")
        return 0

    print(f"\n[Error] main.py failed {preset} verification.")
    return 1


def main() -> int:
    """Parse the requested preset and run verification."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "preset",
        choices=VALID_PRESETS,
        nargs="?",
        default="default",
        help="Pyrefly preset to use (default: default).",
    )
    return verify(parser.parse_args().preset)


if __name__ == "__main__":
    raise SystemExit(main())
