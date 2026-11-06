"""Dev tools for packages: add, remove, upgrade, sync, find imports, terminal, export."""

from __future__ import annotations

from backend.DONT_CHANGE import backend_settings as paths
from backend.DONT_CHANGE.scripts.config import display_path, settings
from backend.DONT_CHANGE.scripts.console_tools import (
    ANSI_DIM,
    ANSI_GOOD,
    ask,
    print_choices,
    print_heading,
    print_info,
    print_success,
    print_warn,
    styled,
)
from backend.DONT_CHANGE.scripts.dev.common import (
    COMMIT_HINT,
    ask_package_names,
    global_packages_mode,
    install_into_interpreter,
    normalized,
    prepare,
    requirement_name,
)
from backend.DONT_CHANGE.scripts.env.uv import run_uv
from backend.DONT_CHANGE.scripts.env.venv import (
    add_packages,
    ensure_lock,
    open_package_terminal,
    refuse_mutation_while_running,
    remove_packages,
    sync,
)


def cmd_add(arguments):
    """Add packages (recorded in developer_settings.py and uv.lock) and install them."""
    s = settings()
    names = arguments or ask_package_names("Package(s) to add, e.g. requests numpy>=2:")
    if not names:
        return
    prepare(s)
    if global_packages_mode(s):
        install_into_interpreter(s, names)
        return
    refuse_mutation_while_running()
    add_packages(names)
    print_success("Added: " + " ".join(names))
    print_info(COMMIT_HINT)


def cmd_remove(arguments):
    """Remove declared packages."""
    s = settings()
    if global_packages_mode(s):
        print_warn('Removing packages is only available for package_environment = "project_venv".')
        return
    names = list(arguments)
    if not names:
        declared = list(settings().packages)
        if not declared:
            print_info('"packages" in developer_settings.py is empty.')
            return
        print_heading("Declared packages")
        print_choices(declared)
        chosen = ask("Numbers or names to remove (space separated):").replace(",", " ").split()
        for item in chosen:
            if item.isdigit() and 1 <= int(item) <= len(declared):
                names.append(requirement_name(declared[int(item) - 1]))
            elif item:
                names.append(item)
    if not names:
        return
    prepare(s)
    refuse_mutation_while_running()
    remove_packages(names)
    print_success("Removed: " + " ".join(names))
    print_info(COMMIT_HINT)


def cmd_upgrade(arguments):
    """Upgrade all (or the named) packages within their declared limits."""
    s = settings()
    if global_packages_mode(s):
        install_into_interpreter(s, ["--upgrade", *(arguments or [])])
        return
    prepare(s)
    refuse_mutation_while_running()
    lock_arguments = ["lock"] + (
        [item for name in arguments for item in ("--upgrade-package", name)] if arguments else ["--upgrade"]
    )
    run_uv(lock_arguments)
    sync(paths.VENV_PYTHON_EXE, exact=True)
    print_success("Packages upgraded. Test the app, then commit backend/uv.lock.")


def cmd_sync(arguments):
    """Make the environment match uv.lock exactly (removes packages installed by hand)."""
    s = settings()
    if global_packages_mode(s):
        print_warn('Syncing is only available for package_environment = "project_venv".')
        return
    prepare(s)
    refuse_mutation_while_running()
    ensure_lock(s)
    sync(paths.VENV_PYTHON_EXE, exact=True)
    print_success("The environment matches uv.lock.")


def find_imports_and_add():
    """Show the imports found in the project, let the user review them, then add the chosen ones."""
    from backend.DONT_CHANGE.scripts.import_finder import find_requirements

    s = settings()
    requirements, problems = find_requirements()
    for problem in problems:
        print_warn("Could not parse " + problem)
    declared = {requirement_name(r) for r in s.packages}
    candidates = [r for r in requirements if normalized(r.distribution) not in declared]
    if not requirements:
        print_info("No third-party imports found.")
        return
    print_heading("Third-party imports")
    width = max(len(r.distribution) for r in requirements)
    for r in requirements:
        state = "declared" if normalized(r.distribution) in declared else r.source
        note = ", optional import" if r.optional else ""
        files = ", ".join(r.files[:3]) + (" ..." if len(r.files) > 3 else "")
        print(
            f"  {r.distribution:<{width}}  "
            + styled(f"import {', '.join(r.imports)}; {state}{note}; in {files}", ANSI_DIM)
        )
    if not candidates:
        print()
        print_success("Every imported package is already declared.")
        return
    selected = [not r.optional for r in candidates]
    print_heading("Packages to add")
    print_info(
        "installed = found in the environment, mapping = bundled list, guess = same as the import name (check it!)"
    )
    while True:
        print()
        print_choices(
            f"[{styled('x', ANSI_GOOD) if chosen else ' '}] {r.distribution}  "
            + styled(r.source + (", optional" if r.optional else ""), ANSI_DIM)
            for r, chosen in zip(candidates, selected)
        )
        answer = ask("Enter = add the checked ones, numbers = toggle (e.g. 2 5), n = cancel:").strip().lower()
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
    refuse_mutation_while_running()
    add_packages(names)
    print_success("Added: " + " ".join(names))
    print_info(COMMIT_HINT)


def cmd_find_imports(arguments):
    """Find the packages the code imports and add the missing ones after review."""
    prepare()
    find_imports_and_add()


def cmd_terminal(arguments):
    """Command prompt with the app environment activated and uv on PATH."""
    prepare()
    open_package_terminal()


def cmd_export(arguments):
    """Write backend/requirements.txt from uv.lock (for tools that need that format)."""
    prepare()
    run_uv(
        [
            "export",
            "--format",
            "requirements.txt",
            "--no-hashes",
            "--no-header",
            "--output-file",
            paths.EXPORTED_REQUIREMENTS_PATH,
            "--quiet",
        ]
    )
    print_success(f'Wrote "{display_path(paths.EXPORTED_REQUIREMENTS_PATH)}".')
