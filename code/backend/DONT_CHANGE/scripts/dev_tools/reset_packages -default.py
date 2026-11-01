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

fail_message: str = "[Error] Failed to run reset_packages -default: {e}"
close_terminal_on_finish: bool = False
import sys

from backend.DONT_CHANGE.scripts.frontend_environment import ensure_python_distro, install_packages_from_file
from backend.DONT_CHANGE.settings.backend_settings import DEFAULT_PACKAGES_PATH


def main() -> None:
    ensure_python_distro()
    install_packages_from_file(DEFAULT_PACKAGES_PATH, replace=True)
    print()
    print("[Success] Finished.")
