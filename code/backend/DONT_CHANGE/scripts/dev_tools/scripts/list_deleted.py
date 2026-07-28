"""Show tracked files that have been deleted from the working tree."""

import sys
from pathlib import Path

CODE_DIR = Path(__file__).resolve().parents[5]
if str(CODE_DIR) not in sys.path:
    sys.path.insert(0, str(CODE_DIR))

from backend.DONT_CHANGE.scripts._common_code import show_git_results


if __name__ == "__main__":
    raise SystemExit(
        show_git_results(
            ["ls-files", "-d"],
            heading="Tracked files deleted from the working tree:",
            no_results_message="No tracked files have been deleted.",
        )
    )
