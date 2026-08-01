"""Run main.py lint, formatting, and type-check verification."""

# ==============================
# settings

# ==============================
# import Python packages
import argparse
import shutil
import subprocess
import sys
from pathlib import Path

# ==============================
# import third-party packages

# ==============================
# import from files

# ==============================
# local variables

# Paths are relative to the code folder. Use forward slashes.
TARGETS = ("main.py",)

# Files and folders listed here are skipped by both Ruff and Pyrefly.
EXCLUDED_FILES: tuple[str, ...] = ()
EXCLUDED_FOLDERS: tuple[str, ...] = ()

VALID_PRESETS = ("basic", "default", "strict")
CODE_DIR = Path(__file__).resolve().parents[4]

# ==============================
# local functions/classes


def tool_command(tool: str) -> list[str]:
    """Use a PATH tool, this interpreter's tool, or an ephemeral uv tool."""
    installed_tool = shutil.which(tool)
    if installed_tool:
        return [installed_tool]

    scripts_dir = Path(sys.executable).parent / "Scripts"
    embedded_tool = scripts_dir / f"{tool}.exe"
    if embedded_tool.is_file():
        return [str(embedded_tool)]

    embedded_uvx = scripts_dir / "uvx.exe"
    uvx = shutil.which("uvx") or (str(embedded_uvx) if embedded_uvx.is_file() else None)
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


def verify(preset: str, *, fix: bool) -> int:
    """Run main.py verification, optionally applying safe Ruff fixes first."""
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
        (
            "Ruff lint/fix: main.py" if fix else "Ruff lint: main.py",
            [*ruff, "check", *(("--fix",) if fix else ()), *TARGETS, *ruff_exclusions],
        ),
        (
            "Ruff format/fix: main.py" if fix else "Ruff format: main.py",
            [*ruff, "format", *(("--check",) if not fix else ()), *TARGETS, *ruff_exclusions],
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


# ==============================
# main function


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
    parser.add_argument(
        "--fix", action="store_true", help="Apply safe Ruff lint and formatting fixes before verification."
    )
    arguments = parser.parse_args()
    return verify(arguments.preset, fix=arguments.fix)


# ==============================
# execute main function


if __name__ == "__main__":
    raise SystemExit(main())
