"""One error, exit-code and acknowledgement policy for developer/shortcut tools."""

from __future__ import annotations

import os
import runpy
import sys
import traceback


def normalize_exit_code(value):
    """Convert a return or SystemExit value to a process code, printing nonnumeric errors."""
    if value is None:
        return 0
    if isinstance(value, int):
        return value
    print(value, file=sys.stderr)
    return 1


def acknowledge(message):
    # An outer launcher can own the final prompt and preserve native-crash output.
    """Wait for interactive acknowledgement unless an outer launcher owns the prompt."""
    if os.environ.get("PYAPP_ENTRYPOINT_NO_PAUSE") == "1":
        return
    if sys.stdin is not None and sys.stdin.isatty():
        try:
            input(message)
        except (EOFError, KeyboardInterrupt):
            pass


def run_file(path):
    """Load imports and run main under the same failure policy, with one prompt."""
    namespace = {}
    try:
        namespace = runpy.run_path(str(path), run_name="_pyapp_entry")
        result = namespace["main"]()
        code = normalize_exit_code(result)
        pause_on_success = namespace.get(
            "pause_on_success",
            "close_terminal_on_finish" in namespace
            and not namespace["close_terminal_on_finish"],
        )
        if pause_on_success:
            acknowledge("Press Enter to exit")
        return code
    except SystemExit as error:
        return normalize_exit_code(error.code)
    except KeyboardInterrupt:
        print("\n[Info] Interrupted by Ctrl+C", file=sys.stderr)
        return 130
    except Exception as error:
        if type(error).__name__ == "LaunchCancelled":
            print("[Info] Launch cancelled.")
            return 0
        problem = expected_problem(error)
        if problem is not None:
            # Settings mistakes, missing downloads etc.: a clear message, no traceback.
            _show_console()
            print("\n[Error] " + problem, file=sys.stderr)
            acknowledge("Press Enter to exit")
            return 1
        _show_console()
        description = namespace.get("fail_message", "[Error] Tool failed: {e}")
        print(description.format(e=error), file=sys.stderr)
        traceback.print_exc()
        acknowledge("Press Enter to exit")
        return 1


def expected_problem(error):
    """Return a message for user-fixable errors (no traceback needed), else None."""
    names = {cls.__name__ for cls in type(error).__mro__}
    if names & {"SettingsError", "SetupError"}:
        return str(error)
    if isinstance(error, SyntaxError) and str(getattr(error, "filename", "") or "").endswith("developer_settings.py"):
        return f"developer_settings.py has a syntax error in line {error.lineno}: {error.msg}\n  \"{error.filename}\""
    return None


def _show_console():
    try:
        from backend.DONT_CHANGE.scripts.console_tools import show_console

        show_console()
    except Exception:
        pass
