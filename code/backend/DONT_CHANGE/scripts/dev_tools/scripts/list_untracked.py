"""Show untracked files that are not ignored by Git."""

# ==============================
# settings

fail_message: str = "[Error] Failed to run list_untracked: {e}"
close_terminal_on_finish: bool = False

import os

root_dir: str = os.path.dirname(__file__) + "\\..\\..\\..\\..\\.."

# ==============================

try:
    # ==============================
    # import Python packages

    import sys

    from pathlib import Path

    # ==============================
    # import third-party packages

    # ==============================
    # import from files

    if root_dir not in sys.path:
        sys.path.insert(0, root_dir)

    from backend.DONT_CHANGE.scripts.generic_helpers import close_terminal, input_warn, show_git_results
    from backend.DONT_CHANGE.scripts.common_code import print_traceback

    # ==============================
    # local variables

    # ==============================
    # local functions/classes

    # ==============================
    # main function

    def main() -> None:
        raise SystemExit(
            show_git_results(
                ["ls-files", "-o", "--exclude-standard"],
                heading="Untracked files that are not ignored:",
                no_results_message="No untracked, non-ignored files were found.",
            )
        )

    # ==============================
    # execute main function

    if __name__ == "__main__":
        try:
            main()
        except Exception as e:
            print_traceback(fail_message.format(e=e))
            input_warn("[Error] Press enter to exit")
        if close_terminal_on_finish:
            close_terminal()

except Exception as e:
    import traceback

    print()
    print()
    print("=" * 30)
    print(fail_message.format(e=e))
    print("-" * 30)
    print(traceback.format_exc())
    print("=" * 30)
    input("[Error] Press enter to exit")
    if close_terminal_on_finish:
        os._exit(1)
