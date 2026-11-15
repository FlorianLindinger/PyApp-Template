"""App syntax validation and explicit Nuitka builds using the managed interpreter."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path
from typing import List

from pyapp.DONT_CHANGE import backend_settings as paths
from pyapp.DONT_CHANGE.scripts.config import main_script_path, settings, validate
from pyapp.DONT_CHANGE.scripts.console_tools import print_heading, print_info, print_success
from pyapp.DONT_CHANGE.scripts.dev_tools.common import prepare
from pyapp.DONT_CHANGE.scripts.errors import SetupError

CONFIG = Path(paths.BACKEND_DIR) / "dev_tools" / "compilation_settings.json"
OUTPUT = Path(paths.GENERATED_DIR) / "compilation"
MARKER = ".pyapp-compilation"


def app_sources(code: Path) -> List[Path]:
    """App Python sources, excluding the launcher, environments and linked external folders."""
    sources: List[Path] = []
    pending = [code]
    root = code.resolve()
    while pending:
        for path in pending.pop().iterdir():
            if path.is_symlink() or root not in path.resolve().parents:
                continue
            if path.is_dir():
                if (
                    path.name.startswith(".")
                    or path.name in ("pyapp", "__pycache__")
                    or (path / "pyvenv.cfg").is_file()
                ):
                    continue
                pending.append(path)
            elif path.suffix.lower() in (".py", ".pyw"):
                sources.append(path)
    return sorted(sources)


def validate_sources(python: str, sources: List[Path]) -> None:
    """Use the real interpreter's compiler without importing the app or writing .pyc files."""
    program = (
        "import json,sys; from pathlib import Path; "
        "sources=json.load(sys.stdin); "
        "[compile(Path(p).read_bytes(), p, 'exec') for p in sources]; "
        "print(str(len(sources))+' Python files compiled successfully (syntax only).')"
    )
    # Fixed standard-library validation code; paths are JSON data, never shell source.
    result = subprocess.run(  # noqa: S603
        [python, "-E", "-c", program], input=json.dumps([str(p) for p in sources]), text=True, check=False
    )
    if result.returncode:
        raise SetupError("Python syntax validation failed; see the compiler diagnostic above.")


def cmd_validate_syntax(_arguments: List[str]) -> None:
    """Compile app source syntax with its managed Python, without executing the app."""
    print_heading("Validate app syntax")
    app = prepare()
    validate_sources(app.exe, app_sources(Path(paths.PYTHON_SCRIPTS_DIR)))


def build_command(python: str, script: Path, mode: str, terminal: bool, extra: List[str]) -> List[str]:
    """Build the configured application directly; launcher supervision is not bundled."""
    variant = "terminal" if terminal else "no_terminal"
    return [
        python,
        "-m",
        "nuitka",
        f"--mode={mode}",
        "--windows-console-mode=" + ("force" if terminal else "disable"),
        f"--windows-icon-from-ico={paths.ICON_PATH}",
        f"--output-dir={OUTPUT / variant / mode}",
        f"--report={OUTPUT / variant / mode / 'compilation-report.xml'}",
        *extra,
        str(script),
    ]


def cmd_compile_app(arguments: List[str]) -> None:
    """Build the app with Nuitka: terminal/no_terminal, standalone/onefile, optional --dry-run."""
    parser = argparse.ArgumentParser(description=cmd_compile_app.__doc__)
    parser.add_argument("variant", nargs="?", choices=("terminal", "no_terminal"), default="terminal")
    parser.add_argument("--mode", choices=("standalone", "onefile"), default="standalone")
    parser.add_argument("--dry-run", action="store_true")
    options = parser.parse_args(arguments)
    s = settings()
    if options.dry_run:
        validate(s)
        python = paths.VENV_PYTHON_EXE
    else:
        python = prepare(s).exe
    extra: List[str] = []
    if CONFIG.is_file():
        data = json.loads(CONFIG.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise SetupError(f"{CONFIG}: expected a JSON object with extra_args.")
        extra = data.get("extra_args", [])
        if not isinstance(extra, list) or not all(isinstance(item, str) for item in extra):
            raise SetupError(f"{CONFIG}: extra_args must be a list of strings.")
        if any(arg.startswith(("--output-dir", "--report", "--remove-output")) for arg in extra):
            raise SetupError("Output and report paths are owned by the compilation tool; remove those overrides.")
    command = build_command(python, Path(main_script_path(s)), options.mode, options.variant == "terminal", extra)
    print_heading("Compile app")
    print_info(subprocess.list2cmdline(command))
    if options.dry_run:
        return
    validate_sources(python, app_sources(Path(paths.PYTHON_SCRIPTS_DIR)))
    # Optional compiler packages are installed only by the developer, never by this tool.
    available = subprocess.run(  # noqa: S603
        [python, "-c", "import nuitka"], capture_output=True, check=False
    )
    if available.returncode:
        raise SetupError(
            "Nuitka is not installed in the managed environment. In the dev terminal run "
            "'uv pip install nuitka ordered-set zstandard'; a supported C compiler is also required. "
            "See code/pyapp/dev_tools/COMPILATION.md."
        )
    if OUTPUT.exists() and not (OUTPUT / MARKER).is_file():
        raise SetupError(f"Refusing to reuse an unowned output folder: {OUTPUT}")
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / MARKER).write_text("PyApp compilation output\n", encoding="utf-8")
    (OUTPUT / options.variant / options.mode).mkdir(parents=True, exist_ok=True)
    result = subprocess.run(  # noqa: S603 - configured compiler, no shell
        command, cwd=paths.PYTHON_SCRIPTS_DIR, check=False
    )
    if result.returncode:
        raise SetupError("Nuitka compilation failed; see the compiler output above.")
    print_success(f"Build completed: {OUTPUT}. Test the produced application on a clean target machine.")


def cmd_clean_compilation(_arguments: List[str]) -> None:
    """Remove only the compilation tool's marked generated output; preserve compiler caches."""
    target = OUTPUT.resolve()
    parent = Path(paths.GENERATED_DIR).resolve()
    if target.parent != parent or target.name != "compilation" or OUTPUT.is_symlink():
        raise SetupError("Compilation output resolves outside the owned generated folder.")
    if not target.exists():
        print_info("No compilation output to remove.")
        return
    if not (target / MARKER).is_file():
        raise SetupError(f"Refusing to delete unowned output: {target}")
    shutil.rmtree(target)
    print_success("Removed compilation output.")
