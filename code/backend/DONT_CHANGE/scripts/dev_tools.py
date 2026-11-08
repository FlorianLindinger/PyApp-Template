"""Developer tools for the uv-based app environment. Usage: dev_tools.py <command> [arguments]

The .cmd files in code/backend/dev_tools call this script with one command each; the commands
live in scripts/dev/.
"""

from __future__ import annotations

fail_message = "Dev tool failed: {e}"
pause_on_success = True

import sys

from backend.DONT_CHANGE.scripts.banner import print_banner
from backend.DONT_CHANGE.scripts.console_tools import (
    ANSI_DIM,
    ask,
    enable_ansi,
    print_choices,
    print_error,
    print_heading,
    styled,
)
from backend.DONT_CHANGE.scripts.dev.housekeeping import cmd_clean, cmd_remove_shortcuts, cmd_status, cmd_test
from backend.DONT_CHANGE.scripts.dev.packages import (
    cmd_add,
    cmd_export,
    cmd_find_imports,
    cmd_remove,
    cmd_sync,
    cmd_terminal,
    cmd_upgrade,
)
from backend.DONT_CHANGE.scripts.dev.portable import cmd_make_portable
from backend.DONT_CHANGE.scripts.dev.py_vers import cmd_change_python, cmd_update_python
from backend.DONT_CHANGE.scripts.entrypoint import expected_problem

# Commands that end on their own (a menu, a terminal); no "Press Enter" afterwards.
NO_PAUSE = {"menu", "terminal"}

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
    "test": cmd_test,
}


def cmd_menu(arguments: list[str]):
    """Interactive menu of all commands."""
    names = list(COMMANDS)
    while True:
        print_heading("Dev tools")
        print_choices(
            name.ljust(17) + styled((COMMANDS[name].__doc__ or "").strip().splitlines()[0], ANSI_DIM) for name in names
        )
        answer = ask("Number (Enter = quit):").strip()
        if not answer:
            return
        if answer.isdigit() and 1 <= int(answer) <= len(names):
            try:
                COMMANDS[names[int(answer) - 1]]([])
            except Exception as error:
                problem = expected_problem(error)
                if problem is None:
                    raise
                print_error(problem)


def main():
    global pause_on_success
    enable_ansi()
    print_banner()
    command = sys.argv[1] if len(sys.argv) > 1 else "menu"
    if command in NO_PAUSE:
        pause_on_success = False
    if command == "menu":
        return cmd_menu(sys.argv[2:])
    if command not in COMMANDS:
        raise SystemExit("Unknown command. Use one of: menu, " + ", ".join(COMMANDS))
    return COMMANDS[command](sys.argv[2:])
