"""Runs every launcher tool with one error, exit-code and acknowledgement policy.

bootstrap/run.bat starts `python -I -S -X utf8 entrypoint.py <tool.py> [arguments]`. The tool
is a plain module with a main() function; the optional module variables `fail_message` (text
with {e}) and `pause_on_success` (keep the window open after success) customize the policy.
"""

# Where this file sits: a shortcut runs a file in B\ (e.g. B\W.bat), which runs bootstrap\run.bat,
# which runs THIS file with the launcher's Python. This file then runs the actual tool, for example
# actions/start_program.py (start the app) or actions/setup.py (Setup).
#
# Python notes for readers new to it:
#   import x            makes another module (file) usable as x; "from x import y" takes one name.
#   def name(...):      defines a function; the indented lines below belong to it.
#   """text"""          right under a def: the function's description (docstring).
#   try: ... except E:  run the code; if error E happens inside, continue in the except part.
#   f"...{value}..."    a text with values filled in.
#   if __name__ == "__main__":  true only when this file is run directly, not when imported.
from __future__ import annotations

import os
import runpy
import sys
import traceback
from pathlib import Path
from typing import Optional, Sequence, Union

if __name__ == "__main__":
    # -I leaves the script folder off sys.path; make "pyapp...." importable (the code folder).
    # Appended, not inserted first: most standard-library imports happen later and lazily, and an
    # app module such as code/random.py or code/signal.py must not replace them in the launcher.
    sys.path.append(os.path.normpath(str((Path(__file__).parent / ".." / ".." / "..").absolute())))

import contextlib

from pyapp.DONT_CHANGE.scripts.diagnostics import note_ignored
from pyapp.DONT_CHANGE.scripts.errors import LaunchCancelled, SettingsError, SetupError


def normalize_exit_code(value: object) -> int:
    """Convert a return or SystemExit value to a process code, printing nonnumeric errors."""
    if value is None:
        return 0
    if isinstance(value, int):
        return value
    print(value, file=sys.stderr)
    return 1


def acknowledge(message: str) -> None:
    """Wait for interactive acknowledgement unless an outer launcher owns the prompt."""
    # An outer launcher can own the final prompt and preserve native-crash output.
    if os.environ.get("PYAPP_ENTRYPOINT_NO_PAUSE") == "1":
        return
    if sys.stdin is not None and sys.stdin.isatty():
        with contextlib.suppress(EOFError, KeyboardInterrupt):
            input(message)


def acknowledge_failure() -> None:
    """Wait after a failure, unless bootstrap/run.bat does that itself once this process has ended.

    run.bat waits after any failure (also when Python cannot even start this file), so asking here
    as well would make the user press a key twice.
    """
    if os.environ.get("PYAPP_BATCH_PAUSES_ON_FAILURE") == "1":
        return
    acknowledge("Press Enter to close this window.")


# The heart of this file. "-> int" means the function returns a whole number: the exit code
# (0 = success). Errors are sorted into four kinds below, from expected to unexpected.
def run_file(path: Union[str, Path], arguments: Sequence[str] = ()) -> int:
    """Load the tool, run its main() under the shared failure policy, with at most one prompt."""
    namespace = {}
    sys.argv = [str(path), *arguments]
    try:
        # Load the tool file like an imported module, then call the main() function defined in it.
        namespace = runpy.run_path(str(path), run_name="_pyapp_entry")
        main = namespace["main"]
        result = main()
        code = normalize_exit_code(result)
        # run_path returns a copy of the module globals; read the live ones, which main() may
        # have changed (e.g. "global pause_on_success").
        namespace = getattr(main, "__globals__", namespace)
        # A tool sets pause_on_success = True to keep its window open after success.
        pause_on_success = namespace.get("pause_on_success", False)
        if code != 0:
            _show_console()  # a minimized start window must not wait unseen
            acknowledge_failure()
        elif pause_on_success:
            acknowledge("Press Enter to close this window.")
        return code
    # 1. The tool called sys.exit(code): use its code.
    except SystemExit as error:
        code = normalize_exit_code(error.code)
        if code != 0:
            _show_console()
            acknowledge_failure()
        return code
    # 2. The user pressed Ctrl+C: 130 is the usual exit code for that.
    except KeyboardInterrupt:
        print("\nStopped with Ctrl+C.", file=sys.stderr)
        return 130
    # 3. and 4. Any other error: a known problem (bad setting, failed download) gets a short message;
    # anything else is a bug and gets the full traceback, so it can be reported and fixed.
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
            acknowledge_failure()
            return 1
        _show_console()
        description = namespace.get("fail_message", "Tool failed: {e}")
        print(file=sys.stderr)
        _print_error(description.format(e=error))
        traceback.print_exc()
        acknowledge_failure()
        return 1


def expected_problem(error: BaseException) -> Optional[str]:
    """Return a message for user-fixable errors (no traceback needed), else None."""
    if isinstance(error, (SettingsError, SetupError)):
        return str(error)
    return settings_file_problem(error)


SETTINGS_FILE_NAME = "developer_settings.py"


def settings_file_problem(error: BaseException) -> Optional[str]:
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


def _print_error(message: str) -> None:
    try:
        from pyapp.DONT_CHANGE.scripts.console_tools import print_error

        print_error(message, file=sys.stderr)
    except Exception:
        print("ERROR  " + message, file=sys.stderr)


def _show_console() -> None:
    try:
        from pyapp.DONT_CHANGE.scripts.console_tools import show_console

        show_console()
    except Exception:
        note_ignored("_show_console")


if __name__ == "__main__":
    raise SystemExit(run_file(sys.argv[1], sys.argv[2:]))
