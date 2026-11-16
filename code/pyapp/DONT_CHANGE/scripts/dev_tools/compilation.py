"""App syntax validation and explicit Nuitka builds using the managed interpreter."""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Generator, List, NamedTuple, Optional

from pyapp.DONT_CHANGE import backend_settings as paths
from pyapp.DONT_CHANGE.scripts.config import main_script_path, settings, validate
from pyapp.DONT_CHANGE.scripts.console_tools import print_heading, print_info, print_success
from pyapp.DONT_CHANGE.scripts.dev_tools.common import normalized, prepare
from pyapp.DONT_CHANGE.scripts.env.uv import run_uv
from pyapp.DONT_CHANGE.scripts.errors import SetupError

FOLDER = Path(paths.BACKEND_DIR) / "dev_tools" / "compilation"
CONFIG = FOLDER / "settings.json"
PRESETS = FOLDER / "presets.json"
DEFAULT_PRESETS = Path(paths.DONT_CHANGE_DIR) / "compilation" / "presets.json"
LEGACY_CONFIG = FOLDER.parent / "compilation_settings.json"
OUTPUT = Path(paths.GENERATED_DIR) / "compilation"
MARKER = ".pyapp-compilation"
BUILD_PACKAGES = ("nuitka", "ordered-set", "zstandard")


def installed_packages(python: str) -> Dict[str, str]:
    """Inspect the managed interpreter without importing third-party packages."""
    program = (
        "import json; from importlib.metadata import distributions; "
        "print(json.dumps({d.metadata['Name']:d.version for d in distributions() if d.metadata['Name']}))"
    )
    result = subprocess.run(  # noqa: S603 - fixed metadata query in the managed interpreter
        [python, "-X", "utf8", "-c", program], capture_output=True, text=True, encoding="utf-8", check=False
    )
    if result.returncode:
        raise SetupError("Cannot inspect installed packages before compilation.\n" + result.stderr.strip())
    try:
        values = json.loads(result.stdout)
    except ValueError as error:
        raise SetupError("The managed interpreter did not return valid package metadata.") from error
    if not isinstance(values, dict):
        raise SetupError("The managed interpreter did not return a package-version mapping.")
    installed: Dict[str, str] = {}
    for name, version in values.items():
        if not isinstance(name, str) or not isinstance(version, str):
            raise SetupError("Invalid package name/version in managed interpreter metadata.")
        installed[normalized(name)] = version
    return installed


@contextlib.contextmanager
def temporary_compiler(python: str) -> Generator[Dict[str, str], None, None]:
    """Expose build tools for one invocation without installing/uninstalling in the app venv.

    Existing distributions constrain the temporary resolution, keeping overlapping app
    dependencies at their installed versions. A failed install/build also removes the target.
    The caller reserves the marked OUTPUT folder before entering this context.
    """
    installed = installed_packages(python)
    env = os.environ.copy()
    if all(package in installed for package in BUILD_PACKAGES):
        print_info("Using the existing Nuitka build packages; no temporary installation needed.")
        yield env
        return
    with tempfile.TemporaryDirectory(prefix=".nuitka-build-", dir=OUTPUT) as folder:
        temporary = Path(folder)
        target = temporary / "packages"
        constraints = temporary / "installed.txt"
        constraints.write_text(
            "".join(f"{name}=={version}\n" for name, version in sorted(installed.items())), encoding="utf-8"
        )
        print_info("Installing temporary Nuitka build packages; the app environment stays unchanged.")
        try:
            run_uv(
                [
                    "pip",
                    "install",
                    "--python",
                    python,
                    "--target",
                    str(target),
                    "--constraint",
                    str(constraints),
                    *BUILD_PACKAGES,
                ]
            )
            env["PYTHONPATH"] = str(target) + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
            yield env
        finally:
            print_info("Removing temporary Nuitka build packages.")


class BuildOptions(NamedTuple):
    """Validated configuration after preset, settings and command-line overrides."""

    preset: str
    mode: str
    variant: str
    extra_args: List[str]


def _object(path: Path) -> Dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise SetupError(f"Cannot read compilation configuration {path}: {error}") from error
    if not isinstance(value, dict):
        raise SetupError(f"{path}: expected a JSON object.")
    return {str(key): item for key, item in value.items()}


def _strings(value: object, setting: str) -> List[str]:
    if not isinstance(value, list):
        raise SetupError(f"{setting} must be a list of strings.")
    result: List[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise SetupError(f"{setting} must contain nonempty strings.")
        result.append(item)
    return result


def load_options(
    preset: Optional[str], mode: Optional[str], variant: Optional[str], config: Optional[Path] = None
) -> BuildOptions:
    """Resolve CLI > settings > preset; retain old projects' extra_args without rewriting files."""
    source = CONFIG if config is None else config
    data = _object(source) if source.is_file() else {}
    known = {
        "preset",
        "mode",
        "variant",
        "jobs",
        "unbuffered",
        "extra_args",
        "plugins",
        "include_packages",
        "include_package_data",
        "include_data_files",
        "include_data_dirs",
    }
    unknown = set(data) - known
    if unknown:
        raise SetupError("Unknown compilation settings: " + ", ".join(sorted(unknown)))
    selected = preset if preset is not None else data.get("preset", "standalone")
    presets = _object(PRESETS if PRESETS.is_file() else DEFAULT_PRESETS)
    if not isinstance(selected, str) or selected not in presets:
        raise SetupError(f"Unknown compilation preset {selected!r}. Choose: {', '.join(presets)}")
    definition = presets[selected]
    if not isinstance(definition, dict):
        raise SetupError(f"Preset {selected}: expected a JSON object.")
    chosen_mode = mode if mode is not None else data.get("mode")
    if chosen_mode is None:
        chosen_mode = definition.get("mode")
    chosen_variant = variant if variant is not None else data.get("variant")
    if chosen_variant is None:
        chosen_variant = definition.get("variant")
    if not isinstance(chosen_mode, str) or chosen_mode not in ("standalone", "onefile"):
        raise SetupError("Compilation mode must be standalone or onefile.")
    if not isinstance(chosen_variant, str) or chosen_variant not in ("terminal", "no_terminal"):
        raise SetupError("Compilation variant must be terminal or no_terminal.")
    extra = _strings(definition.get("extra_args", []), f"Preset {selected} extra_args")
    if config is None and LEGACY_CONFIG.is_file():
        extra += _strings(_object(LEGACY_CONFIG).get("extra_args", []), "Legacy extra_args")
    jobs = data.get("jobs")
    if jobs is not None:
        if isinstance(jobs, bool) or not isinstance(jobs, int) or jobs < 1:
            raise SetupError("Compilation jobs must be null (automatic) or a positive integer.")
        extra.append(f"--jobs={jobs}")
    unbuffered = data.get("unbuffered")
    if unbuffered is None:
        unbuffered = definition.get("unbuffered", False)
    if not isinstance(unbuffered, bool):
        raise SetupError("Compilation unbuffered must be true, false or null (preset default).")
    if unbuffered:
        extra.append("--python-flag=unbuffered")
    for key, flag in (
        ("plugins", "enable-plugin"),
        ("include_packages", "include-package"),
        ("include_package_data", "include-package-data"),
        ("include_data_files", "include-data-files"),
        ("include_data_dirs", "include-data-dir"),
    ):
        for item in _strings(data.get(key, []), key):
            if key in ("include_data_files", "include_data_dirs") and ("=" not in item or not all(item.split("=", 1))):
                raise SetupError(f"{key} entries must be source=destination mappings.")
            extra.append(f"--{flag}={item}")
    extra += _strings(data.get("extra_args", []), "extra_args")
    reserved = (
        "--output-dir",
        "--output-filename",
        "--report",
        "--remove-output",
        "--mode",
        "--standalone",
        "--onefile",
        "--windows-console-mode",
        "--disable-console",
        "--run",
    )
    if any(arg.startswith(reserved) for arg in extra):
        raise SetupError(
            "Extra arguments must be Nuitka options; mode, console, output/report paths and execution are reserved."
        )
    # Preset names also form an output-directory component.
    if not selected or any(character not in "abcdefghijklmnopqrstuvwxyz0123456789-_" for character in selected):
        raise SetupError("Preset names must use lowercase letters, numbers, hyphens or underscores.")
    return BuildOptions(selected, chosen_mode, chosen_variant, extra)


def cmd_compilation_presets(_arguments: List[str]) -> None:
    """List the editable compilation presets and their intended use."""
    print_heading("Compilation presets")
    source = PRESETS if PRESETS.is_file() else DEFAULT_PRESETS
    for name, value in _object(source).items():
        description = value.get("description", "") if isinstance(value, dict) else "invalid preset"
        print_info(f"{name}: {description}")
    print_info(f"Settings: {CONFIG}\nPresets: {source}")


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


def build_command(
    python: str, script: Path, mode: str, terminal: bool, extra: List[str], preset: str = ""
) -> List[str]:
    """Build the configured application directly; launcher supervision is not bundled."""
    variant = "terminal" if terminal else "no_terminal"
    output = (OUTPUT / preset if preset else OUTPUT) / variant / mode
    return [
        python,
        "-m",
        "nuitka",
        f"--mode={mode}",
        "--windows-console-mode=" + ("force" if terminal else "disable"),
        f"--windows-icon-from-ico={paths.ICON_PATH}",
        f"--output-dir={output}",
        f"--report={output / 'compilation-report.xml'}",
        *extra,
        str(script),
    ]


def cmd_compile_app(arguments: List[str]) -> None:
    """Build the app using an editable preset; --dry-run previews the effective command."""
    parser = argparse.ArgumentParser(description=cmd_compile_app.__doc__)
    parser.add_argument("variant", nargs="?", choices=("terminal", "no_terminal"), default=None)
    parser.add_argument("--mode", choices=("standalone", "onefile"), default=None)
    parser.add_argument("--preset", help="preset in compilation/presets.json; overrides settings.json")
    parser.add_argument("--dry-run", action="store_true")
    options = parser.parse_args(arguments)
    build = load_options(options.preset, options.mode, options.variant)
    s = settings()
    if options.dry_run:
        validate(s)
        python = paths.VENV_PYTHON_EXE
    else:
        python = prepare(s).exe
    command = build_command(
        python, Path(main_script_path(s)), build.mode, build.variant == "terminal", build.extra_args, build.preset
    )
    print_heading("Compile app")
    print_info(f"Preset: {build.preset}; mode: {build.mode}; console: {build.variant}")
    print_info(subprocess.list2cmdline(command))
    if options.dry_run:
        return
    validate_sources(python, app_sources(Path(paths.PYTHON_SCRIPTS_DIR)))
    if OUTPUT.exists() and not (OUTPUT / MARKER).is_file():
        raise SetupError(f"Refusing to reuse an unowned output folder: {OUTPUT}")
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / MARKER).write_text("PyApp compilation output\n", encoding="utf-8")
    target = OUTPUT / build.preset / build.variant / build.mode
    target.mkdir(parents=True, exist_ok=True)
    with temporary_compiler(python) as env:
        result = subprocess.run(  # noqa: S603 - configured compiler, no shell
            command, cwd=paths.PYTHON_SCRIPTS_DIR, env=env, check=False
        )
        if result.returncode:
            raise SetupError("Nuitka compilation failed; see the compiler output above.")
    print_success(f"Build completed: {target}. Test the produced application on a clean target machine.")


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
