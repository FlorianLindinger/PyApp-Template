# ruff: noqa: E402
# The early __main__ handoff lets the shared runner catch dependency import failures.

"""WIP"""

if __name__ == "__main__":
    import sys
    from pathlib import Path

    code_dir = next(
        parent
        for parent in Path(__file__).resolve().parents
        if (parent / "backend" / "DONT_CHANGE").is_dir()
    )
    sys.path.insert(0, str(code_dir))
    from backend.DONT_CHANGE.scripts.entrypoint import run_file

    raise SystemExit(run_file(__file__))

fail_message: str = "[Error] Failed to run save_imported_packages -versions: {e}"
close_terminal_on_finish: bool = False
import sys

from backend.DONT_CHANGE.scripts.frontend_environment import (
    save_requirements_of_root_folder_withVersion,
)


def main() -> None:
    success = save_requirements_of_root_folder_withVersion()
    if not success:
        raise RuntimeError("Failed to determine needed packages with versions.")
    print()
    print("[Success] Finished.")
