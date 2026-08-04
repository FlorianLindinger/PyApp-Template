"""Apply configured completion behavior after the wrapper or watchdog exits.

This script is always launched with a terminal available for status output.
"""

# ==============================
# settings

# {e} will be formatted to exception:
fail_message = "[Error] Failed while processing program exit: {e}"

try:
    # ==============================
    # import Python packages
    # ==============================

    import os
    import subprocess
    import sys
    from datetime import datetime
    from typing import Any, Literal, TextIO, cast

    # ==============================
    # import third-party packages
    # ==============================

    # ==============================
    # import from files
    # ==============================

    # add root dir to resolve file imports for debug cases where this script is called on its own:
    root_dir = os.path.dirname(__file__) + "\\..\\..\\..\\..\\.."
    if root_dir not in sys.path:
        sys.path.insert(0, root_dir)

    from backend.developer_settings import (
        PRINTED_ERROR_DATE_FORMAT,
        RICH_TRACEBACK_COLOR_THEME,
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
        open_main_py_after_crash,
        open_main_py_after_failure,
        open_main_py_after_KeyboardInterrupt,
        open_main_py_after_success,
        overwrite_crash_log,
        play_sound_after_crash,
        play_sound_after_failure,
        play_sound_after_KeyboardInterrupt,
        play_sound_after_success,
        show_traceback_locals,
        terminal_colors_after_crash,
        terminal_colors_after_failure,
        terminal_colors_after_KeyboardInterrupt,
        terminal_colors_after_success,
        title_after_crash,
        title_after_failure,
        title_after_KeyboardInterrupt,
        title_after_success,
        traceback_extra_lines,
        use_uv_to_install_packages,
    )
    from backend.DONT_CHANGE.scripts.common_code import (
        get_log_path,
        input_warn,
        install_packages_from_file,
        print_traceback,
        print_warn,
        save_requirements_of_root_folder_noVersion,
        set_terminal_app_id,
        set_terminal_colors,
        set_terminal_icon,
        set_terminal_title,
    )
    from backend.DONT_CHANGE.scripts.generic_helpers import (
        exit_code_looks_like_interpreter_crash,
        install_packages,
        open_in_editor,
    )
    from backend.DONT_CHANGE.settings.backend_settings import (
        BACKEND_PYTHON_EXE,
        CRASH_ICON_PATH,
        DEFAULT_SOUND_AFTER_CRASH,
        DEFAULT_SOUND_AFTER_FAILURE,
        DEFAULT_SOUND_AFTER_SUCCESS,
        FAILURE_ICON_PATH,
        FRONTEND_LAUNCHER_FOR_PIP_INSTALL_TERMINAL,
        FRONTEND_PACKAGES_DIR,
        FRONTEND_PYTHON_EXE,
        KEYBOARD_INTERRUPT_ICON_PATH,
        MAIN_PY_SCRIPT_PATH,
        PIPREQS_MAPPING_PATH,
        START_PROGRAM_PATH,
        SUCCESS_ICON_PATH,
        TMP_TRACEBACK_JSON_PATH,
        WINDOWS_DIR,
        DEFAULT_SOUND_AFTER_KeyboardInterrupt,
    )

    # ==============================
    # local variables
    # ==============================

    # ==============================
    # local functions/classes
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
        if (
            not first_path
            or not second_path
            or first_path.startswith("<")
            or second_path.startswith("<")
        ):
            return False
        return os.path.normcase(os.path.abspath(first_path)) == os.path.normcase(
            os.path.abspath(second_path)
        )

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

        if relative_filename != ".." and not relative_filename.startswith(
            ".." + os.sep
        ):
            return relative_filename
        return filename

    def _traceback_entries(traceback_payload: dict[str, Any]) -> list[dict[str, Any]]:
        """Return exception entries from the current traceback JSON format."""
        return [
            entry
            for entry in traceback_payload.get("traceback") or []
            if isinstance(entry, dict)
        ]

    def _traceback_metadata_lines(traceback_payload: dict[str, Any]) -> list[str]:
        """Return details about when and where the failure is handled."""
        lines: list[str] = []
        if script_path := traceback_payload.get("script_path"):
            lines.append(f"Script: {os.path.abspath(str(script_path))}")

        error_datetime = datetime.now().astimezone().strftime(PRINTED_ERROR_DATE_FORMAT)
        lines.append(f"Error date: {error_datetime}")
        if python_version := traceback_payload.get("python_version"):
            lines.append(f"Python: {python_version}")
        return lines

    def _frames_from_traceback_origin(
        error_data: dict[str, Any], script_path: str
    ) -> list[dict[str, Any]]:
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
        frames = [
            frame for frame in error_data.get("frames") or [] if isinstance(frame, dict)
        ]
        if not script_path:
            return frames

        for outer_frames_to_skip, frame in enumerate(frames):
            if _same_file(str(frame.get("filename") or ""), script_path):
                return frames[outer_frames_to_skip:]

        syntax = error_data.get("syntax")
        if isinstance(syntax, dict) and _same_file(
            str(syntax.get("filename") or ""), script_path
        ):
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
            lines.append(
                f"{exception_type}: {exception_message}"
                if exception_message
                else exception_type
            )

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
                filename=_display_filename(
                    str(syntax.get("filename") or "?"), script_path
                ),
                line=str(syntax.get("text") or ""),
                lineno=_as_int(syntax.get("lineno")),
                msg=exception_message or exception_type,
            )

        for frame in _frames_from_traceback_origin(error_data, script_path):
            stack.frames.append(
                Frame(
                    filename=_display_filename(
                        str(frame.get("filename") or "?"), script_path
                    ),
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
            extra_lines=traceback_extra_lines,
            theme=RICH_TRACEBACK_COLOR_THEME["code"],
            word_wrap=True,
            show_locals=show_traceback_locals,
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
                    text = (
                        text.replace("\u25b2", "^")
                        .encode(encoding, errors="replace")
                        .decode(encoding)
                    )
            written = self.stream.write(text)
            return len(text) if written is None else written

        def flush(self) -> None:
            self.stream.flush()

        def isatty(self) -> bool:
            return self.stream.isatty()

        def fileno(self) -> int:
            return self.stream.fileno()

    def print_traceback_from_json_payload(
        traceback_payload: dict[str, Any] | None,
    ) -> None:
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
            metadata_style = (
                f"{RICH_TRACEBACK_COLOR_THEME['metadata']} {background_style}"
            )
            text_style = f"{RICH_TRACEBACK_COLOR_THEME['text']} {background_style}"
            traceback_entries = _traceback_entries(traceback_payload)
            rich_traceback = (
                _rich_traceback(traceback_payload) if traceback_entries else None
            )
            console = Console(
                file=cast("TextIO", _RichSafeStream(sys.stdout)),
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
                        "traceback.offset": (
                            f"{RICH_TRACEBACK_COLOR_THEME['syntax_pointer']} {background_style}"
                        ),
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
                    script_folder = (
                        os.path.dirname(os.path.abspath(script_path))
                        if script_path
                        else ""
                    )
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
            print(f"[Error] Rich traceback rendering failed: {error}")
            print()
            print(script_name)
            for metadata_line in metadata_lines:
                print(metadata_line)
            print("\n".join(_plain_traceback_lines(traceback_payload)))

    def write_txt_crash_log(
        crash_log_payload: dict[str, Any] | None, message: str | None
    ):
        # write a human readable crash log:
        crash_log_path_resolved = get_log_path(
            crash_log_path, crash_log_path_is_relative_to_start_folder_if_relative
        )

        divider_length: int = 30

        if crash_log_payload is None and message is None:
            return

        if crash_log_path_resolved:
            lines: list[str] = ["=" * divider_length]
            if message:
                lines.append(message)
            if crash_log_payload:
                if message:
                    lines.append("-" * divider_length)
                lines.extend(_traceback_metadata_lines(crash_log_payload))
                lines.append("-" * divider_length)
                lines.extend(_plain_traceback_lines(crash_log_payload))
            lines.append("=" * divider_length)

            os.makedirs(os.path.dirname(crash_log_path_resolved), exist_ok=True)
            with open(
                crash_log_path_resolved, "w" if overwrite_crash_log else "a"
            ) as f:
                f.write("\n".join(lines))

    # ==============================
    # miscellaneous

    def get_package_install_name(import_name: str) -> str:
        """Uses pipreqs mapping to convert from import name to install name: e.g., "cv2" -> "opencv-python"."""

        with open(PIPREQS_MAPPING_PATH, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or ":" not in line:
                    continue
                import_package_name, install_package_name = line.split(":", 1)
                if import_package_name.strip() == import_name:
                    return install_package_name.strip()

        return import_name  # if not found in mappings

    def restart_program(app_id: str, new_terminal_was_created: bool) -> None:
        """Relaunch the program using the same visible/hidden terminal behavior."""
        launch_mode = "no_terminal" if new_terminal_was_created else "terminal"
        subprocess.Popen(
            [BACKEND_PYTHON_EXE, START_PROGRAM_PATH, app_id, launch_mode],
        )

    def install_auto_detected_packages(app_id: str) -> None:
        """Discover project imports and install all inferred distributions."""
        success, requirements_path = save_requirements_of_root_folder_noVersion()
        if not success:
            raise RuntimeError("Could not auto-detect the project's required packages.")
        install_packages_from_file(requirements_path, app_id_for_slow=app_id)

    def open_manual_package_terminal() -> None:
        """Wait for the user to finish package changes in a configured terminal."""
        if not os.path.isfile(FRONTEND_LAUNCHER_FOR_PIP_INSTALL_TERMINAL):
            raise FileNotFoundError(
                f'Package-terminal launcher not found at "{FRONTEND_LAUNCHER_FOR_PIP_INSTALL_TERMINAL}"'
            )

        print()
        print(
            'Install packages with "pip install package_name", then type "exit" to restart the program.'
        )
        subprocess.run(
            ["cmd.exe", "/d", "/c", "call", FRONTEND_LAUNCHER_FOR_PIP_INSTALL_TERMINAL],
            check=True,
        )

    def handle_missing_package_options(
        missing_module: str,
        install_name: str,
        app_id: str,
        new_terminal_was_created: bool,
    ) -> None:
        """Prompt for package recovery and restart after a successful recovery action."""
        while True:
            print()
            print_warn("Choose how to proceed:")
            print("1: Install the missing package and restart")
            print("2: Auto-detect required packages, install them, and restart")
            print("3: Open a terminal for manual package installation, then restart")
            print("4: Quit")
            choice = input_warn("Choose an option [1-4]: ").strip()

            if choice == "4":
                return
            if choice not in {"1", "2", "3"}:
                print_warn("[Warning] Invalid choice. Please enter 1, 2, 3, or 4.")
                continue

            try:
                if choice == "1":
                    if not missing_module:
                        print_warn(
                            "[Warning] The exception did not identify a missing module. Choose another option."
                        )
                        continue
                    print(
                        f'[Info] Installing "{install_name}" for missing import "{missing_module}"...'
                    )
                    install_packages(
                        python_exe=FRONTEND_PYTHON_EXE,
                        packages=install_name,
                        target=FRONTEND_PACKAGES_DIR,
                        upgrade=True,
                        use_uv=use_uv_to_install_packages,
                        local_uv_python_exe=BACKEND_PYTHON_EXE,
                    )
                elif choice == "2":
                    print("[Info] Auto-detecting and installing required packages...")
                    install_auto_detected_packages(app_id)
                else:
                    open_manual_package_terminal()
            except Exception as error:
                print_traceback(f"[Error] Package recovery failed: {error}")
                continue

            print("[Success] Package recovery completed. Restarting the program...")
            restart_program(app_id, new_terminal_was_created)
            return

    def load_traceback_payload() -> tuple[dict[str, Any] | None, str | None]:
        """Load the wrapper's traceback report and describe unusable reports."""
        import json

        try:
            with open(TMP_TRACEBACK_JSON_PATH, encoding="utf-8") as f:
                payload = json.load(f)
        except FileNotFoundError:
            return (
                None,
                f'Traceback report was not created at "{TMP_TRACEBACK_JSON_PATH}".',
            )
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            return (
                None,
                f'Could not read traceback report "{TMP_TRACEBACK_JSON_PATH}": {error}',
            )

        if not isinstance(payload, dict):
            return (
                None,
                f'Traceback report "{TMP_TRACEBACK_JSON_PATH}" does not contain a JSON object.',
            )
        return payload, None

    def execute_exit_settings(
        mode: Literal["failure", "success", "KeyboardInterrupt", "crash"],
        log_path: str = "",
        traceback_payload: dict[str, Any] | None = None,
        exit_msg: str | None = None,
        override_to_not_closing_and_disable_wait: bool = False,
    ) -> None:
        """Run completion side effects such as sounds and opening logs."""

        # get settings
        if mode == "success":
            play_sound = play_sound_after_success
            play_sound_default = DEFAULT_SOUND_AFTER_SUCCESS
            open_log = open_log_file_after_success
            terminal_colors = terminal_colors_after_success
            terminal_icon = SUCCESS_ICON_PATH
            terminal_title = title_after_success
            close = close_after_success
            open_main = open_main_py_after_success
        elif mode == "failure":
            play_sound = play_sound_after_failure
            play_sound_default = DEFAULT_SOUND_AFTER_FAILURE
            open_log = open_log_file_after_failure
            terminal_colors = terminal_colors_after_failure
            terminal_icon = FAILURE_ICON_PATH
            terminal_title = title_after_failure
            close = close_after_failure
            open_main = open_main_py_after_failure
        elif mode == "crash":
            play_sound = play_sound_after_crash
            play_sound_default = DEFAULT_SOUND_AFTER_CRASH
            open_log = open_log_file_after_crash
            terminal_colors = terminal_colors_after_crash
            terminal_icon = CRASH_ICON_PATH
            terminal_title = title_after_crash
            close = close_after_crash
            open_main = open_main_py_after_crash
        elif mode == "KeyboardInterrupt":
            play_sound = play_sound_after_KeyboardInterrupt
            play_sound_default = DEFAULT_SOUND_AFTER_KeyboardInterrupt
            open_log = open_log_file_after_KeyboardInterrupt
            terminal_colors = terminal_colors_after_KeyboardInterrupt
            terminal_icon = KEYBOARD_INTERRUPT_ICON_PATH
            terminal_title = title_after_KeyboardInterrupt
            close = close_after_KeyboardInterrupt
            open_main = open_main_py_after_KeyboardInterrupt

        # play sound
        if play_sound is True:
            wav_path = play_sound_default
        elif play_sound in (False, None, ""):
            wav_path = ""
        elif not os.path.isabs(play_sound):
            wav_path = os.path.normpath(WINDOWS_DIR + "\\Media\\" + play_sound)
        else:
            wav_path = play_sound
        if wav_path != "":
            if wav_path[-4:] != ".wav":
                wav_path += ".wav"

        def _play_exit_sound(wav_path: str, wait: bool = True) -> None:
            if not wav_path:
                return
            try:
                import winsound

                flags = winsound.SND_FILENAME | winsound.SND_NODEFAULT
                if not wait:
                    flags = flags | winsound.SND_ASYNC
                winsound.PlaySound(
                    wav_path,
                    flags,
                )
            except Exception as e:
                print(f"[Error] Failed to play .wav file: {e}")

        # open log
        if log_path and open_log:
            try:
                os.startfile(log_path)  # type: ignore[attr-defined]
            except Exception as e:
                print(f"[Error] Failed to open log: {e}")

        if open_main:
            open_in_editor(MAIN_PY_SCRIPT_PATH)

        # rest
        print(exit_msg)
        write_txt_crash_log(traceback_payload, exit_msg)

        if close == False or override_to_not_closing_and_disable_wait:
            set_terminal_title(terminal_title)
            set_terminal_colors(terminal_colors)
            set_terminal_icon(terminal_icon)
            print_traceback_from_json_payload(
                traceback_payload
            )  # must be after set_terminal_colors
            _play_exit_sound(
                wav_path, wait=not override_to_not_closing_and_disable_wait
            )
            if not override_to_not_closing_and_disable_wait:
                input("Press enter to exit")
        else:
            print_traceback_from_json_payload(traceback_payload)
            _play_exit_sound(wav_path)
            return

    # ==============================
    # main function
    # ==============================

    def main() -> None:
        # ==============================
        # handle args

        (
            _script_path,
            exit_mode,
            app_id,
            new_terminal_was_created,
            log_path_resolved,
            selected_python_script_path,
        ) = sys.argv
        exit_mode = int(exit_mode)
        new_terminal_was_created = new_terminal_was_created.lower() == "true"

        if new_terminal_was_created == True:
            set_terminal_app_id(app_id)

        # ==============================
        # process exit

        # exit_mode meaning:
        # 0 = correctly handled end of script in main.py (no json)
        # 1 = correctly handled other exit of main.py (json)
        # 2 = handled failure in wrapper of main.py (json)
        # 3 = unsuccessfully handled failure in wrapper of main.py (no json)
        # 4 = handled failure watchdog script (json)

        if exit_mode == 0:  # 0 = correctly handled end of script in main.py (no json)
            execute_exit_settings(
                "success",
                log_path_resolved,
                None,
                "[Success] Program finished successfully",
            )
            sys.exit()

        elif exit_mode == 1:  # 1 = correctly handled other exit of main.py (json)
            traceback_payload, traceback_error = load_traceback_payload()
            if traceback_payload is not None:
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
                        execute_exit_settings(
                            "success",
                            log_path_resolved,
                            traceback_payload,
                            "[Success] Program finished successfully",
                        )

                    elif exit_code_looks_like_interpreter_crash(main_exit_code):
                        execute_exit_settings(
                            "crash",
                            log_path_resolved,
                            traceback_payload,
                            f'[Crash] It appears like the Python interpreter crashed with exit code "{main_exit_code}" while running "{selected_python_script_path}".',
                        )

                    else:
                        execute_exit_settings(
                            "failure",
                            log_path_resolved,
                            traceback_payload,
                            f'[Failure] "{selected_python_script_path}" exited with error code "{main_exit_code}".',
                        )

                elif exception_type in ["ImportError", "ModuleNotFoundError"]:
                    missing_module = str(
                        traceback_entries[-1].get("missing_module") or ""
                    ).strip()
                    install_name = ""

                    if missing_module:
                        install_name = get_package_install_name(missing_module)

                        if install_name != missing_module:
                            exit_message = f'[Missing Package Error] "{selected_python_script_path}" could not import package "{missing_module}" (likely installed as "{install_name}") (see below).'
                        else:
                            exit_message = (
                                f'[Missing Package Error] "{selected_python_script_path}" could not import package '
                                f'"{missing_module}" (see below).'
                            )
                    else:  # can be for cases like "raise ImportError()"
                        exit_message = f'[Missing Package Error] "{selected_python_script_path}" could not import a package (see below).'

                    execute_exit_settings(
                        "failure",
                        log_path_resolved,
                        traceback_payload,
                        exit_message,
                        override_to_not_closing_and_disable_wait=True,
                    )
                    handle_missing_package_options(
                        missing_module,
                        install_name,
                        app_id,
                        new_terminal_was_created,
                    )

                elif exception_type == "SyntaxError":
                    execute_exit_settings(
                        "failure",
                        log_path_resolved,
                        traceback_payload,
                        f'[Failure] "{selected_python_script_path}" had a syntax error (see below).',
                    )

                elif exception_type == "KeyboardInterrupt":
                    execute_exit_settings(
                        "KeyboardInterrupt",
                        log_path_resolved,
                        traceback_payload,
                        f'[Failure] "{selected_python_script_path}" was interrupted by user with Ctrl+C',
                    )

                else:  # remaining exceptions cases
                    execute_exit_settings(
                        "failure",
                        log_path_resolved,
                        traceback_payload,
                        f'[Failure] "{selected_python_script_path}" had exception of type "{exception_type}" (see below).',
                    )

            else:
                execute_exit_settings(
                    "failure",
                    log_path_resolved,
                    None,
                    f'[Failure] "{selected_python_script_path}" failed, but its traceback could not be loaded. '
                    f"{traceback_error}",
                )

        elif exit_mode == 2:  # 2 = handled failure in wrapper of main.py (json)
            traceback_payload, traceback_error = load_traceback_payload()
            if traceback_payload is not None:
                traceback_entries = _traceback_entries(traceback_payload)
                exception_type = (
                    str(traceback_entries[-1].get("type") or "Exception")
                    if traceback_entries
                    else "Exception"
                )
                execute_exit_settings(
                    "failure",
                    log_path_resolved,
                    traceback_payload,
                    f'[Failure] The script wrapper failed with exception of type "{exception_type}" (see below).',
                )
            else:
                execute_exit_settings(
                    "failure",
                    log_path_resolved,
                    None,
                    f"[Failure] The script wrapper failed, but its traceback could not be loaded. {traceback_error}",
                )
        elif (
            exit_mode == 3
        ):  # 3 = unsuccessfully handled failure in wrapper of main.py (no json)
            # The wrapper's last-resort handler already displayed the traceback
            # and waited for acknowledgement. Avoid a second failure prompt.
            return
        elif exit_mode == 4:  # 4 = handled failure watchdog script (json)
            traceback_payload, traceback_error = load_traceback_payload()
            execute_exit_settings(
                "failure",
                log_path_resolved,
                traceback_payload,
                (
                    "[Failure] The background watchdog failed (see below)."
                    if traceback_payload is not None
                    else f"[Failure] The background watchdog failed, but its traceback could not be loaded. "
                    f"{traceback_error}"
                ),
            )
        else:
            mode = (
                "crash"
                if exit_code_looks_like_interpreter_crash(exit_mode)
                else "failure"
            )
            label = "Crash" if mode == "crash" else "Failure"
            execute_exit_settings(
                mode,
                log_path_resolved,
                None,
                f'[{label}] The script wrapper exited unexpectedly with status "{exit_mode}" while running '
                f'"{selected_python_script_path}".',
            )

    # ==============================
    # execute main function
    # ==============================

    if __name__ == "__main__":
        try:
            main()
        except Exception as e:
            print_traceback(fail_message.format(e=e))
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
    os._exit(
        1
    )  # instead of sys.exit(1) to prevent exception by script calling this script
