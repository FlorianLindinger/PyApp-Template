"""One error, exit-code and acknowledgement policy for developer/shortcut tools."""

import os
import runpy
import sys
import traceback


def normalize_exit_code(value):
    if value is None:
        return 0
    if isinstance(value, int):
        return value
    print(value, file=sys.stderr)
    return 1


def acknowledge(message):
    # An outer launcher can own the final prompt and preserve native-crash output.
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
            "close_terminal_on_finish" in namespace and not namespace["close_terminal_on_finish"],
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
        description = namespace.get("fail_message", "[Error] Tool failed: {e}")
        print(description.format(e=error), file=sys.stderr)
        # Standard-library reporting also works if settings or Rich cannot import.
        traceback.print_exc()
        acknowledge("Press Enter to exit")
        return 1
