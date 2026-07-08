"""Render traceback payloads passed by background_watchdog."""

import json
import os
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
    print(f"{_ANSI_WARN}{msg}{_ANSI_RESET}", sep=sep, end=end)


def _fallback_input_warn(msg: object) -> str:
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
        try:
            import ctypes

            ctypes.windll.kernel32.SetConsoleTitleW(title.replace("\r\n", "").replace("\r", ""))
        except Exception:
            pass


def _int_or_default(value: object, default: int) -> int:
    try:
        return int(value)  # type: ignore[arg-type]
    except Exception:
        return default


def _load_payload() -> dict[str, Any]:
    if len(sys.argv) != 2:
        raise ValueError("Expected a watchdog traceback payload JSON path as the only argument.")

    with open(sys.argv[1], encoding="utf-8-sig") as f:
        loaded_payload = json.load(f)

    if not isinstance(loaded_payload, dict):
        raise ValueError("Expected the watchdog traceback payload JSON to contain an object.")

    return loaded_payload


def _split_exception_title(error_data: dict[str, Any]) -> tuple[str, str]:
    exception_type = str(error_data.get("type") or "")
    exception_value = str(error_data.get("message") or "")
    if exception_type:
        return exception_type, exception_value

    title = str(error_data.get("title") or "Exception")
    if ": " in title:
        exception_type, exception_value = title.split(": ", 1)
        return exception_type, exception_value
    return title, exception_value


def _print_exception_line(error_data: dict[str, Any]) -> None:
    exception_type, exception_value = _split_exception_title(error_data)
    if exception_value:
        print(f"{exception_type}: {exception_value}")
    else:
        print(exception_type)


def _print_plain_traceback_payload(traceback_payload: dict[str, Any], wrapper_exit_code: int) -> None:
    origin = traceback_payload.get("origin") or ("child" if wrapper_exit_code == 1 else "wrapper")
    if origin == "child":
        print_warn("Python child script traceback")
    elif origin == "wrapper":
        print_warn("Python wrapper traceback")
    else:
        print_warn("Python traceback")

    errors = traceback_payload.get("errors") or []
    if not errors:
        print_warn("The wrapper reported a failure, but the traceback JSON did not contain errors.")
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
                filename = str(frame_data.get("filename") or "?")
                lineno = _int_or_default(frame_data.get("lineno"), 0)
                function = str(frame_data.get("function") or "<module>")
                source = str(frame_data.get("source") or "")
                print(f'  File "{filename}", line {lineno}, in {function}')
                if source:
                    print(f"    {source.strip()}")

        syntax = error_data.get("syntax")
        if isinstance(syntax, dict):
            filename = str(syntax.get("filename") or "?")
            lineno = _int_or_default(syntax.get("lineno"), 0)
            offset = _int_or_default(syntax.get("offset"), 0)
            source = str(syntax.get("text") or "")
            print(f'  File "{filename}", line {lineno}')
            if source:
                print(f"    {source.rstrip()}")
                if offset > 0:
                    print("    " + (" " * (offset - 1)) + "^")

        _print_exception_line(error_data)


def _stack_from_error(error_data: dict[str, Any]) -> Any:
    from rich.traceback import Frame, Stack, _SyntaxError

    exception_type, exception_value = _split_exception_title(error_data)
    stack = Stack(exc_type=exception_type, exc_value=exception_value)

    syntax = error_data.get("syntax")
    if isinstance(syntax, dict):
        stack.syntax_error = _SyntaxError(
            offset=_int_or_default(syntax.get("offset"), 0),
            filename=str(syntax.get("filename") or "?"),
            line=str(syntax.get("text") or ""),
            lineno=_int_or_default(syntax.get("lineno"), 0),
            msg=exception_value or exception_type,
        )

    for frame_data in error_data.get("frames") or []:
        if not isinstance(frame_data, dict):
            continue
        stack.frames.append(
            Frame(
                filename=str(frame_data.get("filename") or "?"),
                lineno=_int_or_default(frame_data.get("lineno"), 0),
                name=str(frame_data.get("function") or "<module>"),
                line=str(frame_data.get("source") or ""),
            )
        )

    return stack


def _traceback_from_errors(errors: list[dict[str, Any]]) -> Any:
    from rich.traceback import Trace, Traceback

    display_stacks = [_stack_from_error(error_data) for error_data in errors]
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
    from rich.console import Console
    from rich.text import Text

    console = Console(legacy_windows=True)
    origin = traceback_payload.get("origin") or ("child" if wrapper_exit_code == 1 else "wrapper")
    if origin == "child":
        heading = "Python child script traceback"
    elif origin == "wrapper":
        heading = "Python wrapper traceback"
    else:
        heading = "Python traceback"

    raw_errors = traceback_payload.get("errors") or []
    errors = [error_data for error_data in raw_errors if isinstance(error_data, dict)]
    console.rule(Text(heading, style="bold red"), style="red")
    if not errors:
        console.print(Text("The wrapper reported a failure, but the traceback JSON did not contain errors.", style="red"))
        return

    console.print(_traceback_from_errors(errors))


def _has_serialized_syntax_error(traceback_payload: dict[str, Any]) -> bool:
    for error_data in traceback_payload.get("errors") or []:
        if isinstance(error_data, dict) and isinstance(error_data.get("syntax"), dict):
            return True
    return False


def _render_traceback_payload(traceback_payload: dict[str, Any], wrapper_exit_code: int) -> None:
    if _has_serialized_syntax_error(traceback_payload):
        _print_plain_traceback_payload(traceback_payload, wrapper_exit_code)
        return

    try:
        _print_rich_traceback_payload(traceback_payload, wrapper_exit_code)
    except Exception as error:
        print_warn(f"[Warning] Rich traceback rendering failed: {error}")
        print()
        _print_plain_traceback_payload(traceback_payload, wrapper_exit_code)


def _render_missing_traceback_message(payload: dict[str, Any], wrapper_exit_code: int) -> None:
    missing_traceback_path = str(payload["missing_traceback_path"])
    print_warn("=" * 30)
    print_warn("[Error] Python process exited without a captured traceback")
    print_warn("-" * 30)
    print_warn(f'Wrapper exit code: "{wrapper_exit_code}"')
    print_warn(f'Expected traceback JSON: "{missing_traceback_path}"')
    print_warn("-" * 30)
    if wrapper_exit_code == 1:
        print_warn("The child script ended before the wrapper could write traceback data.")
        print_warn("Common causes: os._exit(...), os.abort(), native crash, or forced process kill.")
    elif wrapper_exit_code == 2:
        print_warn("The wrapper failed before it could write traceback data.")
    else:
        print_warn("The process ended before traceback data was available.")
    print_warn("=" * 30)


def _render_watchdog_warning_payload(payload: dict[str, Any]) -> None:
    title = str(payload.get("title") or f"{program_name} - Warning")
    message = str(payload.get("message") or "[Warning]")
    wrapper_exit_code = _int_or_default(payload.get("wrapper_exit_code"), 1)
    traceback_payload = payload.get("traceback_payload")

    try:
        set_terminal_title(title)
    except Exception:
        pass

    try:
        subprocess.run(["cmd.exe", "/c", "color", WARNING_TERMINAL_COLORS], check=False)  # noqa:S603
    except Exception:
        pass

    print()
    print_warn("=" * 30)
    print_warn(message)
    print_warn("=" * 30)
    print()

    if isinstance(traceback_payload, dict):
        _render_traceback_payload(traceback_payload, wrapper_exit_code)
    elif payload.get("missing_traceback_path"):
        _render_missing_traceback_message(payload, wrapper_exit_code)


def main() -> None:
    loaded_payload = _load_payload()

    _render_watchdog_warning_payload(loaded_payload)

    if loaded_payload.get("wait_for_input", False):
        input_warn("Press enter to exit")


if __name__ == "__main__":
    main()
