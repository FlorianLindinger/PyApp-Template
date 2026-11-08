"""Runs every launcher tool with one error, exit-code and acknowledgement policy.

bootstrap/run.bat starts `python -I -S -X utf8 entrypoint.py <tool.py> [arguments]`. The tool
is a plain module with a main() function; the optional module variables `fail_message` (text
with {e}) and `pause_on_success` (keep the window open after success) customize the policy.
"""

from __future__ import annotations

import os
import runpy
import sys
import traceback

if __name__ == "__main__":
    # -I leaves the script folder off sys.path; make "backend...." importable (the code folder).
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from backend.DONT_CHANGE.scripts.diagnostics import note_ignored
from backend.DONT_CHANGE.scripts.errors import LaunchCancelled, SettingsError, SetupError


def normalize_exit_code(value):
    """Convert a return or SystemExit value to a process code, printing nonnumeric errors."""
    if value is None:
        return 0
    if isinstance(value, int):
        return value
    print(value, file=sys.stderr)
    return 1


def acknowledge(message):
    """Wait for interactive acknowledgement unless an outer launcher owns the prompt."""
    # An outer launcher can own the final prompt and preserve native-crash output.
    if os.environ.get("PYAPP_ENTRYPOINT_NO_PAUSE") == "1":
        return
    if sys.stdin is not None and sys.stdin.isatty():
        try:
            input(message)
        except (EOFError, KeyboardInterrupt):
            pass


def run_file(path, arguments=()):
    """Load the tool, run its main() under the shared failure policy, with at most one prompt."""
    namespace = {}
    sys.argv = [str(path), *arguments]
    try:
        namespace = runpy.run_path(str(path), run_name="_pyapp_entry")
        main = namespace["main"]
        result = main()
        code = normalize_exit_code(result)
        # run_path returns a copy of the module globals; read the live ones, which main() may
        # have changed (e.g. "global pause_on_success").
        namespace = getattr(main, "__globals__", namespace)
        # A tool sets pause_on_success = True to keep its window open after success.
        pause_on_success = namespace.get("pause_on_success", False)
        if pause_on_success:
            acknowledge("Press Enter to close this window.")
        return code
    except SystemExit as error:
        return normalize_exit_code(error.code)
    except KeyboardInterrupt:
        print("\nStopped with Ctrl+C.", file=sys.stderr)
        return 130
    except Exception as error:
        if isinstance(error, LaunchCancelled):
            print("Launch cancelled.")
            return 0
        problem = expected_problem(error)
        if problem is not None:
            # Settings mistakes, missing downloads etc.: a clear message, no traceback.
            _show_console()
            print(file=sys.stderr)
            _print_error(problem)
            acknowledge("Press Enter to close this window.")
            return 1
        _show_console()
        description = namespace.get("fail_message", "Tool failed: {e}")
        print(file=sys.stderr)
        _print_error(description.format(e=error))
        traceback.print_exc()
        acknowledge("Press Enter to close this window.")
        return 1


def expected_problem(error):
    """Return a message for user-fixable errors (no traceback needed), else None."""
    if isinstance(error, (SettingsError, SetupError)):
        return str(error)
    return settings_file_problem(error)


SETTINGS_FILE_NAME = "developer_settings.py"


def settings_file_problem(error):
    """A short message if the error comes from running developer_settings.py itself, else None.

    Catches syntax errors and mistakes such as `Ture` (NameError) or `"a" + 1` (TypeError).
    """
    if isinstance(error, SyntaxError):
        filename = str(getattr(error, "filename", "") or "")
        if not filename.endswith(SETTINGS_FILE_NAME):
            return None
        return f'{SETTINGS_FILE_NAME} has a syntax error in line {error.lineno}: {error.msg}\n  "{filename}"'
    line = filename = None
    tb = error.__traceback__
    while tb is not None:
        if tb.tb_frame.f_code.co_filename.endswith(SETTINGS_FILE_NAME):
            filename, line = tb.tb_frame.f_code.co_filename, tb.tb_lineno
        tb = tb.tb_next
    if filename is None:
        return None
    hint = ""
    if isinstance(error, NameError):
        hint = "\n  Check the spelling: True, False and None start with a capital letter, and text needs quotes."
    return f'{SETTINGS_FILE_NAME} line {line}: {type(error).__name__}: {error}{hint}\n  "{filename}"'


def _print_error(message):
    try:
        from backend.DONT_CHANGE.scripts.console_tools import print_error

        print_error(message, file=sys.stderr)
    except Exception:
        print("ERROR  " + message, file=sys.stderr)


def _show_console():
    try:
        from backend.DONT_CHANGE.scripts.console_tools import show_console

        show_console()
    except Exception:
        note_ignored("_show_console")


if __name__ == "__main__":
    raise SystemExit(run_file(sys.argv[1], sys.argv[2:]))
