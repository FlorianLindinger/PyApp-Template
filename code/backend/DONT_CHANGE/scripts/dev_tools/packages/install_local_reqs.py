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

fail_message: str = "[Error] Failed to run install_local_reqs: {e}"
close_terminal_on_finish: bool = False
import os
import sys

from backend.DONT_CHANGE.scripts.frontend_environment import (
    ensure_python_distro,
    install_packages_from_file,
)


def main() -> None:
    ensure_python_distro()
    install_packages_from_file(os.path.join(os.getcwd(), "requirements.txt"))
    print()
    print("[Success] Finished.")
