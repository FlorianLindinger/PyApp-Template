"""Show tracked files that have been deleted from the working tree."""

if __name__ == "__main__":
    import sys
    from pathlib import Path

    code_dir = next(
        parent for parent in Path(__file__).resolve().parents if (parent / "backend" / "DONT_CHANGE").is_dir()
    )
    sys.path.insert(0, str(code_dir))
    from backend.DONT_CHANGE.scripts.entrypoint import run_file

    raise SystemExit(run_file(__file__))

fail_message: str = "[Error] Failed to run list_deleted: {e}"
close_terminal_on_finish: bool = False
import sys

from backend.DONT_CHANGE.scripts.git_tools import show_git_results


def main() -> None:
    raise SystemExit(
        show_git_results(
            ["ls-files", "-d"],
            heading="Tracked files deleted from the working tree:",
            no_results_message="No tracked files have been deleted.",
        )
    )
