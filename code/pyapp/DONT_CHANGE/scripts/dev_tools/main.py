"""Developer tools for the uv-based app environment. Usage: main.py <command> [arguments]

The .cmd files in code/pyapp/dev_tools call this script with one command each; the commands
live in scripts/dev_tools/.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Sequence, Tuple

fail_message = "Dev tool failed: {e}"
pause_on_success = True

import sys

from pyapp.DONT_CHANGE.scripts.banner import print_banner
from pyapp.DONT_CHANGE.scripts.console_tools import (
    ANSI_DIM,
    ANSI_HEADING,
    ask,
    enable_ansi,
    print_choices,
    print_error,
    print_heading,
    styled,
    wait_for_enter,
)
from pyapp.DONT_CHANGE.scripts.dev_tools.app_tests import cmd_run_tests
from pyapp.DONT_CHANGE.scripts.dev_tools.compilation import (
    cmd_clean_compilation,
    cmd_compilation_presets,
    cmd_compile_app,
    cmd_validate_syntax,
)
from pyapp.DONT_CHANGE.scripts.dev_tools.housekeeping import cmd_clean, cmd_remove_shortcuts, cmd_status, cmd_test
from pyapp.DONT_CHANGE.scripts.dev_tools.linux_compilation import cmd_compile_linux, cmd_setup_linux
from pyapp.DONT_CHANGE.scripts.dev_tools.package_list import cmd_list_packages
from pyapp.DONT_CHANGE.scripts.dev_tools.packages import (
    cmd_add,
    cmd_clear_packages,
    cmd_export,
    cmd_find_imports,
    cmd_install_requirements,
    cmd_remove,
    cmd_reset_imports,
    cmd_sync,
    cmd_terminal,
    cmd_upgrade,
)
from pyapp.DONT_CHANGE.scripts.dev_tools.py_vers import cmd_change_python, cmd_update_python
from pyapp.DONT_CHANGE.scripts.dev_tools.self_contained import cmd_make_self_contained
from pyapp.DONT_CHANGE.scripts.entrypoint import expected_problem

# Commands that end on their own (a menu, a terminal); no "Press Enter" afterwards.
NO_PAUSE = {"menu", "terminal", "compilation"}


def cmd_compilation_menu(_arguments: List[str]) -> None:
    """Build a standalone .exe (or a Linux version) of the app: presets, build, clean up."""
    from pyapp.DONT_CHANGE.scripts.dev_tools.compilation import FOLDER

    _command_menu(
        SUBMENU_GROUPS["compilation"],
        zero=("compilation/", "Open the folder with the build settings (settings.json, presets.json)", FOLDER),
    )


COMMANDS = {
    "compilation": cmd_compilation_menu,
    "compilation-presets": cmd_compilation_presets,
    "compile-app": cmd_compile_app,
    "compile-linux": cmd_compile_linux,
    "setup-linux": cmd_setup_linux,
    "validate-syntax": cmd_validate_syntax,
    "clean-compilation": cmd_clean_compilation,
    "list-packages": cmd_list_packages,
    "add": cmd_add,
    "remove": cmd_remove,
    "clear-packages": cmd_clear_packages,
    "upgrade": cmd_upgrade,
    "sync": cmd_sync,
    "find-imports": cmd_find_imports,
    "reset-imports": cmd_reset_imports,
    "install-requirements": cmd_install_requirements,
    "terminal": cmd_terminal,
    "change-python": cmd_change_python,
    "update-python": cmd_update_python,
    "make-self-contained": cmd_make_self_contained,
    "export": cmd_export,
    "clean": cmd_clean,
    "remove-shortcuts": cmd_remove_shortcuts,
    "status": cmd_status,
    "run-tests": cmd_run_tests,
    "test": cmd_test,
}


# Every command, in the order and groups of the menu.
MENU_GROUPS = (
    (
        "Packages",
        (
            "list-packages",
            "add",
            "remove",
            "clear-packages",
            "upgrade",
            "sync",
            "find-imports",
            "reset-imports",
            "install-requirements",
            "terminal",
            "export",
        ),
    ),
    ("Python", ("change-python", "update-python")),
    ("Compilation", ("compilation",)),
    ("Project", ("run-tests", "status", "clean", "remove-shortcuts", "make-self-contained", "test")),
)
SUBMENU_GROUPS = {
    "compilation": (
        ("Windows build (Nuitka)", ("compilation-presets", "validate-syntax", "compile-app", "clean-compilation")),
        ("Linux build (in WSL)", ("setup-linux", "compile-linux")),
    ),
}
# Arguments a command gets when it is chosen in the menu (on the command line it gets none).
MENU_ARGUMENTS = {"compile-app": ["--choose"]}
# For the commands that do not start with a heading of their own.
HEADINGS = {
    "add": "Add packages",
    "remove": "Remove packages",
    "upgrade": "Upgrade packages",
    "sync": "Sync packages",
    "export": "Export requirements",
    "update-python": "Update Python",
    "remove-shortcuts": "Remove shortcuts",
}


def run_command(name: str, arguments: List[str]) -> None:
    if name in HEADINGS:
        print_heading(HEADINGS[name])
    return COMMANDS[name](arguments)


def cmd_menu(_arguments: List[str]) -> None:
    """Interactive menu of all commands."""
    from pyapp.DONT_CHANGE import backend_settings as paths

    _command_menu(
        MENU_GROUPS,
        zero=(
            "developer_settings.py",
            "Open the app's settings: name, Python, packages, logs, windows, shortcuts",
            Path(paths.DEV_SETTINGS_PATH),
        ),
    )


# (label, description, file or folder): entry 0 of a menu, opened in the editor or Explorer.
ZeroEntry = Tuple[str, str, Path]


def _command_menu(definitions: Sequence[Tuple[str, Sequence[str]]], zero: Optional[ZeroEntry] = None) -> None:
    """Use the same presentation for the main developer menu and its subgroups."""
    groups = [
        (
            title,
            [
                (name, name.ljust(22) + styled((COMMANDS[name].__doc__ or "").strip().splitlines()[0], ANSI_DIM))
                for name in group
            ],
        )
        for title, group in definitions
    ]
    _run_menu(groups, zero)


def _open_zero_entry(entry: ZeroEntry) -> None:
    """Open entry 0: a file in VS Code (else Notepad), a folder in Explorer."""
    import os

    from pyapp.DONT_CHANGE.scripts.console_tools import open_in_editor, print_info

    path = entry[2]
    if path.is_dir():
        os.startfile(str(path))  # noqa: S606 - a folder of this project, opened in Explorer
    else:
        open_in_editor(str(path))
    print_info(f"Opened {path}")


def _run_menu(groups: List[Tuple[str, List[Tuple[str, str]]]], zero: Optional[ZeroEntry] = None) -> None:
    """Numbered menu of (title, [(command, line)]) groups; runs the chosen command until Enter.

    ``zero``, if given, is shown first as entry 0 and opens a settings file or folder.
    """
    names = [name for _, group in groups for name, _ in group]
    while True:
        if zero is not None:
            print_heading("Settings")
            print(f"  {styled(' 0', ANSI_HEADING)}  {zero[0].ljust(22)}{styled(zero[1], ANSI_DIM)}")
        number = 1
        for title, group in groups:
            print_heading(title)
            print_choices((line for _, line in group), start=number)
            number += len(group)
        print()
        try:
            answer = ask("Number (Enter = quit):").strip()
        except EOFError:  # no more input: the same as pressing Enter
            return
        if not answer:
            return
        if zero is not None and answer == "0":
            try:
                _open_zero_entry(zero)
            except OSError as error:
                print_error(f"Could not open {zero[2]}: {error}")
            continue
        lowest = 0 if zero is not None else 1
        if not (answer.isdecimal() and 1 <= int(answer) <= len(names)):
            print_error(f"Please enter a number from {lowest} to {len(names)}.")
            continue
        try:
            selected = names[int(answer) - 1]
            run_command(selected, list(MENU_ARGUMENTS.get(selected, [])))
            if selected in SUBMENU_GROUPS:
                continue
        except Exception as error:
            problem = expected_problem(error)
            if problem is None:
                raise
            print_error(problem)
        # The menu would otherwise push the result out of sight.
        print()
        wait_for_enter("Press Enter to return to the menu.")


def _set_window_title_and_icon(command: str) -> None:
    """Give the window the app's icon and a title that says what it is, e.g. "My App - Developer Tools"."""
    from pyapp.DONT_CHANGE import backend_settings as paths
    from pyapp.DONT_CHANGE.scripts.console_tools import set_terminal_icon, set_terminal_title

    try:
        from pyapp.DONT_CHANGE.scripts.config import settings

        name = settings().program_name
    except Exception:
        name = "PyApp"  # a broken settings file is reported by the tool itself, right after this
    purpose = {"menu": "Developer Tools", "compilation": "Compilation Tools"}.get(command, command)
    set_terminal_title(f"{name} - {purpose}")
    set_terminal_icon(paths.ICON_PATH)


def main() -> None:
    global pause_on_success
    enable_ansi()
    print_banner()
    if sys.argv[1:2] == ["dev"]:  # DONT_CHANGE\\B\\run.bat passes its own first word on
        del sys.argv[1]
    command = sys.argv[1] if len(sys.argv) > 1 else "menu"
    if command == "menu" and len(sys.argv) > 2:
        # "Open Developer Tools Menu.cmd add requests": run that command instead of showing the menu.
        del sys.argv[1]
        command = sys.argv[1]
    _set_window_title_and_icon(command)
    if command in NO_PAUSE:
        pause_on_success = False
    if command == "menu":
        return cmd_menu(sys.argv[2:])
    if command not in COMMANDS:
        raise SystemExit("Unknown command. Use one of: menu, " + ", ".join(COMMANDS))
    return run_command(command, sys.argv[2:])
