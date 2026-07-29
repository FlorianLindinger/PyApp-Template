"""Show untracked files that are not ignored by Git."""

import sys
from pathlib import Path

CODE_DIR = Path(__file__).resolve().parents[5]
if str(CODE_DIR) not in sys.path:
    sys.path.insert(0, str(CODE_DIR))

from backend.DONT_CHANGE.scripts.common_code import show_git_results


if __name__ == "__main__":
    raise SystemExit(
        show_git_results(
            ["ls-files", "-o", "--exclude-standard"],
            heading="Untracked files that are not ignored:",
            no_results_message="No untracked, non-ignored files were found.",
        )
    )
