# ruff: noqa: E402
# The early __main__ handoff lets the shared runner report import failures once.

"""Developer tools for the uv-based app environment. Usage: dev_tools.py <command> [arguments]

The .cmd files in code/backend/dev_tools call this script with one command each.
"""

from __future__ import annotations

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

fail_message = "[Error] Dev tool failed: {e}"
pause_on_success = True

import os
import re
import shutil
import sys
import tempfile
import types

from backend.DONT_CHANGE.scripts import uv_env
from backend.DONT_CHANGE.scripts.config import (
    _version_problem,
    describe_python_request,
    display_path,
    edit_settings,
    settings,
    validate,
)
from backend.DONT_CHANGE.scripts.console_tools import enable_ansi, input_warn, print_success, print_warn
from backend.DONT_CHANGE import backend_settings as paths

# ---------------------------------------------------------------- helpers


def ask(question: str) -> bool:
    return input_warn(question + " [y/N] ").strip().lower() in ("y", "yes", "j", "ja")


def normalized(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def requirement_name(requirement: str) -> str:
    match = re.match(r"\s*([A-Za-z0-9][A-Za-z0-9._-]*)", requirement)
    return normalized(match.group(1)) if match else normalized(requirement)


def global_packages_mode(s) -> bool:
    return s.package_environment == "interpreter_site_packages"


def prepare(s=None):
    """Validate settings and make sure the environment exists before changing it."""
    s = s or settings()
    validate(s)
    return uv_env.ensure_environment(interactive=True, purpose="tool")


def install_into_interpreter(s, names) -> None:
    """package_environment = "interpreter_site_packages": install only when explicitly allowed."""
    python = uv_env.app_python_for_tools()
    if not s.allow_installing_into_global_python:
        print_warn("The app uses the selected interpreter's own packages; this tool does not change them.")
        print(f'Install them yourself:  "{python}" -m pip install {" ".join(names)}')
        print("(or set allow_installing_into_global_python = True in developer_settings.py)")
        return
    uv_env.install_without_recording(names, python)


def ask_package_names(prompt: str) -> list:
    return input_warn(prompt).replace(",", " ").split()


# ---------------------------------------------------------------- package commands


def cmd_add(arguments):
    """Add packages to pyproject.toml/uv.lock and install them."""
    s = settings()
    names = arguments or ask_package_names("Package(s) to add, e.g. requests numpy>=2: ")
    if not names:
        return
    prepare(s)
    if global_packages_mode(s):
        install_into_interpreter(s, names)
        return
    uv_env.refuse_mutation_while_running()
    uv_env.add_packages(names)
    print_success("[Success] Added: " + " ".join(names) + ". Commit pyproject.toml and uv.lock.")


def cmd_remove(arguments):
    """Remove declared packages."""
    s = settings()
    if global_packages_mode(s):
        print_warn("Removing packages is only available for package_environment = \"project_venv\".")
        return
    names = list(arguments)
    if not names:
        declared = uv_env.declared_dependencies()
        if not declared:
            print("[Info] No packages are declared in pyproject.toml.")
            return
        for index, requirement in enumerate(declared, 1):
            print(f"  {index}: {requirement}")
        chosen = input_warn("Numbers or names to remove (space separated): ").replace(",", " ").split()
        for item in chosen:
            if item.isdigit() and 1 <= int(item) <= len(declared):
                names.append(requirement_name(declared[int(item) - 1]))
            elif item:
                names.append(item)
    if not names:
        return
    prepare(s)
    uv_env.refuse_mutation_while_running()
    uv_env.remove_packages(names)
    print_success("[Success] Removed: " + " ".join(names) + ". Commit pyproject.toml and uv.lock.")


def cmd_upgrade(arguments):
    """Upgrade all (or the named) packages within their declared limits."""
    s = settings()
    if global_packages_mode(s):
        install_into_interpreter(s, ["--upgrade", *(arguments or [])])
        return
    prepare(s)
    uv_env.refuse_mutation_while_running()
    lock_arguments = ["lock"] + ([item for name in arguments for item in ("--upgrade-package", name)] if arguments else ["--upgrade"])
    uv_env.run_uv(lock_arguments)
    uv_env.sync(paths.VENV_PYTHON_EXE, exact=True)
    print_success("[Success] Packages upgraded. Test the app, then commit uv.lock.")


def cmd_sync(arguments):
    """Make the environment match uv.lock exactly (removes packages installed by hand)."""
    s = settings()
    if global_packages_mode(s):
        print_warn("Syncing is only available for package_environment = \"project_venv\".")
        return
    prepare(s)
    uv_env.refuse_mutation_while_running()
    uv_env.ensure_lock(s)
    uv_env.sync(paths.VENV_PYTHON_EXE, exact=True)
    print_success("[Success] The environment matches uv.lock.")


def find_imports_and_add():
    """Show the imports found in the project, let the user review them, then add the chosen ones."""
    from backend.DONT_CHANGE.scripts.import_finder import find_requirements

    s = settings()
    requirements, problems = find_requirements()
    for problem in problems:
        print_warn("[Warning] Could not parse " + problem)
    declared = {requirement_name(r) for r in uv_env.declared_dependencies()}
    candidates = [r for r in requirements if normalized(r.distribution) not in declared]
    if requirements:
        print("Imported third-party packages:")
        for r in requirements:
            state = "declared" if normalized(r.distribution) in declared else r.source
            note = ", optional import" if r.optional else ""
            print(f"  - {r.distribution}  (import {', '.join(r.imports)}; {state}{note}; in {', '.join(r.files[:3])}{' ...' if len(r.files) > 3 else ''})")
    if not candidates:
        print_success("[Success] Every imported package is already declared." if requirements else "[Info] No third-party imports found.")
        return
    selected = [not r.optional for r in candidates]
    print()
    print('Sources: "installed" = found in the environment, "mapping" = bundled list, "guess" = same as the import name (check it!).')
    while True:
        print("Packages to add:")
        for index, (r, chosen) in enumerate(zip(candidates, selected), 1):
            print(f"  [{'x' if chosen else ' '}] {index}: {r.distribution}  ({r.source}{', optional' if r.optional else ''})")
        answer = input_warn("Enter = add the checked ones, numbers = toggle (e.g. 2 5), n = cancel: ").strip().lower()
        if answer in ("n", "no", "q"):
            return
        if not answer:
            break
        for item in answer.replace(",", " ").split():
            if item.isdigit() and 1 <= int(item) <= len(candidates):
                selected[int(item) - 1] = not selected[int(item) - 1]
    names = [r.distribution for r, chosen in zip(candidates, selected) if chosen]
    if not names:
        return
    if global_packages_mode(s):
        install_into_interpreter(s, names)
        return
    uv_env.refuse_mutation_while_running()
    uv_env.add_packages(names)
    print_success("[Success] Added: " + " ".join(names) + ". Commit pyproject.toml and uv.lock.")


def cmd_find_imports(arguments):
    """Find the packages the code imports and add the missing ones after review."""
    prepare()
    find_imports_and_add()


def cmd_terminal(arguments):
    """Command prompt with the app environment activated and uv on PATH."""
    global pause_on_success
    prepare()
    pause_on_success = False
    uv_env.open_package_terminal()


def cmd_export(arguments):
    """Write code/requirements.txt from uv.lock (for tools that need that format)."""
    prepare()
    uv_env.run_uv(["export", "--format", "requirements.txt", "--no-hashes", "--no-header", "--output-file", paths.EXPORTED_REQUIREMENTS_PATH, "--quiet"])
    print_success(f'[Success] Wrote "{display_path(paths.EXPORTED_REQUIREMENTS_PATH)}".')


# ---------------------------------------------------------------- Python commands


def cmd_change_python(arguments):
    """Set a new python_version and migrate the project to it."""
    s = settings()
    current = uv_env.read_python_version_file()
    print(f"Current project Python: {current or '(not set up yet)'}; python_version setting: {describe_python_request(s.python_version)}")
    print(uv_env.available_summary(s))
    new = arguments[0] if arguments else input_warn('New python_version (e.g. "3.13", "3.14t", empty = newest stable): ').strip().strip('"')
    problem = _version_problem(new)
    if problem:
        raise uv_env.SettingsError(problem)
    for line in edit_settings({"python_version": new}):
        print(line)
    if not new:
        print("[Info] python_version is now empty (newest stable, chosen once). Use update_python to move to a newer Python.")
        return
    prepare()  # offers the migration menu because the setting now differs from code/.python-version


def cmd_update_python(arguments):
    """Newest patch release of the project's Python; with python_version = "" also a newer minor version."""
    s = settings()
    prepare(s)
    current = uv_env.read_python_version_file()
    if not s.python_version:
        newest = uv_env.newest_stable_minor(s)
        if current and newest != current and uv_env._version_key(newest) > uv_env._version_key(current):
            if ask(f"Python {newest} is available (the project uses {current}). Switch now?"):
                uv_env.switch_python(newest, s=s)
                return
    request = current or s.python_version
    in_use = uv_env.find_python(request, s) or ""
    if s.python_source.startswith("system") and not os.path.normcase(in_use).startswith(os.path.normcase(paths.LOCAL_PYTHONS_DIR)):
        print("[Info] The project uses an installed system Python; update it with its own installer.")
        return
    print(f"[Setup] Updating Python {request} to its newest patch release...")
    uv_env.run_uv(["python", "install", "--upgrade", request], cwd=tempfile.gettempdir())
    newest_exe = uv_env.find_python(request, s)
    in_use = os.path.join(uv_env.read_venv_config().get("home", ""), "python.exe")
    current_version = uv_env.interpreter_version(in_use) if os.path.isfile(in_use) else None
    if newest_exe and current_version != uv_env.interpreter_version(newest_exe):
        uv_env.refuse_mutation_while_running()
        uv_env.build_venv(newest_exe, locked=True, s=s)
    uv_env.invalidate_runtime_cache()
    print_success(f"[Success] Python {uv_env.version_text(uv_env.interpreter_version(newest_exe or sys.executable))} is ready.")


# ---------------------------------------------------------------- portability


def _settings_copy(s, **overrides):
    values = {name: getattr(s, name) for name in dir(s) if not name.startswith("_")}
    values.update(overrides)
    return types.SimpleNamespace(**values)


def cmd_make_portable(arguments):
    """Put uv, Python and all packages inside this folder so it runs offline on other PCs."""
    s = settings()
    prepare(s)
    uv_env.refuse_mutation_while_running()
    local = _settings_copy(s, python_source="local", package_environment="project_venv")

    # 1. uv
    current_uv = uv_env.uv_exe()
    if os.path.normcase(os.path.dirname(os.path.abspath(current_uv))) != os.path.normcase(paths.LOCAL_UV_DIR):
        staging = paths.LOCAL_UV_DIR + ".staging"
        shutil.rmtree(staging, ignore_errors=True)
        os.makedirs(staging)
        for name in ("uv.exe", "uvx.exe", "uvw.exe"):
            source = os.path.join(os.path.dirname(current_uv), name)
            if os.path.isfile(source):
                shutil.copy2(source, staging)
        if os.path.isdir(paths.LOCAL_UV_DIR):
            shutil.rmtree(paths.LOCAL_UV_DIR)
        os.rename(staging, paths.LOCAL_UV_DIR)
        print(f"[Setup] Copied uv {uv_env.uv_version()} into {display_path(paths.LOCAL_UV_DIR)}")
    os.environ["PYAPP_UV"] = paths.LOCAL_UV_EXE

    # 2. Python
    request = uv_env.read_python_version_file() or s.python_version or uv_env.newest_stable_minor(local)
    python = uv_env.find_python(request, local) or uv_env.install_python(request, local)
    if not os.path.normcase(os.path.abspath(python)).startswith(os.path.normcase(paths.LOCAL_PYTHONS_DIR)):
        raise uv_env.SetupError(f"uv did not install Python {request} into {paths.LOCAL_PYTHONS_DIR}.")
    print(f"[Setup] Local Python: {display_path(python)}")

    # 3. packages
    if uv_env.read_python_version_file() is None:
        uv_env.write_python_version_file(request)
    uv_env.set_requires_python(uv_env.interpreter_version(python))
    uv_env.ensure_lock(local)
    home = uv_env.read_venv_config().get("home", "")
    if not os.path.normcase(home).startswith(os.path.normcase(paths.LOCAL_PYTHONS_DIR)):
        uv_env.build_venv(python, locked=True, s=local)
    else:
        uv_env.sync(paths.VENV_PYTHON_EXE, exact=True, s=local)
    uv_env.invalidate_runtime_cache()

    # 4. settings
    wanted = {"uv_prefer": "local", "uv_install_if_missing": "local", "python_source": "local", "package_environment": "project_venv"}
    changes = {name: value for name, value in wanted.items() if getattr(s, name) != value}
    print()
    print_success("[Success] uv, Python and all packages are now inside this folder.")
    if changes:
        print("To actually use them, developer_settings.py needs:")
        for name, value in changes.items():
            print(f'  {name} = "{value}"   (now "{getattr(s, name)}")')
        if ask("Apply these changes now?"):
            for line in edit_settings(changes):
                print(line)
    else:
        print("developer_settings.py already uses the local uv, Python and packages.")
    print()
    print("Optional for strictly offline use: allow_downloads_at_launch = False (launches never try the network).")
    print("Copy the whole project folder. After moving it, run 'Setup - run first and after moving folder.cmd'")
    print("to refresh the shortcuts; the environment adapts to the new location automatically.")


# ---------------------------------------------------------------- housekeeping


def cmd_clean(arguments):
    """Delete logs or run diagnostics."""
    from backend.DONT_CHANGE.scripts.filesystem_tools import remove_tree_inside
    from backend.DONT_CHANGE.scripts.launcher_ui import get_log_folder_path

    s = settings()
    log_folder = get_log_folder_path(s.log_path, s.log_path_is_relative_to_start_folder_if_relative)
    crash_folder = get_log_folder_path(s.crash_log_path, s.crash_log_path_is_relative_to_start_folder_if_relative)
    options = [
        ("logs", f"Delete all files in the log folder ({display_path(log_folder) if log_folder else 'disabled'})"),
        ("crash", f"Delete all files in the crash log folder ({display_path(crash_folder) if crash_folder else 'disabled'})"),
        ("runs", "Delete per-run diagnostics (temporary\\runs)"),
    ]
    for index, (_, label) in enumerate(options, 1):
        print(f"  {index}: {label}")
    chosen = input_warn("Numbers to clean (space separated), Enter = cancel: ").replace(",", " ").split()
    keys = {options[int(c) - 1][0] for c in chosen if c.isdigit() and 1 <= int(c) <= len(options)}
    if not keys or not ask("Delete permanently?"):
        return
    for key, folder in (("logs", log_folder), ("crash", crash_folder)):
        if key in keys and folder and os.path.isdir(folder):
            for name in os.listdir(folder):
                path = os.path.join(folder, name)
                if os.path.isfile(path) and name != ".gitkeep":
                    os.remove(path)
    if "runs" in keys and os.path.isdir(paths.RUNS_DIR):
        remove_tree_inside(paths.RUNS_DIR, paths.TEMPORARY_DIR)
    print_success("[Success] Cleaned.")


def cmd_remove_shortcuts(arguments):
    """Remove every shortcut Setup created (project folder, Start Menu, Desktop)."""
    from backend.DONT_CHANGE.scripts.setup.generate_shortcuts import read_created_shortcuts, remove_shortcuts, write_created_shortcuts

    removed = remove_shortcuts(read_created_shortcuts())
    write_created_shortcuts([])
    for path in removed:
        print("[Info] Removed: " + path)
    print_success(f"[Success] Removed {len(removed)} shortcut(s). Run Setup to create them again.")


def cmd_status(arguments):
    """Show uv, Python, environment and shortcut state."""
    s = settings()
    try:
        validate(s)
        settings_state = "valid"
    except Exception as error:
        settings_state = str(error)
    uv = uv_env.uv_exe()
    config = uv_env.read_venv_config()
    lines = [
        ("Program", s.program_name),
        ("Settings", settings_state),
        ("python_version", describe_python_request(s.python_version)),
        ("python_source", s.python_source),
        ("package_environment", s.package_environment),
        ("uv", f"{uv_env.uv_version()} at {uv}" + (" (local)" if os.path.normcase(uv).startswith(os.path.normcase(paths.LOCAL_UV_DIR)) else " (global)")),
        ("Launcher Python", f"{uv_env.version_text(sys.version_info[:3])} at {sys.executable}"),
        ("code/.python-version", uv_env.read_python_version_file() or "(missing)"),
        ("requires-python", uv_env.current_requires_python() or "(missing)"),
        ("Declared packages", ", ".join(uv_env.declared_dependencies()) or "(none)"),
        ("Environment", display_path(paths.VENV_DIR) if config else "(not created)"),
    ]
    if config:
        lines += [
            ("  Python", uv_env.version_text(uv_env.venv_version(config) or ())),
            ("  base", config.get("home", "?") + ("" if uv_env.venv_home_valid(config) else "  (MISSING - repaired on next start)")),
            ("  relocatable", config.get("relocatable", "false")),
        ]
    if os.path.isfile(paths.UV_LOCK_PATH):
        code = 0 if uv_env._quiet_attempt(["lock", "--check", "--offline"]) else 1
        lines.append(("uv.lock", "up to date" if code == 0 else "needs an update (next start or sync)"))
    else:
        lines.append(("uv.lock", "(missing - created on next start)"))
    try:
        from backend.DONT_CHANGE.scripts.setup.generate_shortcuts import read_created_shortcuts

        lines.append(("Shortcuts", f"{len(read_created_shortcuts())} created by Setup"))
    except Exception:
        pass
    lines.append(("Downloads at launch", "allowed" if s.allow_downloads_at_launch else "disabled"))
    width = max(len(label) for label, _ in lines)
    for label, value in lines:
        print(f"{label.ljust(width)} : {value}")


COMMANDS = {
    "add": cmd_add,
    "remove": cmd_remove,
    "upgrade": cmd_upgrade,
    "sync": cmd_sync,
    "find-imports": cmd_find_imports,
    "terminal": cmd_terminal,
    "change-python": cmd_change_python,
    "update-python": cmd_update_python,
    "make-portable": cmd_make_portable,
    "export": cmd_export,
    "clean": cmd_clean,
    "remove-shortcuts": cmd_remove_shortcuts,
    "status": cmd_status,
}


def cmd_menu(arguments):
    """Interactive menu of all commands."""
    names = list(COMMANDS)
    while True:
        print()
        print("Dev tools:")
        for index, name in enumerate(names, 1):
            doc = (COMMANDS[name].__doc__ or "").strip().splitlines()[0]
            print(f"  {index:2}: {name.ljust(17)} {doc}")
        answer = input_warn("Choose a number (Enter = quit): ").strip()
        if not answer:
            return
        if answer.isdigit() and 1 <= int(answer) <= len(names):
            try:
                COMMANDS[names[int(answer) - 1]]([])
            except Exception as error:
                problem = __import__("backend.DONT_CHANGE.scripts.entrypoint", fromlist=["x"]).expected_problem(error)
                if problem is None:
                    raise
                print_warn("[Error] " + problem)


def main():
    global pause_on_success
    enable_ansi()
    command = sys.argv[1] if len(sys.argv) > 1 else "menu"
    if command == "menu":
        pause_on_success = False
        return cmd_menu(sys.argv[2:])
    if command not in COMMANDS:
        raise SystemExit("Unknown command. Use one of: menu, " + ", ".join(COMMANDS))
    return COMMANDS[command](sys.argv[2:])
