"""Show the Git ignore rule that matches a supplied file or folder path."""

# ==============================
# settings

# ==============================
# import Python packages

import argparse
import sys
from pathlib import Path

# ==============================
# import third-party packages

# ==============================
# import from files

CODE_DIR = Path(__file__).resolve().parents[4]
if str(CODE_DIR) not in sys.path:
    sys.path.insert(0, str(CODE_DIR))

from backend.DONT_CHANGE.scripts.generic_helpers import run_git

# ==============================
# local variables

# ==============================
# local functions/classes


# ==============================
# main function


def main() -> int:
    """Parse the path and display its matching ignore rule, if any."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "path",
        nargs="?",
        help="Path to inspect, relative to the repository or absolute. Prompts when omitted.",
    )
    path = parser.parse_args().path
    if path is None:
        path = input("[Input] Path to inspect: ").strip()
    if not path:
        print("[Error] No path was provided.")
        return 2
    print(f"[Info] Checking ignore rules for: {path}", flush=True)
    exit_code = run_git(["check-ignore", "-v", "--", path])
    if exit_code == 1:
        print("[Info] This path is not ignored by Git.")
        return 0
    return exit_code


# ==============================
# execute main function


if __name__ == "__main__":
    raise SystemExit(main())
