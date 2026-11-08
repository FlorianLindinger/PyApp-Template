"""Lint, format-check and type-check the launcher (code/backend/DONT_CHANGE).

Uses the launcher's own ruff.toml and pyrefly.toml (Python 3.8, 120 columns). Usage:

    verify_launcher.bat            check only
    verify_launcher.bat --fix      apply Ruff's safe fixes and formatting first
"""

from __future__ import annotations

import argparse
import shutil
import subprocess

from _paths import DONT_CHANGE_DIR


def tool_command(tool: str) -> list[str]:
    """The tool from PATH, else run it through uvx."""
    installed = shutil.which(tool)
    if installed:
        return [installed]
    uvx = shutil.which("uvx")
    if uvx:
        return [uvx, tool]
    raise FileNotFoundError(f'Neither "{tool}" nor "uvx" was found on PATH.')


def run_check(label: str, command: list[str]) -> bool:
    print(f"\n[Info] {label}", flush=True)
    # Execute the Ruff/Pyrefly command resolved from local PATH or uvx.
    code = subprocess.run(command, cwd=DONT_CHANGE_DIR, check=False).returncode  # noqa: S603
    if code == 1:
        print(f"[Warning] {label} reported problems; see the diagnostics above.", flush=True)
    elif code != 0:
        print(f"[Error] {label} could not complete (exit code {code}).", flush=True)
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
        print(f"[Error] {error}")
        return 2

    checks = [
        (
            "Ruff lint",
            [*ruff, "check", *(["--fix"] if fix else []), *(["--unsafe-fixes"] if arguments.unsafe_fixes else []), "."],
        ),
        ("Ruff format", [*ruff, "format", *([] if fix else ["--check"]), "."]),
        ("Pyrefly", [*pyrefly, "check"]),
    ]
    results = [run_check(label, command) for label, command in checks]
    if all(results):
        print("\n[Success] The launcher passed verification.")
        return 0
    print("\n[Error] The launcher failed verification.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
