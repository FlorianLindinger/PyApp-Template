"""Show untracked (??) and ignored (!!) files, as reported by Git status."""

import sys
from pathlib import Path

CODE_DIR = Path(__file__).resolve().parents[5]
if str(CODE_DIR) not in sys.path:
    sys.path.insert(0, str(CODE_DIR))

from backend.DONT_CHANGE.scripts._common_code import show_git_results


if __name__ == "__main__":
    print("[Info] ?? = untracked; !! = ignored.")
    raise SystemExit(
        show_git_results(
            ["status", "--ignored", "--short"],
            heading="Untracked and ignored paths:",
            no_results_message="No untracked or ignored paths were found.",
        )
    )
