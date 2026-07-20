"""WIP"""

# {e} will be formatted to exception:
fail_message = "[Error] Failed WIP: {e}"

try:
    # ==============================
    # import Python packages
    # ==============================

    import os
    import sys
    from typing import Any, Literal

    # ==============================
    # import third-party packages
    # ==============================

    # ==============================
    # imports from files
    # ==============================

    # add root dir to resolve file imports for debug cases where this script is called on its own:
    root_dir = os.path.dirname(__file__) + "\\..\\..\\.."
    if root_dir not in sys.path:
        sys.path.insert(0, root_dir)

    from backend.developer_settings import (
        close_after_crash,
        close_after_failure,
        close_after_KeyboardInterrupt,
        close_after_success,
        crash_log_path,
        crash_log_path_is_relative_to_start_folder_if_relative,
        open_log_file_after_crash,
        open_log_file_after_failure,
        open_log_file_after_KeyboardInterrupt,
        open_log_file_after_success,
        overwrite_crash_log,
        play_sound_after_crash,
        play_sound_after_failure,
        play_sound_after_KeyboardInterrupt,
        play_sound_after_success,
        program_name,
    )
    from backend.DONT_CHANGE.scripts._common_code import (
        input_success,
        input_warn,
        print_success,
        print_traceback,
        print_warn,
        resolve_log_path,
        set_terminal_app_id,
        set_terminal_colors,
        set_terminal_icon,
        set_terminal_title,
    )
    from backend.DONT_CHANGE.scripts._common_variables import (
        CRASH_TERMINAL_COLORS,
        FAILURE_TERMINAL_COLORS,
        KEYBOARDINTERRUPT_TERMINAL_COLORS,
        SUCCESS_TERMINAL_COLORS,
        KeyboardInterrupt_icon_path,
        crash_icon_path,
        failure_icon_path,
        play_sound_after_crash_default,
        play_sound_after_failure_default,
        play_sound_after_KeyboardInterrupt_default,
        play_sound_after_success_default,
        success_icon_path,
        tmp_traceback_json_path,
        windows_dir,
    )

    # ==============================
    # define local variables
    # ==============================

    # ==============================
    # define local functions/classes
    # ==============================
    
    def _int_or_default(value: object, default: int) -> int:
        """Return value as int, or default when conversion fails."""
        try:
            return int(value)  # type: ignore[arg-type]
        except Exception:
            return default

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
        script_path = str(traceback_payload.get("script_path"))
        print_warn(os.path.basename(str(traceback_payload.get("script_path"))))

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

    def print_traceback_from_json_payload(traceback_payload: dict[str, Any], mode: int) -> None:
        """Render traceback data with Rich when reliable, otherwise fall back to plain output."""
        
        if not traceback_payload:
            return
        
        if _has_serialized_syntax_error(traceback_payload):
            _print_plain_traceback_payload(traceback_payload, wrapper_exit_code)
            return

        try:
            _print_rich_traceback_payload(traceback_payload, wrapper_exit_code)
        except Exception as error:
            print_warn(f"[Warning] Rich traceback rendering failed: {error}")
            print()
            _print_plain_traceback_payload(traceback_payload, wrapper_exit_code)


    def generate_error_text(traceback_payload: dict[str, Any], title: str, message: str) -> str:
        import json

        errors = traceback_payload.get("errors") or []

        lines = [
            "=" * 80,
            title,
            "=" * 80,
            "",
            message,
        ]

        for error in errors:
            frames = error.get("frames") or []

            if frames:
                lines.extend(["", "Traceback (most recent call last):"])

                for frame in frames:
                    lines.append(
                        f'  File "{frame.get("filename", "<unknown>")}", '
                        f"line {frame.get('lineno', '?')}, "
                        f"in {frame.get('function', '<unknown>')}"
                    )

                    if source := frame.get("source"):
                        lines.append(f"    {str(source).strip()}")

            if syntax := error.get("syntax"):
                lines.extend(
                    [
                        "",
                        json.dumps(syntax, indent=2, ensure_ascii=False),
                    ]
                )

            exception_type = error.get("type", "Exception")
            exception_message = error.get("message")

            lines.extend(
                [
                    "",
                    (f"{exception_type}: {exception_message}" if exception_message else str(exception_type)),
                ]
            )

        lines.extend(["", "=" * 80])
        return "\n".join(lines)

    def get_package_install_name(import_name: str, mappings_file_path: str) -> str:
        """Uses pipreqs mapping to convert from import name to install name: e.g., "cv2" -> "opencv-python"."""

        with open(mappings_file_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or ":" not in line:
                    continue
                import_package_name, install_package_name = line.split(":", 1)
                if import_package_name.strip() == import_name:
                    return install_package_name.strip()

        return import_name  # if not found in mappings

    def exit_code_looks_like_interpreter_crash(exit_code: int) -> bool:
        """
        Return whether a process return code matches a common Windows crash code.
        """
        windows_crash_codes = {
            -1073741819,  # unsigned: 0xC0000005 — access violation
            -1073741571,  # unsigned: 0xC00000FD — stack overflow
            -1073741795,  # unsigned: 0xC000001D — illegal instruction
            -1073741674,  # unsigned: 0xC0000096 — privileged instruction
            -1073740791,  # unsigned: 0xC0000409 — stack buffer overrun
        }

        return exit_code in windows_crash_codes

    def process_sound_and_log_opening_and_terminal_appearance(
        mode: Literal["failure", "success", "KeyboardInterrupt", "crash"], log_path: str = ""
    ) -> None:
        """Run completion side effects such as sounds and opening logs."""

        if mode == "failure":
            play_sound = play_sound_after_failure
            play_sound_default = play_sound_after_failure_default
            open_log = open_log_file_after_failure
            terminal_colors = FAILURE_TERMINAL_COLORS
            terminal_icon = failure_icon_path
        elif mode == "success":
            play_sound = play_sound_after_success
            play_sound_default = play_sound_after_success_default
            open_log = open_log_file_after_success
            terminal_colors = SUCCESS_TERMINAL_COLORS
            terminal_icon = success_icon_path
        elif mode == "KeyboardInterrupt":
            play_sound = play_sound_after_KeyboardInterrupt
            play_sound_default = play_sound_after_KeyboardInterrupt_default
            open_log = open_log_file_after_KeyboardInterrupt
            terminal_colors = KEYBOARDINTERRUPT_TERMINAL_COLORS
            terminal_icon = KeyboardInterrupt_icon_path
        elif mode == "crash":
            play_sound = play_sound_after_crash
            play_sound_default = play_sound_after_crash_default
            open_log = open_log_file_after_crash
            terminal_colors = CRASH_TERMINAL_COLORS
            terminal_icon = crash_icon_path

        set_terminal_colors(terminal_colors)
        set_terminal_icon(terminal_icon)

        if play_sound is True:
            wav_path = play_sound_default
        elif play_sound in (False, None, ""):
            wav_path = ""
        elif not os.path.isabs(play_sound):
            wav_path = os.path.normpath(windows_dir + "\\Media\\" + play_sound)
        else:
            wav_path = play_sound
        if wav_path != "":
            if wav_path[-4:] != ".wav":
                wav_path += ".wav"
        if wav_path:
            try:
                import winsound

                winsound.PlaySound(
                    wav_path,
                    winsound.SND_FILENAME | winsound.SND_NODEFAULT,
                )
            except Exception as e:
                print(f"[Error] Failed to play .wav file: {e}")

        if log_path and open_log:
            try:
                os.startfile(log_path)  # type: ignore[attr-defined]  # noqa:S606
            except Exception as e:
                print(f"[Error] Failed to open log: {e}")

    # ==============================
    # define main function
    # ==============================

    def main() -> None:
        # ==============================
        # handle args

        _script_path, exit_mode, app_id, new_terminal_was_created, log_path_resolved, selected_python_script_path = (
            sys.argv
        )
        exit_mode = int(exit_mode)
        new_terminal_was_created = new_terminal_was_created.lower() == "true"

        # ==============================
        # process exit
        
        # exit_mode meaning:
        # 0 = correctly handled exit of main.py
        # 1 = handled failure in wrapper of main.py
        # 2 = unsuccessfully handled failure in wrapper of main.py
        # (3 = handled failure in this script. See Exception of main below)
        
        # WIP: i have to not spawn a crash report on succes but everywhere else

        if os.path.exists(tmp_traceback_json_path):
            import json

            with open(tmp_traceback_json_path, encoding="utf-8") as f:
                traceback_payload = json.load(f)
            print_traceback_from_json_payload(traceback_payload,exit_mode)
            exception_type = str(traceback_payload.get("exception_type"))
        else:
            exception_type = 

        if exit_code == 0:  # success
            process_sound_and_log_opening_and_terminal_appearance("success", log_path_resolved)
            if close_after_success == False:
                print_success("[Success] Program finished successfully")
                input_success("Press enter to exit")

            sys.exit()

        elif exit_mode == 0:  # 0 = correctly handled exit of main.py
            
            if 
            
            
            # write a human readable crash log:
            crash_log_path_resolved = resolve_log_path(
                crash_log_path, crash_log_path_is_relative_to_start_folder_if_relative
            )
            if crash_log_path_resolved:
                os.makedirs(os.path.dirname(crash_log_path_resolved), exist_ok=True)
                with open(crash_log_path_resolved, "w" if overwrite_crash_log else "a") as f:
                    f.write(
                        generate_error_text(
                            traceback_payload=crash_log_payload,
                            title=f"{exception_type} - {program_name}",
                            message=f"[Error] Program failed due to {exception_type} in {os.path.basename(selected_python_script_path)}",
                        )
                    )

            if exception_type == "SystemExit":
                
                
                
                # success-like SystemExit-codes were already onvertecd to exit_code=0 in wrapper:
                
                
                
                child_exit_code = crash_log_payload.get("system_exit_code")

                if exit_code_looks_like_interpreter_crash(child_exit_code):
                    process_sound_and_log_opening_and_terminal_appearance("crash", log_path_resolved)
                    if close_after_crash == False:
                        print_warn(
                            f'[Crash] It appears like the Python interpreter crashed with exit code "{child_exit_code}" while running "{selected_python_script_path}".'
                        )
                        input_warn("Press enter to exit")
                    sys.exit()

                else:
                    process_sound_and_log_opening_and_terminal_appearance("failure", log_path_resolved)
                    if close_after_failure == False:
                        print_warn(
                            '[Failure] "{selected_python_script_path}" exited with error code "{child_exit_code}".'
                        )
                        input_warn("Press enter to exit")
                    sys.exit()

            elif exception_type in ["ImportError", "ModuleNotFoundError"]:
                process_sound_and_log_opening_and_terminal_appearance("failure", log_path_resolved)

                # options:
                # 1) install missing package->use pipreqs mappings if needed i guess
                # 2) auto search packages needed
                # 3) open terminal for manual installation
                # 4) quit

            elif exception_type == "SyntaxError":
                process_sound_and_log_opening_and_terminal_appearance("failure", log_path_resolved)

                print_traceback_from_json_payload(
                    traceback_payload,
                    message or "[Warning]",
                    wrapper_exit_code,
                )

                print_error_here_or_new_terminal(
                    f"[Error] Program failed due to a syntax error in {selected_python_script_path.split(os.sep)[-1]}",
                    traceback_json_path=tmp_traceback_json_path,
                    wrapper_exit_code=exit_code,
                    title=f"SyntaxError - {program_name}",
                    app_id=app_id,
                    icon_file_path=failure_icon_path,
                    wait_for_input=not close_after_failure,
                )
                if close_after_failure == False:
                    run_here_or_new_terminal(
                        base_script
                        + f"print_warn('[Failure] \"{selected_python_script_path}\" had a syntax error (see above).')"
                        'input_warn("Press enter to exit")'
                    )
                sys.exit(1)

            elif exception_type == "KeyboardInterrupt":
                process_sound_and_log_opening_and_terminal_appearance("KeyboardInterrupt", log_path_resolved)

                print_error_here_or_new_terminal(
                    "[Warning] Program was interrupted by user with Ctrl+C (KeyboardInterrupt)",
                    traceback_json_path=tmp_traceback_json_path,
                    wrapper_exit_code=exit_code,
                    title=f"KeyboardInterrupt - {program_name}",
                    app_id=app_id,
                    icon_file_path=failure_icon_path,
                    create_terminal=not PROGRAM_HAS_TERMINAL,
                    wait_for_input=not close_after_KeyboardInterrupt,
                )
                if close_after_KeyboardInterrupt == False:
                    run_here_or_new_terminal(
                        base_script
                        + f"print_warn('[Failure] \"{selected_python_script_path}\" was interrupted by user with Ctrl+C')"
                        'input_warn("Press enter to exit")'
                    )
                sys.exit(1)

            else:  # remaining exceptions cases
                process_sound_and_log_opening_and_terminal_appearance(
                    wav_after_failure, log_path_resolved, open_log_file_after_failure
                )
                if close_after_failure == False:
                    run_here_or_new_terminal(
                        base_script
                        + f'print_warn(\'[Failure] "{selected_python_script_path}" had exception of type {exception_type} (see above).'
                        'input_warn("Press enter to exit")'
                    )
                sys.exit(1)

            # WIP: i need to close this after opening new window and that is being closed or waited for

            # waiting and printing is handled by print_error_here_or_new_terminal, for which this script waits
            sys.exit(exit_code)

            # if close_after_failure:
            #     sys.exit(exit_code)
            # else:
            #     if PROGRAM_HAS_TERMINAL:
            #         input_warn("[Error] Press enter to exit")
            #     sys.exit(exit_code)

        elif exit_mode == 1:  # 1 = handled failure in wrapper of main.py
            import json

            json
        elif exit_mode == 2:  # 2 = unsuccessfully handled failure in wrapper of main.py
            ...
        elif exit_mode == 3:  # 3 = handled failure in background watchdog
            ...
        else:
            raise ValueError(f'[Error] Specific exit code of wrapper is not implemented: "{exit_mode}"')

    # ==============================
    # execute main function
    # ==============================

    if __name__ == "__main__":
        try:
            main()
        except Exception as e:
            print_traceback(fail_message.format(e=e))  # WIP function to be in new terminal?
            input_warn("[Error] Press enter to exit")
        sys.exit()

    # ==============================

except Exception as e:
    import os
    import traceback

    print()
    print()
    print("=" * 30)
    print(fail_message.format(e=e))
    print("-" * 30)
    print(traceback.format_exc())
    print("=" * 30)
    input("[Error] Press enter to exit")
    os._exit(1)  # instead of sys.exit(1) to prevent exception by script calling this script
