# ruff: noqa: E402 RUF100
# The early __main__ handoff lets the shared runner catch dependency import failures.

"""Review inferred imports and replace application packages with that selection."""

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

fail_message: str = "[Error] Failed to run reset_packages -imports: {e}"
close_terminal_on_finish: bool = False
import sys

from backend.DONT_CHANGE.scripts.frontend_environment import (
    ensure_python_distro,
    install_packages_from_file,
    save_requirements_of_root_folder_noVersion,
)


def main() -> None:
    """Review inferred imports and replace application packages with that selection."""
    success, output_path = save_requirements_of_root_folder_noVersion()
    if not success:
        raise RuntimeError("Failed to determine needed packages.")
    ensure_python_distro()
    install_packages_from_file(output_path, replace=True)
    print()
    print("[Success] Finished.")
