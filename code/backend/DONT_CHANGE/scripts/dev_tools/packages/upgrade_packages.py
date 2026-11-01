"""WIP"""

if __name__ == "__main__":
    import sys
    from pathlib import Path

    code_dir = next(
        parent for parent in Path(__file__).resolve().parents if (parent / "backend" / "DONT_CHANGE").is_dir()
    )
    sys.path.insert(0, str(code_dir))
    from backend.DONT_CHANGE.scripts.entrypoint import run_file

    raise SystemExit(run_file(__file__))

fail_message: str = "[Error] Failed to run upgrade_packages: {e}"
close_terminal_on_finish: bool = False
import sys

from backend.DONT_CHANGE.scripts.frontend_environment import (
    ensure_python_distro,
    install_packages_from_file,
    save_current_packages,
)


def main() -> None:
    ensure_python_distro()
    path = save_current_packages(with_version=False)
    install_packages_from_file(path, replace=True)
    print()
    print("[Success] Finished.")
