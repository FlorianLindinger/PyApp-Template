"""Developer tools for the uv-based app environment. Usage: main.py <command> [arguments]

The .cmd files in code/pyapp/dev_tools call this script with one command each; the commands
live in scripts/dev_tools/.
"""

from __future__ import annotations

from typing import List, Tuple

fail_message = "Dev tool failed: {e}"
pause_on_success = True

import sys

from pyapp.DONT_CHANGE.scripts.banner import print_banner
from pyapp.DONT_CHANGE.scripts.console_tools import (
    ANSI_DIM,
    ask,
    enable_ansi,
    print_choices,
    print_error,
    print_heading,
    styled,
    wait_for_enter,
)
from pyapp.DONT_CHANGE.scripts.dev_tools.housekeeping import cmd_clean, cmd_remove_shortcuts, cmd_status, cmd_test
from pyapp.DONT_CHANGE.scripts.dev_tools.packages import (
    cmd_add,
    cmd_export,
    cmd_find_imports,
    cmd_remove,
    cmd_sync,
    cmd_terminal,
    cmd_upgrade,
)
from pyapp.DONT_CHANGE.scripts.dev_tools.py_vers import cmd_change_python, cmd_update_python
from pyapp.DONT_CHANGE.scripts.dev_tools.self_contained import cmd_make_self_contained
from pyapp.DONT_CHANGE.scripts.entrypoint import expected_problem

# Commands that end on their own (a menu, a terminal); no "Press Enter" afterwards.
NO_PAUSE = {"menu", "tools", "terminal"}

COMMANDS = {
    "add": cmd_add,
    "remove": cmd_remove,
    "upgrade": cmd_upgrade,
    "sync": cmd_sync,
    "find-imports": cmd_find_imports,
    "terminal": cmd_terminal,
    "change-python": cmd_change_python,
    "update-python": cmd_update_python,
    "make-self-contained": cmd_make_self_contained,
    "export": cmd_export,
    "clean": cmd_clean,
    "remove-shortcuts": cmd_remove_shortcuts,
    "status": cmd_status,
    "test": cmd_test,
}


# Every command, in the order and groups of the menu.
MENU_GROUPS = (
    ("Packages", ("add", "remove", "upgrade", "sync", "find-imports", "terminal", "export")),
    ("Python", ("change-python", "update-python")),
    ("Project", ("status", "clean", "remove-shortcuts", "make-self-contained", "test")),
)
# The Tools shortcut's menu, for the people using the app rather than its developer:
# (command, what it does, what to know before using it). The other commands change what the
# developer recorded for everyone (packages they did not test, another Python), so they are left out.
USER_TOOLS = (
    ("status", "Check uv, Python and the packages", "Send this to the developer when the app does not start."),
    ("sync", "Repair the packages", "Reinstalls exactly the packages the app lists."),
    (
        "add",
        "Add packages for good",
        (
            "Recorded in code\\pyapp\\developer_settings.py of this copy. A new version of the app from its developer"
            " replaces that file: ask them to add it, if it should be in the app for everyone."
        ),
    ),
    (
        "terminal",
        "Package command prompt (advanced)",
        (
            '"uv pip install" there is only temporary: the next repair or update removes it.'
            ' To keep a package, use "uv add" there, or "Add packages" here.'
        ),
    ),
    (
        "make-self-contained",
        "Make this folder run on other PCs without internet",
        (
            "Copies uv, Python and the packages into this folder and changes settings in"
            " code\\pyapp\\developer_settings.py of this copy."
        ),
    ),
    ("clean", "Delete logs", "Only the app's own log files."),
    ("remove-shortcuts", "Remove the shortcuts", "In this folder, the Start Menu and on the Desktop."),
)
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
    groups = [
        (
            title,
            [
                (name, name.ljust(17) + styled((COMMANDS[name].__doc__ or "").strip().splitlines()[0], ANSI_DIM))
                for name in group
            ],
        )
        for title, group in MENU_GROUPS
    ]
    _run_menu(groups)


def cmd_tools(_arguments: List[str]) -> None:
    """The menu of the Tools shortcut (USER_TOOLS)."""
    lines = [(name, label + "\n       " + styled(note, ANSI_DIM)) for name, label, note in USER_TOOLS]
    _run_menu([("Tools", lines)])


def _run_menu(groups: List[Tuple[str, List[Tuple[str, str]]]]) -> None:
    """Numbered menu of (title, [(command, line)]) groups; runs the chosen command until Enter."""
    names = [name for _, group in groups for name, _ in group]
    while True:
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
        if not (answer.isdigit() and 1 <= int(answer) <= len(names)):
            print_error(f"Please enter a number from 1 to {len(names)}.")
            continue
        try:
            run_command(names[int(answer) - 1], [])
        except Exception as error:
            problem = expected_problem(error)
            if problem is None:
                raise
            print_error(problem)
        # The menu would otherwise push the result out of sight.
        print()
        wait_for_enter("Press Enter to return to the menu.")


def main() -> None:
    global pause_on_success
    enable_ansi()
    print_banner()
    if sys.argv[1:2] == ["dev"]:  # DONT_CHANGE\\run.bat passes its own first word on
        del sys.argv[1]
    command = sys.argv[1] if len(sys.argv) > 1 else "menu"
    if command in NO_PAUSE:
        pause_on_success = False
    if command == "menu":
        return cmd_menu(sys.argv[2:])
    if command == "tools":
        return cmd_tools(sys.argv[2:])
    if command not in COMMANDS:
        raise SystemExit("Unknown command. Use one of: menu, " + ", ".join(COMMANDS))
    return run_command(command, sys.argv[2:])
