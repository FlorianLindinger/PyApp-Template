"""WIP"""


def _render_watchdog_warning_payload(payload: dict) -> None:
    title = str(payload.get("title") or f"{program_name} - Warning")
    message = str(payload.get("message") or "[Warning]")
    wrapper_exit_code = int(payload.get("wrapper_exit_code") or 1)
    traceback_payload = payload.get("traceback_payload")
    app_id = str(payload.get("app_id") or "")
    icon_file_path = str(payload.get("icon_file_path") or failure_icon_path)

    # Apply warning-specific title, color, icon, and app id before printing the warning.
    try:
        set_console_title(title)
    except Exception:
        pass

    try:
        subprocess.run(["cmd.exe", "/c", "color", WARNING_TERMINAL_COLORS], check=False)  # noqa:S603
    except Exception:
        pass

    try:
        candidate_hwnds = get_candidate_hwnds()
        warning_icon = icon_file_path if os.path.exists(icon_file_path) else icon_path
        set_terminal_icon(candidate_hwnds, warning_icon)
        if app_id:
            set_terminal_app_id_safe(candidate_hwnds, app_id)
    except Exception:
        pass

    print()
    print_warn("=" * 30)
    print_warn(message)
    print_warn("=" * 30)
    print()

    if isinstance(traceback_payload, dict):
        # Render the serialized traceback snapshot saved by the frontend wrapper.
        from rich.console import Console
        from rich.text import Text
        from rich.traceback import Frame, Stack, Trace, Traceback, _SyntaxError

        console = Console()

        def _int_or_default(value, default: int) -> int:
            try:
                return int(value)
            except Exception:
                return default

        def _split_exception_title(error_data: dict) -> tuple[str, str]:
            exception_type = str(error_data.get("type") or "")
            exception_value = str(error_data.get("message") or "")
            if exception_type:
                return exception_type, exception_value

            title = str(error_data.get("title") or "Exception")
            if ": " in title:
                exception_type, exception_value = title.split(": ", 1)
                return exception_type, exception_value
            return title, exception_value

        def _stack_from_error(error_data: dict) -> Stack:
            exception_type, exception_value = _split_exception_title(error_data)
            stack = Stack(exc_type=exception_type, exc_value=exception_value)

            syntax = error_data.get("syntax")
            if syntax:
                stack.syntax_error = _SyntaxError(
                    offset=_int_or_default(syntax.get("offset"), 0),
                    filename=str(syntax.get("filename") or "?"),
                    line=str(syntax.get("text") or ""),
                    lineno=_int_or_default(syntax.get("lineno"), 0),
                    msg=exception_value or exception_type,
                )

            for frame_data in error_data.get("frames") or []:
                stack.frames.append(
                    Frame(
                        filename=str(frame_data.get("filename") or "?"),
                        lineno=_int_or_default(frame_data.get("lineno"), 0),
                        name=str(frame_data.get("function") or "<module>"),
                        line=str(frame_data.get("source") or ""),
                    )
                )

            return stack

        def _traceback_from_errors(errors: list[dict]) -> Traceback:
            display_stacks = [_stack_from_error(error_data) for error_data in errors]
            for index, error_data in enumerate(errors[1:], 1):
                relation = error_data.get("relation") or ""
                if "direct cause" in relation:
                    display_stacks[index - 1].is_cause = True
            return Traceback(
                Trace(stacks=list(reversed(display_stacks))),
                width=None,
                extra_lines=3,
                word_wrap=True,
                show_locals=False,
            )

        origin = traceback_payload.get("origin") or ("child" if wrapper_exit_code == 1 else "wrapper")
        if origin == "child":
            heading = "Python child script traceback"
        elif origin == "wrapper":
            heading = "Python wrapper traceback"
        else:
            heading = "Python traceback"

        errors = traceback_payload.get("errors") or []
        if not errors:
            console.rule(Text(heading, style="bold red"), style="red")
            console.print(
                Text("The wrapper reported a failure, but the traceback JSON did not contain errors.", style="red")
            )
        else:
            console.rule(Text(heading, style="bold red"), style="red")
            console.print(_traceback_from_errors(errors))
    elif payload.get("missing_traceback_path"):
        # Report abrupt exits where the wrapper could not serialize a Python traceback.
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


_render_watchdog_warning_payload(payload)
if rich_traceback is not None:
    from rich.console import Console

    Console().print(rich_traceback)
if wait_for_input:
    input_warn("Press enter to exit")
