"""App syntax validation and explicit Nuitka builds using the managed interpreter."""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Dict, Generator, List, NamedTuple, Optional

from pyapp.DONT_CHANGE import backend_settings as paths
from pyapp.DONT_CHANGE.scripts.config import main_script_path, settings, validate
from pyapp.DONT_CHANGE.scripts.console_tools import (
    ANSI_BOLD,
    ANSI_DIM,
    ANSI_GOOD,
    ask,
    print_fields,
    print_heading,
    print_info,
    print_success,
    styled,
)
from pyapp.DONT_CHANGE.scripts.dev_tools.common import normalized, prepare
from pyapp.DONT_CHANGE.scripts.env.uv import run_uv
from pyapp.DONT_CHANGE.scripts.errors import SetupError

# The editable settings: code/pyapp/compilation.
FOLDER = Path(paths.BACKEND_DIR) / "compilation"
CONFIG = FOLDER / "settings.json"
PRESETS = FOLDER / "presets.json"
LINUX_CONFIG = FOLDER / "linux_settings.json"
# The shipped presets, used when the project's presets.json is missing.
DEFAULT_PRESETS = Path(paths.DATA_DIR) / "compilation_presets.json"
# The builds: code/pyapp/compiled/windows/<preset> and .../linux/<preset> (ignored by Git).
OUTPUT = Path(paths.BACKEND_DIR) / "compiled"
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
    """Resolve command line > settings.json > preset into the build options."""
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


def _presets() -> Dict[str, Dict[str, object]]:
    """The presets (the project's presets.json, else the bundled one); an invalid entry becomes {}."""
    source = PRESETS if PRESETS.is_file() else DEFAULT_PRESETS
    return {name: value if isinstance(value, dict) else {} for name, value in _object(source).items()}


def _configured_preset() -> str:
    """The preset settings.json chooses (compile-app uses it without --preset)."""
    try:
        return str(_object(CONFIG).get("preset") or "standalone") if CONFIG.is_file() else "standalone"
    except SetupError:
        return "standalone"


def _console_text(variant: object) -> str:
    return "no console (GUI)" if variant == "no_terminal" else "console"


def _print_preset_table(presets: Dict[str, Dict[str, object]], current: str, numbered: bool = False) -> None:
    """One aligned line per preset: name, build type, console, use; the configured one is marked."""
    width = max((len(name) for name in presets), default=0)
    for number, (name, value) in enumerate(presets.items(), start=1):
        marker = styled("*", ANSI_GOOD) if name == current else " "
        build = "single .exe" if value.get("mode") == "onefile" else "folder"
        kind = f"{build}, {_console_text(value.get('variant'))}"
        prefix = f"{number:>3}  " if numbered else "  "
        print(
            f"{prefix}{marker} {styled(name.ljust(width), ANSI_BOLD)}  {kind:<28}  {styled(value.get('description', ''), ANSI_DIM)}"
        )


def cmd_compilation_presets(_arguments: List[str]) -> None:
    """Show the build presets (folder, single file, GUI) and which one is used."""
    print_heading("Compilation presets")
    current = _configured_preset()
    _print_preset_table(_presets(), current)
    print()
    print_info('* = used by compile-app ("preset" in settings.json). Other choices: compile-app --preset NAME.')
    source = PRESETS if PRESETS.is_file() else DEFAULT_PRESETS
    print_fields([("Settings", CONFIG), ("Presets", source), ("Output", OUTPUT)])


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
    """Check every Python file of the app for syntax errors, without running it."""
    print_heading("Validate app syntax")
    app = prepare()
    validate_sources(app.exe, app_sources(Path(paths.PYTHON_SCRIPTS_DIR)))


def output_folder(build: BuildOptions, platform: str = "windows", keep: bool = False) -> Path:
    """compiled/<platform>/<preset>; a changed mode or console is added to the name, so it never
    overwrites the preset's normal build. keep=True adds the date and time: a copy that stays."""
    definition = _presets().get(build.preset, {})
    name = build.preset
    if definition.get("mode", build.mode) != build.mode:
        name += "-" + build.mode
    if platform == "windows" and definition.get("variant", build.variant) != build.variant:
        name += "-" + build.variant
    if keep:
        name += "-" + time.strftime("%Y-%m-%d_%H-%M-%S")
    return OUTPUT / platform / name


def reserve_output(target: Path) -> None:
    """Mark OUTPUT as ours and empty the target folder, so no file of an older build remains."""
    if OUTPUT.exists() and not (OUTPUT / MARKER).is_file():
        raise SetupError(f"Refusing to reuse an unowned output folder: {OUTPUT}")
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / MARKER).write_text("PyApp compilation output\n", encoding="utf-8")
    if target.exists():
        if OUTPUT.resolve() not in target.resolve().parents:
            raise SetupError(f"Refusing to empty a folder outside the compilation output: {target}")
        shutil.rmtree(target)
    target.mkdir(parents=True)


def build_command(
    python: str, script: Path, mode: str, terminal: bool, extra: List[str], output: Optional[Path] = None
) -> List[str]:
    """Build the configured application directly; launcher supervision is not bundled."""
    if output is None:
        output = OUTPUT / "windows" / "build"
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


def _ask_preset() -> Optional[str]:
    """From the menu: choose a preset by number; Enter keeps the configured one, q cancels."""
    presets = _presets()
    current = _configured_preset()
    print_heading("Choose a build preset")
    _print_preset_table(presets, current, numbered=True)
    print()
    answer = ask(f"Number (Enter = {current}, q = cancel):").strip().lower()
    if answer in ("q", "n", "no", "cancel"):
        return None
    names = list(presets)
    if answer.isdecimal() and 1 <= int(answer) <= len(names):
        return names[int(answer) - 1]
    return answer or current


def cmd_compile_app(arguments: List[str]) -> None:
    """Build an .exe of the app with Nuitka, using a preset; --dry-run only shows the command."""
    parser = argparse.ArgumentParser(description=cmd_compile_app.__doc__)
    parser.add_argument("variant", nargs="?", choices=("terminal", "no_terminal"), default=None)
    parser.add_argument("--mode", choices=("standalone", "onefile"), default=None)
    parser.add_argument("--preset", help="preset in compilation/presets.json; overrides settings.json")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--keep", action="store_true", help="build into a new dated folder instead of replacing")
    parser.add_argument("--choose", action="store_true", help="ask for the preset (the dev menu passes this)")
    options = parser.parse_args(arguments)
    if options.choose and not options.preset:
        options.preset = _ask_preset()
        if options.preset is None:
            print_info("Nothing was built.")
            return
    build = load_options(options.preset, options.mode, options.variant)
    s = settings()
    if options.dry_run:
        validate(s)
        python = paths.VENV_PYTHON_EXE
    else:
        python = prepare(s).exe
    target = output_folder(build, keep=options.keep)
    command = build_command(
        python, Path(main_script_path(s)), build.mode, build.variant == "terminal", build.extra_args, target
    )
    print_heading("Compile app")
    print_fields(
        [
            ("Preset", build.preset),
            ("Build", "one folder (copy all of it)" if build.mode == "standalone" else "a single .exe file"),
            ("Console", _console_text(build.variant)),
            ("Main script", main_script_path(s)),
            ("Output", target),
            ("Replaces", "nothing (dated copy)" if options.keep else "the previous build of this preset"),
        ]
    )
    print(styled("  " + subprocess.list2cmdline(command), ANSI_DIM))
    print()
    if options.dry_run:
        return
    validate_sources(python, app_sources(Path(paths.PYTHON_SCRIPTS_DIR)))
    reserve_output(target)
    with temporary_compiler(python) as env:
        result = subprocess.run(  # noqa: S603 - configured compiler, no shell
            command, cwd=paths.PYTHON_SCRIPTS_DIR, env=env, check=False
        )
        if result.returncode:
            raise SetupError("Nuitka compilation failed; see the compiler output above.")
    print_success("Build completed.")
    executables = sorted(target.rglob("*.exe"))
    print_fields([("Folder", target), *(("Program", path) for path in executables[:3])])
    print_info("Test it on a PC without Python before sharing it.")


def cmd_clean_compilation(_arguments: List[str]) -> None:
    """Delete every build (code/pyapp/compiled); compiler caches are kept."""
    target = OUTPUT.resolve()
    parent = Path(paths.BACKEND_DIR).resolve()
    if target.parent != parent or target.name != "compiled" or OUTPUT.is_symlink():
        raise SetupError("Compilation output resolves outside code/pyapp/compiled.")
    if not target.exists():
        print_info("No compilation output to remove.")
        return
    if not (target / MARKER).is_file():
        raise SetupError(f"Refusing to delete unowned output: {target}")
    size = sum(path.stat().st_size for path in target.rglob("*") if path.is_file())
    shutil.rmtree(target)
    print_success(f"Removed the compilation output ({size / 1_000_000:.0f} MB): {target}")
