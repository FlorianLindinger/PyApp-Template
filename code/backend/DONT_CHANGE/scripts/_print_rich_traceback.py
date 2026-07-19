"""WIP"""

import json
import os
import shutil
import subprocess
import sys
from typing import Any

root_dir = os.path.normpath(os.path.dirname(os.path.normpath(__file__)) + "\\..\\..\\..")
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

WARNING_TERMINAL_COLORS = "4F"
_ANSI_WARN = "\x1b[1;37;41m"
_ANSI_RESET = "\033[0m"


def _fallback_print_warn(msg: object, sep: str | None = " ", end: str | None = "\n") -> None:
    """Print a warning-styled message without importing the shared helpers."""
    print(f"{_ANSI_WARN}{msg}{_ANSI_RESET}", sep=sep, end=end)


def _fallback_input_warn(msg: object) -> str:
    """Prompt for input with warning styling when shared helpers are unavailable."""
    return input(f"{_ANSI_WARN}{msg}{_ANSI_RESET}")


try:
    from backend.developer_settings import program_name
except Exception:
    program_name = "Python"

try:
    from backend.DONT_CHANGE.scripts._common_code import input_warn, print_warn, set_terminal_title
except Exception:
    input_warn = _fallback_input_warn
    print_warn = _fallback_print_warn

    def set_terminal_title(title: str) -> None:
        """Best-effort console title setter used when shared helpers fail to import."""
        try:
            import ctypes

            ctypes.windll.kernel32.SetConsoleTitleW(title.replace("\r\n", "").replace("\r", ""))
        except Exception:
            pass


def _int_or_default(value: object, default: int) -> int:
    """Return value as int, or default when conversion fails."""
    try:
        return int(value)  # type: ignore[arg-type]
    except Exception:
        return default


def _message_rule(message: str,symbol="=") -> str:
    """Return an equals-sign rule matching message width without wrapping."""
    longest_message_line = max((len(line.expandtabs(4)) for line in message.splitlines()), default=0)
    terminal_columns = shutil.get_terminal_size(fallback=(80, 20)).columns
    max_rule_width = max(1, terminal_columns - 1)
    rule_width = min(max(1, longest_message_line), max_rule_width)
    return symbol * rule_width


def _load_traceback_payload(payload_path: str) -> dict[str, Any]:
    """Load and validate the original wrapper traceback JSON, if one was supplied."""
    if not payload_path:
        return {}

    with open(payload_path, encoding="utf-8-sig") as f:
        loaded_payload = json.load(f)

    if not isinstance(loaded_payload, dict):
        raise TypeError("Expected the wrapper traceback JSON to contain an object.")

    return loaded_payload


def _split_exception_title(error_data: dict[str, Any]) -> tuple[str, str]:
    """Return exception type and message from one serialized exception entry."""
    exception_type = str(error_data.get("type") or "")
    exception_value = str(error_data.get("message") or "")
    if exception_type:
        return exception_type, exception_value

    title = str(error_data.get("title") or "Exception")
    if ": " in title:
        exception_type, exception_value = title.split(": ", 1)
        return exception_type, exception_value
    return title, exception_value


def _traceback_heading(traceback_payload: dict[str, Any], wrapper_exit_code: int) -> str:
    """Return a user-facing traceback heading based on the target script."""
    origin = traceback_payload.get("origin") or ("child" if wrapper_exit_code == 1 else "")
    script_path = str(traceback_payload.get("script_path") or "")
    script_name = os.path.basename(script_path)

    if origin == "child" and script_name:
        return f"{script_name} traceback"
    return "Python traceback"


def _display_filename(filename: str, script_path: str) -> str:
    """Return a frame filename from the target script's perspective."""
    if filename in ("", "?"):
        return "?"

    if script_path:
        script_dir = os.path.dirname(os.path.abspath(script_path))
        try:
            relative_filename = os.path.relpath(os.path.abspath(filename), script_dir)
        except ValueError:
            relative_filename = ""

        if relative_filename and not relative_filename.startswith("..") and not os.path.isabs(relative_filename):
            return relative_filename

    return filename


def _print_exception_line(error_data: dict[str, Any]) -> None:
    """Print the final exception line for a serialized exception entry."""
    exception_type, exception_value = _split_exception_title(error_data)
    if exception_value:
        print(f"{exception_type}: {exception_value}")
    else:
        print(exception_type)


def _print_plain_traceback_payload(traceback_payload: dict[str, Any], wrapper_exit_code: int) -> None:
    """Render serialized traceback data using only built-in print output."""
    script_path = str(traceback_payload.get("script_path") or "")
    print_warn(_traceback_heading(traceback_payload, wrapper_exit_code))

    errors = traceback_payload.get("errors") or []
    if not errors:
        print_warn("No traceback frames were captured.")
        return

    for index, error_data in enumerate(errors):
        if not isinstance(error_data, dict):
            continue

        relation = str(error_data.get("relation") or "")
        if index > 0 and relation:
            print()
            print(relation)
            print()

        frames = error_data.get("frames") or []
        if frames:
            print("Traceback (most recent call last):")
            for frame_data in frames:
                if not isinstance(frame_data, dict):
                    continue
                filename = _display_filename(str(frame_data.get("filename") or "?"), script_path)
                lineno = _int_or_default(frame_data.get("lineno"), 0)
                function = str(frame_data.get("function") or "<module>")
                source = str(frame_data.get("source") or "")
                print(f'  File "{filename}", line {lineno}, in {function}')
                if source:
                    print(f"    {source.strip()}")

        syntax = error_data.get("syntax")
        if isinstance(syntax, dict):
            filename = _display_filename(str(syntax.get("filename") or "?"), script_path)
            lineno = _int_or_default(syntax.get("lineno"), 0)
            offset = _int_or_default(syntax.get("offset"), 0)
            source = str(syntax.get("text") or "")
            print(f'  File "{filename}", line {lineno}')
            if source:
                print(f"    {source.rstrip()}")
                if offset > 0:
                    print("    " + (" " * (offset - 1)) + "^")

        _print_exception_line(error_data)


def _stack_from_error(error_data: dict[str, Any], script_path: str) -> Any:
    """Build one Rich traceback Stack from a serialized exception entry."""
    from rich.traceback import Frame, Stack, _SyntaxError

    exception_type, exception_value = _split_exception_title(error_data)
    stack = Stack(exc_type=exception_type, exc_value=exception_value)

    syntax = error_data.get("syntax")
    if isinstance(syntax, dict):
        stack.syntax_error = _SyntaxError(
            offset=_int_or_default(syntax.get("offset"), 0),
            filename=_display_filename(str(syntax.get("filename") or "?"), script_path),
            line=str(syntax.get("text") or ""),
            lineno=_int_or_default(syntax.get("lineno"), 0),
            msg=exception_value or exception_type,
        )

    for frame_data in error_data.get("frames") or []:
        if not isinstance(frame_data, dict):
            continue
        stack.frames.append(
            Frame(
                filename=_display_filename(str(frame_data.get("filename") or "?"), script_path),
                lineno=_int_or_default(frame_data.get("lineno"), 0),
                name=str(frame_data.get("function") or "<module>"),
                line=str(frame_data.get("source") or ""),
            )
        )

    return stack


def _traceback_from_errors(errors: list[dict[str, Any]], script_path: str) -> Any:
    """Build a Rich Traceback object from serialized exception-chain entries."""
    from rich.traceback import Trace, Traceback

    display_stacks = [_stack_from_error(error_data, script_path) for error_data in errors]
    for index, error_data in enumerate(errors[1:], 1):
        relation = str(error_data.get("relation") or "")
        if "direct cause" in relation:
            display_stacks[index - 1].is_cause = True
    return Traceback(
        Trace(stacks=list(reversed(display_stacks))),
        width=None,
        extra_lines=3,
        word_wrap=True,
        show_locals=False,
    )


def _print_rich_traceback_payload(traceback_payload: dict[str, Any], wrapper_exit_code: int) -> None:
    """Render serialized traceback data with Rich."""
    from rich.console import Console
    from rich.text import Text

    console = Console(legacy_windows=True)
    heading = _traceback_heading(traceback_payload, wrapper_exit_code)
    script_path = str(traceback_payload.get("script_path") or "")

    raw_errors = traceback_payload.get("errors") or []
    errors = [error_data for error_data in raw_errors if isinstance(error_data, dict)]
    console.rule(Text(heading, style="bold red"), style="red")
    if not errors:
        console.print(Text("No traceback frames were captured.", style="red"))
        return

    old_cwd = os.getcwd()
    try:
        if script_path:
            os.chdir(os.path.dirname(os.path.abspath(script_path)))
        console.print(_traceback_from_errors(errors, script_path))
    finally:
        os.chdir(old_cwd)


def _has_serialized_syntax_error(traceback_payload: dict[str, Any]) -> bool:
    """Return true when any serialized exception entry contains SyntaxError data."""
    for error_data in traceback_payload.get("errors") or []:
        if isinstance(error_data, dict) and isinstance(error_data.get("syntax"), dict):
            return True
    return False


def _render_traceback_payload(traceback_payload: dict[str, Any], wrapper_exit_code: int) -> None:
    """Render traceback data with Rich when reliable, otherwise fall back to plain output."""
    if _has_serialized_syntax_error(traceback_payload):
        _print_plain_traceback_payload(traceback_payload, wrapper_exit_code)
        return

    try:
        _print_rich_traceback_payload(traceback_payload, wrapper_exit_code)
    except Exception as error:
        print_warn(f"[Warning] Rich traceback rendering failed: {error}")
        print()
        _print_plain_traceback_payload(traceback_payload, wrapper_exit_code)


def _render_watchdog_warning(
    traceback_payload: dict[str, Any], title: str, message: str, wrapper_exit_code: int
) -> None:
    """Render display metadata and an optional direct serialized traceback."""

    try:
        set_terminal_title(title)
    except Exception:
        pass

    try:
        subprocess.run(["cmd.exe", "/c", "color", WARNING_TERMINAL_COLORS], check=False)  # noqa:S603
    except Exception:
        pass

    divider = _message_rule(message)
    print()
    print_warn(divider)
    print_warn(message)
    print_warn(divider)
    print()

    if traceback_payload:
        _render_traceback_payload(traceback_payload, wrapper_exit_code)


def main() -> None:
    """Load the direct traceback JSON and render it with explicit display arguments."""
    if len(sys.argv) != 6:
        raise TypeError(
            "Expected: traceback JSON path, title, message, wrapper exit code, and wait-for-input flag."
        )

    _script_path, payload_path, title, message, wrapper_exit_code_arg, wait_for_input_arg = sys.argv
    traceback_payload = _load_traceback_payload(payload_path)
    wrapper_exit_code = _int_or_default(wrapper_exit_code_arg, 1)

    _render_watchdog_warning(
        traceback_payload,
        title or f"{program_name} - Warning",
        message or "[Warning]",
        wrapper_exit_code,
    )

    if wait_for_input_arg.casefold() == "true":
        input_warn("Press enter to exit")


if __name__ == "__main__":
    main()
