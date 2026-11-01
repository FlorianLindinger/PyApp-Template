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

fail_message: str = "[Error] Failed to run open_package_terminal: {e}"
close_terminal_on_finish: bool = False
import subprocess
import sys

from backend.DONT_CHANGE.scripts.frontend_environment import (
    ensure_python_distro,
    environment_locked,
    make_file_to_indicate_frontend_pckgs_installed,
    refuse_mutation_while_running,
)
from backend.DONT_CHANGE.settings.backend_settings import (
    FRONTEND_LAUNCHER_FOR_PIP_INSTALL_TERMINAL,
)


@environment_locked
def main() -> None:
    ensure_python_distro()
    refuse_mutation_while_running()
    print('Install packages with "pip install package_name"')
    print()
    subprocess.run(
        ["cmd", "/d", "/c", "call", FRONTEND_LAUNCHER_FOR_PIP_INSTALL_TERMINAL],
        check=True,
    )
    make_file_to_indicate_frontend_pckgs_installed()
