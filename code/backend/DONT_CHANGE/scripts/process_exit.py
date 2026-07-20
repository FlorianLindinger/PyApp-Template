"""WIP

This script assumes that is always has a terminal to print stuff in since it is called that way.
"""

# {e} will be formatted to exception:
fail_message = "[Error] Failed WIP: {e}"

try:
    # ==============================
    # import Python packages
    # ==============================

    import os
    import sys
    from datetime import datetime
    from typing import Any, Literal, TextIO, cast

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
        ERROR_DATE_FORMAT,
        FAILURE_TERMINAL_COLORS,
        KEYBOARDINTERRUPT_TERMINAL_COLORS,
        RICH_TRACEBACK_COLOR_THEME,
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

    # ==============================
    # traceback related

    def _as_int(value: Any) -> int:
        """Return a serialized integer value, or zero if it is invalid."""
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0

    def _same_file(first_path: str, second_path: str) -> bool:
        """Compare two real filenames without treating pseudo filenames as paths."""
        if not first_path or not second_path or first_path.startswith("<") or second_path.startswith("<"):
            return False
        return os.path.normcase(os.path.abspath(first_path)) == os.path.normcase(os.path.abspath(second_path))

    def _display_filename(filename: str, script_path: str) -> str:
        """Make filenames below the traceback origin relative to its directory."""
        if not filename or filename.startswith("<") or not script_path:
            return filename or "?"

        try:
            relative_filename = os.path.relpath(
                os.path.abspath(filename), os.path.dirname(os.path.abspath(script_path))
            )
        except ValueError:
            return filename

        if relative_filename != ".." and not relative_filename.startswith(".." + os.sep):
            return relative_filename
        return filename

    def _traceback_entries(traceback_payload: dict[str, Any]) -> list[dict[str, Any]]:
        """Return exception entries from the current traceback JSON format."""
        return [entry for entry in traceback_payload.get("traceback") or [] if isinstance(entry, dict)]

    def _traceback_metadata_lines(traceback_payload: dict[str, Any]) -> list[str]:
        """Return details about when and where the failure is handled."""
        lines: list[str] = []
        if script_path := traceback_payload.get("script_path"):
            lines.append(f"Script: {os.path.abspath(str(script_path))}")

        error_datetime = datetime.now().astimezone().strftime(ERROR_DATE_FORMAT)
        lines.append(f"Error date: {error_datetime}")
        if python_version := traceback_payload.get("python_version"):
            lines.append(f"Python: {python_version}")
        return lines

    def _frames_from_traceback_origin(error_data: dict[str, Any], script_path: str) -> list[dict[str, Any]]:
        """
        Return frames from the perspective of the script that produced the payload.

        ``traceback_payload["script_path"]`` is passed as ``script_path``. Each
        exception-chain entry is handled independently because a chained inner
        exception may already start inside the target script while the final
        exception still contains wrapper and ``runpy`` frames.

        Frames before the first filename matching ``script_path`` are removed.
        For a compile-time SyntaxError, the target may occur only in the syntax
        metadata; in that case every outer frame is removed. If neither location
        matches, all frames are retained so an unknown origin loses no evidence.
        """
        frames = [frame for frame in error_data.get("frames") or [] if isinstance(frame, dict)]
        if not script_path:
            return frames

        for outer_frames_to_skip, frame in enumerate(frames):
            if _same_file(str(frame.get("filename") or ""), script_path):
                return frames[outer_frames_to_skip:]

        syntax = error_data.get("syntax")
        if isinstance(syntax, dict) and _same_file(str(syntax.get("filename") or ""), script_path):
            return []
        return frames

    def _plain_traceback_lines(traceback_payload: dict[str, Any]) -> list[str]:
        """Format the current traceback JSON as plain text."""
        script_path = str(traceback_payload.get("script_path") or "")
        lines: list[str] = []

        for error_index, error_data in enumerate(_traceback_entries(traceback_payload)):
            relation = str(error_data.get("relation") or "")
            if error_index and relation:
                lines.extend(["", relation, ""])

            frames = _frames_from_traceback_origin(error_data, script_path)
            if frames:
                lines.append("Traceback (most recent call last):")
                for frame in frames:
                    lines.append(
                        f'  File "{_display_filename(str(frame.get("filename") or "?"), script_path)}", '
                        f"line {_as_int(frame.get('lineno')) or '?'}, "
                        f"in {frame.get('function') or '<module>'}"
                    )
                    if source := frame.get("source"):
                        lines.append(f"    {str(source).strip()}")

            syntax = error_data.get("syntax")
            if isinstance(syntax, dict):
                lines.append(
                    f'  File "{_display_filename(str(syntax.get("filename") or "?"), script_path)}", '
                    f"line {_as_int(syntax.get('lineno')) or '?'}"
                )
                if source := syntax.get("text"):
                    lines.append(f"    {str(source).rstrip()}")
                    offset = _as_int(syntax.get("offset"))
                    if offset > 0:
                        lines.append("    " + " " * (offset - 1) + "^")

            exception_type = str(error_data.get("type") or "Exception")
            exception_message = str(error_data.get("message") or "")
            lines.append(f"{exception_type}: {exception_message}" if exception_message else exception_type)

        return lines or ["No traceback frames were captured."]

    def _rich_stack(error_data: dict[str, Any], script_path: str) -> Any:
        """Build one native Rich traceback stack from a serialized exception."""
        from rich.traceback import Frame, Stack, _SyntaxError

        exception_type = str(error_data.get("type") or "Exception")
        exception_message = str(error_data.get("message") or "")
        stack = Stack(exc_type=exception_type, exc_value=exception_message)

        syntax = error_data.get("syntax")
        if isinstance(syntax, dict):
            stack.syntax_error = _SyntaxError(
                offset=_as_int(syntax.get("offset")),
                filename=_display_filename(str(syntax.get("filename") or "?"), script_path),
                line=str(syntax.get("text") or ""),
                lineno=_as_int(syntax.get("lineno")),
                msg=exception_message or exception_type,
            )

        for frame in _frames_from_traceback_origin(error_data, script_path):
            stack.frames.append(
                Frame(
                    filename=_display_filename(str(frame.get("filename") or "?"), script_path),
                    lineno=_as_int(frame.get("lineno")),
                    name=str(frame.get("function") or "<module>"),
                    line=str(frame.get("source") or ""),
                )
            )
        return stack

    def _rich_traceback(traceback_payload: dict[str, Any]) -> Any:
        """Build a native Rich Traceback from the current JSON format."""
        from rich.traceback import Trace, Traceback

        script_path = str(traceback_payload.get("script_path") or "")
        errors = _traceback_entries(traceback_payload)
        stacks = [_rich_stack(error_data, script_path) for error_data in errors]

        for error_index, error_data in enumerate(errors[1:], 1):
            if "direct cause" in str(error_data.get("relation") or ""):
                stacks[error_index - 1].is_cause = True

        return Traceback(
            Trace(stacks=list(reversed(stacks))),
            width=None,
            extra_lines=3,
            theme=RICH_TRACEBACK_COLOR_THEME["code"],
            word_wrap=True,
            show_locals=False,
        )

    class _RichSafeStream:
        """Keep Rich output writable on legacy Windows console encodings."""

        def __init__(self, stream: TextIO) -> None:
            self.stream = stream

        def writable(self) -> bool:
            return True

        def write(self, text: str) -> int:
            encoding = getattr(self.stream, "encoding", None) or "utf-8"
            if encoding:
                try:
                    text.encode(encoding)
                except UnicodeEncodeError:
                    text = text.replace("\u25b2", "^").encode(encoding, errors="replace").decode(encoding)
            written = self.stream.write(text)
            return len(text) if written is None else written

        def flush(self) -> None:
            self.stream.flush()

        def isatty(self) -> bool:
            return self.stream.isatty()

        def fileno(self) -> int:
            return self.stream.fileno()

    def print_traceback_from_json_payload(traceback_payload: dict[str, Any]) -> None:
        """Render the current traceback JSON format, preferring Rich's native layout."""
        if not traceback_payload:
            return

        script_path = str(traceback_payload.get("script_path") or "")
        script_path = os.path.abspath(script_path) if script_path else ""
        script_name = os.path.basename(script_path) or "Python traceback"
        metadata_lines = _traceback_metadata_lines(traceback_payload)
        try:
            from rich.align import Align
            from rich.console import Console
            from rich.padding import Padding
            from rich.text import Text
            from rich.theme import Theme

            background = RICH_TRACEBACK_COLOR_THEME["background"]
            background_style = f"on {background}"
            border_style = f"{RICH_TRACEBACK_COLOR_THEME['border']} {background_style}"
            label_style = f"{RICH_TRACEBACK_COLOR_THEME['label']} {background_style}"
            metadata_style = f"{RICH_TRACEBACK_COLOR_THEME['metadata']} {background_style}"
            text_style = f"{RICH_TRACEBACK_COLOR_THEME['text']} {background_style}"
            traceback_entries = _traceback_entries(traceback_payload)
            rich_traceback = _rich_traceback(traceback_payload) if traceback_entries else None
            console = Console(
                file=cast(TextIO, _RichSafeStream(sys.stdout)),
                legacy_windows=True,
                theme=Theme(
                    {
                        "traceback.border": border_style,
                        "traceback.border.syntax_error": (
                            f"{RICH_TRACEBACK_COLOR_THEME['syntax_border']} {background_style}"
                        ),
                        "traceback.text": text_style,
                        "traceback.title": label_style,
                        "traceback.exc_type": label_style,
                        "traceback.exc_value": text_style,
                        "traceback.offset": (f"{RICH_TRACEBACK_COLOR_THEME['syntax_pointer']} {background_style}"),
                    },
                    inherit=True,
                ),
            )
            console.rule(
                Text(f" {script_name} ", style=label_style),
                style=border_style,
            )
            if metadata_lines:
                for metadata_line in metadata_lines:
                    console.print(
                        Align.left(
                            Text(metadata_line, style=metadata_style, overflow="fold"),
                            style=background_style,
                        ),
                    )
            if rich_traceback is not None:
                old_cwd = os.getcwd()
                try:
                    script_folder = os.path.dirname(os.path.abspath(script_path)) if script_path else ""
                    if os.path.isdir(script_folder):
                        os.chdir(script_folder)
                    console.print(
                        Padding(
                            rich_traceback,
                            (0, 0, 1, 0),
                            style=background_style,
                            expand=True,
                        )
                    )
                finally:
                    os.chdir(old_cwd)
            else:
                console.print("No traceback frames were captured.", style="red")
        except Exception as error:
            print_warn(f"[Warning] Rich traceback rendering failed: {error}")
            print()
            print_warn(script_name)
            for metadata_line in metadata_lines:
                print(metadata_line)
            print("\n".join(_plain_traceback_lines(traceback_payload)))

    def payload_to_text(traceback_payload: dict[str, Any], title: str, message: str) -> str:
        """Build a plain-text crash report from the current traceback JSON format."""
        lines = ["=" * 80, title, "-" * 80, "", message, "", "-" * 80]
        lines.extend(_traceback_metadata_lines(traceback_payload))
        lines.append("")
        lines.extend(_plain_traceback_lines(traceback_payload))
        lines.extend(["", "=" * 80])
        return "\n".join(lines)

    def write_txt_crash_log(crash_log_payload, title, message):
        # write a human readable crash log:
        crash_log_path_resolved = resolve_log_path(
            crash_log_path, crash_log_path_is_relative_to_start_folder_if_relative
        )
        if crash_log_path_resolved:
            os.makedirs(os.path.dirname(crash_log_path_resolved), exist_ok=True)
            with open(crash_log_path_resolved, "w" if overwrite_crash_log else "a") as f:
                f.write(
                    payload_to_text(
                        traceback_payload=crash_log_payload,
                        title=title,
                        message=message,
                    )
                )

    # ==============================
    # miscellaneous

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
        # 0 = correctly handled end of script in main.py (no json)
        # 1 = correctly handled other exit of main.py (json)
        # 2 = handled failure in wrapper of main.py (json)
        # 3 = unsuccessfully handled failure in wrapper of main.py (no json)
        # 4 = handled failure watchdog script (json)

        if exit_mode == 0:  # 0 = correctly handled end of script in main.py (no json)
            process_sound_and_log_opening_and_terminal_appearance("success", log_path_resolved)
            if close_after_success == False:
                print_success("[Success] Program finished successfully")
                input_success("Press enter to exit")
            sys.exit()

        elif exit_mode == 1:  # 1 = correctly handled other exit of main.py (json)
            if os.path.exists(tmp_traceback_json_path):
                import json

                with open(tmp_traceback_json_path, encoding="utf-8") as f:
                    traceback_payload = json.load(f)

                traceback_entries = _traceback_entries(traceback_payload)
                exception_type = (
                    str(traceback_entries[-1].get("type") or "Exception")
                    if traceback_entries
                    else "Exception"
                )

                if exception_type == "SystemExit":  # includes success exits
                    main_exit_code = traceback_payload.get("system_exit_code")

                    # success = main_exit_code: 0, None,False
                    # failure = main_exit_code: non-0-int, True, float, strings (Anything not mentioned here get converted to string in wrapper)

                    if main_exit_code in (0, None, False):  # success
                        process_sound_and_log_opening_and_terminal_appearance("success", log_path_resolved)
                        print_traceback_from_json_payload(traceback_payload)
                        if close_after_success == False:
                            print_success("[Success] Program finished successfully")
                            input_success("Press enter to exit")

                    elif exit_code_looks_like_interpreter_crash(main_exit_code):
                        write_txt_crash_log(traceback_payload, "WIP", "WIP")
                        process_sound_and_log_opening_and_terminal_appearance("crash", log_path_resolved)
                        print_traceback_from_json_payload(traceback_payload)
                        if close_after_crash == False:
                            print_warn(
                                f'[Crash] It appears like the Python interpreter crashed with exit code "{main_exit_code}" while running "{selected_python_script_path}".'
                            )
                            input_warn("Press enter to exit")

                    else:
                        write_txt_crash_log(traceback_payload, "WIP", "WIP")
                        process_sound_and_log_opening_and_terminal_appearance("failure", log_path_resolved)
                        print_traceback_from_json_payload(traceback_payload)
                        if close_after_failure == False:
                            print_warn(
                                f'[Failure] "{selected_python_script_path}" exited with error code "{main_exit_code}".'
                            )
                            input_warn("Press enter to exit")

                elif exception_type in ["ImportError", "ModuleNotFoundError"]:
                    process_sound_and_log_opening_and_terminal_appearance("failure", log_path_resolved)
                    print_traceback_from_json_payload(traceback_payload)

                    # options:
                    # 1) install missing package->use pipreqs mappings if needed i guess
                    # 2) auto search packages needed
                    # 3) open terminal for manual installation
                    # 4) quit
                    
                    input("WIP")

                elif exception_type == "SyntaxError":
                    write_txt_crash_log(traceback_payload, "WIP", "WIP")
                    process_sound_and_log_opening_and_terminal_appearance("failure", log_path_resolved)
                    print_traceback_from_json_payload(traceback_payload)
                    if close_after_failure == False:
                        print_warn(f'[Failure] "{selected_python_script_path}" had a syntax error (see above).')
                        input_warn("Press enter to exit")

                elif exception_type == "KeyboardInterrupt":
                    write_txt_crash_log(traceback_payload, "WIP", "WIP")
                    process_sound_and_log_opening_and_terminal_appearance("KeyboardInterrupt", log_path_resolved)
                    print_traceback_from_json_payload(traceback_payload)

                    if close_after_KeyboardInterrupt == False:
                        print_warn(f'[Failure] "{selected_python_script_path}" was interrupted by user with Ctrl+C')
                        input_warn("Press enter to exit")

                else:  # remaining exceptions cases
                    write_txt_crash_log(traceback_payload, "WIP", "WIP")
                    process_sound_and_log_opening_and_terminal_appearance("failure", log_path_resolved)
                    print_traceback_from_json_payload(traceback_payload)
                    if close_after_failure == False:
                        print_warn(
                            f'[Failure] "{selected_python_script_path}" had exception of type "{exception_type}" (see above).'
                        )
                        input_warn("Press enter to exit")

            else:
                ...  # fialed to generate json ....

        elif exit_mode == 2:  # 2 = handled failure in wrapper of main.py (json)
            ...
        elif exit_mode == 3:  # 3 = unsuccessfully handled failure in wrapper of main.py (no json)
            ...
        elif exit_mode == 4:  # 4 = handled failure watchdog script (json)
            ...
        else:
            ...
            # print
            # raise ValueError(f'[Error] Specific exit code of wrapper is not implemented: "{exit_mode}"')

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
