# ruff: noqa: UP032

"""WIP

This script must be compatible for Python 3.5+:
- No function, argument, variable, or class attribute annotations
- No "from __future__ import annotations"
- No f-strings, including rf/fr strings
- No modern typing syntax such as list[str] or str | None
- No dataclasses
- No walrus operator :=
- No positional-only parameter marker /
- No async generators or async comprehensions
- No underscores in numeric literals
- No pathlib/os.PathLike-only APIs; keep accepting plain strings
- No subprocess.run(..., capture_output=True) or text=True
- No breakpoint()
- No .astimezone() for datetime
"""

# {e} will be formatted to exception:
fail_message = "[Error] Failed during wrapper start: {e}"

try:
    # ==============================
    # import Python packages
    # ==============================

    import os
    import runpy
    import sys
    import traceback
    from datetime import datetime

    # ==============================
    # define local variables
    # ==============================

    crash_log_temp_path = None
    log_file = None

    # ==============================
    # define local functions/classes
    # ==============================

    # ==============================
    # logging related

    def _normalize_strftime_format(fmt):
        """Accept strftime formats whose directives were percent-escaped upstream."""
        # fmt: off
        replacements = ("a", "A", "w", "d", "b", "B", "m", "y", "Y", "H", "I", "p", "M", "S", "f", "z", "Z", "j", "U", "W", "c", "x", "X", "G", "u", "V")
        # fmt: on
        for directive in replacements:
            fmt = fmt.replace("%%" + directive, "%" + directive)
        return fmt

    def _format_prepend(fmt):
        if not fmt:
            return ""

        return datetime.now().strftime(_normalize_strftime_format(fmt))  # noqa:DTZ005

    class pipe_splitter:
        """
        Mirror text output to a console stream and an optional log stream, with:
        - separate optional timestamp formats for console and log
        - optional red coloring for console error output only
        - line-aware prefixing so timestamps appear once per line

        Timestamp behavior:
        - if print_timestamp_format is "", None, or False -> no console timestamp
        - if log_timestamp_format is "", None, or False -> no log timestamp

        Example:
            import atexit
            import sys

            log_file = open("app.log", "w", encoding="utf-8", buffering=1)
            atexit.register(log_file.close)

            sys.stdout = pipe_splitter(
                print_stream=sys.__stdout__,
                log_stream=log_file,
                print_timestamp_format="%H:%M:%S",
                log_timestamp_format="%Y-%m-%d %H:%M:%S",
                print_red=False,
            )

            sys.stderr = pipe_splitter(
                print_stream=sys.__stderr__,
                log_stream=log_file,
                print_timestamp_format="%H:%M:%S",
                log_timestamp_format="%Y-%m-%d %H:%M:%S",
                print_red=True,
            )
        """

        def __init__(
            self,
            print_stream,  # TextIO object
            log_stream=None,  # TextIO object or None
            print_timestamp_format="[%H:%M:%S] ",
            log_timestamp_format="[%H:%M:%S]\t",
            input_timestamp_format="",
            log_input_timestamp_format="",
            print_red=False,
            auto_flush=True,
        ):
            self.print_stream = print_stream
            self.log_stream = log_stream
            self.print_timestamp_format = print_timestamp_format
            self.log_timestamp_format = log_timestamp_format
            self.input_timestamp_format = input_timestamp_format
            self.log_input_timestamp_format = log_input_timestamp_format
            self.print_red = print_red
            self.auto_flush = auto_flush

            self._at_line_start = True
            self._lock = threading.RLock()  # needed if multiple threads want to print at same time #type:ignore

            self.ANSI_escape_re = re.compile(  # type:ignore
                r"\x1b(?:"
                r"\[[0-?]*[ -/]*[@-~]"
                r"|\][^\x07]*(?:\x07|\x1b\\)"
                r"|[@-Z\\-_]"
                r")"
            )

        def _strip_ansi_escape_sequences(self, text):
            """Remove terminal ANSI escape sequences from text."""
            return self.ANSI_escape_re.sub("", text)

        def _timestamp_prefix(self, fmt):
            return _format_prepend(fmt)

        def _print_supports_color(self):
            return bool(getattr(self.print_stream, "isatty", lambda: False)())

        def write(self, data):
            if data is None:
                data = ""
            if not isinstance(data, str):
                data = str(data)
            if data == "":
                return 0

            with self._lock:
                parts = data.splitlines(keepends=True)
                if not parts:
                    parts = [data]

                for part in parts:
                    if self._at_line_start:
                        print_prefix = self._timestamp_prefix(self.print_timestamp_format)
                        log_prefix = self._timestamp_prefix(self.log_timestamp_format)

                        if print_prefix:
                            self.print_stream.write(print_prefix)
                        if self.log_stream is not None and log_prefix:
                            self.log_stream.write(log_prefix)

                        if self.print_red and self._print_supports_color():
                            self.print_stream.write("\x1b[31m")  # ANSI red

                    self.print_stream.write(part)
                    if self.log_stream is not None:
                        self.log_stream.write(self._strip_ansi_escape_sequences(part))

                    if part.endswith("\n"):
                        if self.print_red and self._print_supports_color():
                            self.print_stream.write("\x1b[0m")  # ANSI reset
                        self._at_line_start = True
                    else:
                        self._at_line_start = False

                if self.auto_flush:
                    self.flush()

            return len(data)

        def write_input_prompt(self, prompt):
            """Write the input prompt."""
            if prompt is None:
                prompt = ""
            if not isinstance(prompt, str):
                prompt = str(prompt)

            with self._lock:
                print_prefix = self._timestamp_prefix(self.input_timestamp_format)
                log_prefix = self._timestamp_prefix(self.log_input_timestamp_format)

                self.print_stream.write("{}{}".format(print_prefix, prompt))
                if self.log_stream is not None:
                    self.log_stream.write("{}{}".format(log_prefix, self._strip_ansi_escape_sequences(prompt)))

                self._at_line_start = prompt.endswith("\n")
                if self.auto_flush:
                    self.flush()

        def complete_input_line(self, text):
            """Finish logging a user input line."""
            with self._lock:
                if self.log_stream is not None and not self._at_line_start:
                    self.log_stream.write("{}\n".format(text))
                self._at_line_start = True
                if self.auto_flush:
                    self.flush()

        def flush(self):
            with self._lock:
                if hasattr(self.print_stream, "flush"):
                    self.print_stream.flush()
                if self.log_stream is not None and hasattr(self.log_stream, "flush"):
                    self.log_stream.flush()

        def isatty(self):
            return bool(getattr(self.print_stream, "isatty", lambda: False)())

        def writable(self):
            return True

        def fileno(self):
            if hasattr(self.print_stream, "fileno"):
                return self.print_stream.fileno()
            raise OSError("Underlying print_stream does not support fileno()")

        @property
        def encoding(self):
            return getattr(self.print_stream, "encoding", None)

    def setup_log_prints(
        log_path,
        overwrite_log=True,
        print_prepend="",
        log_print_prepend="",
        input_prepend="",
        log_input_prepend="",
    ):
        """Install stdout, stderr, and input wrappers for logging."""
        import atexit
        import faulthandler

        global log_file, re, threading  # type:ignore
        import re
        import threading

        log_file = None
        if log_path:
            log_folder = os.path.dirname(log_path)
            if log_folder:
                os.makedirs(log_folder, exist_ok=True)
            log_file = open(log_path, "w" if overwrite_log else "a", encoding="utf-8", buffering=1)  # noqa:SIM115
            atexit.register(log_file.close)
        sys.stdout = pipe_splitter(
            sys.__stdout__,
            log_file,
            print_timestamp_format=print_prepend,
            log_timestamp_format=log_print_prepend,
            input_timestamp_format=input_prepend,
            log_input_timestamp_format=log_input_prepend,
        )
        sys.stderr = pipe_splitter(
            sys.__stderr__,
            log_file,
            print_timestamp_format=print_prepend,
            log_timestamp_format=log_print_prepend,
            input_timestamp_format=input_prepend,
            log_input_timestamp_format=log_input_prepend,
            print_red=True,
        )
        if log_file is not None and faulthandler.is_enabled():
            faulthandler.enable(file=log_file, all_threads=True)

    # ==============================
    # traceback related

    def _traceback_snapshot_error(error, relation_text=""):
        """Serialize exception data so backend Python can render it without rerunning the child."""
        frames = [
            {
                "filename": frame.filename,
                "lineno": frame.lineno,
                "function": frame.name,
                "source": frame.line or "",
            }
            for frame in traceback.extract_tb(error.__traceback__)
        ]

        syntax = None
        if isinstance(error, SyntaxError) and any(
            getattr(error, attribute, None) is not None for attribute in ("filename", "lineno", "offset", "text")
        ):
            syntax = {
                "filename": getattr(error, "filename", None),
                "lineno": getattr(error, "lineno", None),
                "offset": getattr(error, "offset", None),
                "text": getattr(error, "text", None),
            }

        return {
            "relation": relation_text,
            "type": type(error).__name__,
            "message": str(error),
            "missing_module": getattr(error, "name", None) if isinstance(error, ImportError) else None,
            "frames": frames,
            "syntax": syntax,
        }

    def _traceback_snapshot_chain(error):
        """Serialize an exception chain in normal display order."""
        snapshots = []
        seen = set()

        def _add(current_error):
            if id(current_error) in seen:
                return
            seen.add(id(current_error))

            cause = getattr(current_error, "__cause__", None)
            context = getattr(current_error, "__context__", None)
            suppress_context = getattr(current_error, "__suppress_context__", False)

            if cause is not None:
                _add(cause)
                relation_text = "The above exception was the direct cause of the following exception:"
            elif context is not None and not suppress_context:
                _add(context)
                relation_text = "During handling of the above exception, another exception occurred:"
            else:
                relation_text = ""

            snapshots.append(_traceback_snapshot_error(current_error, relation_text))

        _add(error)
        return snapshots

    def save_traceback(error, excepted_script_path, output_path):
        import json

        def _get_system_exit_code_for_json(error):
            """Return SystemExit.code in a form json.dump can always serialize."""
            if not isinstance(error, SystemExit):
                return None

            exit_code = error.code
            if exit_code is None or isinstance(exit_code, (bool, int, float, str)):
                return exit_code
            return repr(exit_code)

        payload = {
            "script_path": excepted_script_path,
            "python_version": sys.version.split()[0],
            "system_exit_code": _get_system_exit_code_for_json(error),
            "traceback": _traceback_snapshot_chain(error),
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(payload, f)

    # ==============================
    # miscellaneous

    def string_to_bool(string):
        """Convert a string to a boolean value, interpreting "true" (case-insensitive) as True, "false" (case-insensitive) as False, and raising ValueError for other inputs."""

        lowered = string.lower()
        if lowered == "true":
            return True
        elif lowered == "false":
            return False
        else:
            message = "Cannot convert string to bool: {!r}".format(string)
            raise ValueError(message)

    def process_args(args):
        """Process the command-line arguments: The second element in the input is used as the empty argument indicator, and all occurrences of it in the arguments list are replaced with empty strings in the output list. The first element of the input is typically the script name and is included unchanged in the output."""

        EMPTY_ARG_INDICATOR = args[1]  # args[0] is script name
        out = []

        for elem in args:
            if elem == EMPTY_ARG_INDICATOR:
                out.append("")
            else:
                out.append(elem)

        return out

    # ==============================
    # define main function
    # ==============================

    def main():
        global crash_log_temp_path

        # ==============================
        # import and convert args

        (
            _script_name,
            _EMPTY_ARG_INDICATOR,
            python_script_path,
            app_id,
            print_prepend,
            input_prepend,
            log_input_prepend,
            log_path,
            overwrite_log,
            log_print_prepend,
            crash_log_temp_path,
        ) = process_args(sys.argv)

        overwrite_log = string_to_bool(overwrite_log)

        # ==============================

        # setup print/input prefixing and optional logging:
        should_setup_prints = (
            log_path != ""
            or print_prepend != ""
            or log_print_prepend != ""
            or input_prepend != ""
            or log_input_prepend != ""
        )
        if should_setup_prints:
            setup_log_prints(
                log_path, overwrite_log, print_prepend, log_print_prepend, input_prepend, log_input_prepend
            )

        # ==============================
        # app-id change needed in case main script spawns a GUI: For taskbar grouping (combining) of launched window into taskbar-pinned shortcut:

        if app_id:
            import ctypes

            try:
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)  # type:ignore
            except Exception as e:
                print("[Warning] Failed to set app id for taskbar grouping: {}".format(e))

        # ==============================
        # replace pythons builtin "input" function to add a prepend:
        # (pipe can't do that since input() is not going via that)

        if input_prepend != "" or log_input_prepend != "" or hasattr(sys.stdout, "complete_input_line"):
            import builtins

            _original_input = builtins.input

            def _input_with_prepend(prompt=""):
                """Prompt for input while applying console and log prefixes."""
                if hasattr(sys.stdout, "write_input_prompt"):
                    sys.stdout.write_input_prompt(prompt)
                    text = _original_input("")
                else:
                    text = _original_input("{}{}".format(_format_prepend(input_prepend), prompt))
                if hasattr(sys.stdout, "complete_input_line"):
                    sys.stdout.complete_input_line(text)
                return text

            builtins.input = _input_with_prepend

        # ==============================
        # change sys.path[0] to be dir of target script and not this script:

        sys.path[0] = os.path.dirname(python_script_path)

        # ==============================
        # run in the current python process and wait for finish

        try:
            runpy.run_path(python_script_path, run_name="__main__")

        except BaseException as e:  # BaseException includes KeyboardInterrupt,GeneratorExit,normal Exception, SystemExit (including success exit)
            save_traceback(e, python_script_path, crash_log_temp_path)
            sys.exit(
                1
            )  # exit code 1 indicates child script error need to process saved traceback to watchdog and correct handling

    # ==============================
    # execute main function
    # ==============================

    if __name__ == "__main__":
        try:
            main()
        except Exception as e:
            save_traceback(e, os.path.abspath(__file__), crash_log_temp_path)
            sys.exit(2)  # exit code 2 indicates wrapper error and need to process saved traceback to watchdog
        finally:  # try close log file
            try:
                sys.stdout.flush()
                sys.stderr.flush()
                sys.stdout = sys.__stdout__
                sys.stderr = sys.__stderr__
                log_file.close()  # type:ignore
            except Exception:
                pass

    # =============================

except Exception as e:  # fallback exception handling
    import subprocess
    import sys
    import traceback

    # print error in new terminal in case this program does not have a terminal:
    error_text = (
        "=" * 60
        + "\n[Error] Failed in wrapper script with error: "
        + "{}: {}\n".format(type(e).__name__, e)
        + "-" * 60
        + "\n"
        + traceback.format_exc()
        + "=" * 60
    )
    display_code = """
import sys

print(sys.argv[1])
input("\\nPress Enter to exit...")
"""
    subprocess.Popen(  # noqa:S603
        [sys.executable, "-c", display_code, error_text],
        creationflags=subprocess.CREATE_NEW_CONSOLE,
    )

    # print and wait in case this program has a terminal:
    print("=" * 20)
    print("[Error] Failed in wrapper script with error: {}:".format(e))
    print("-" * 20)
    print(traceback.format_exc())
    print("=" * 20)
    input("Press enter to exit")

    # tell watchdog script with error code 3 that fallback exception handling occured and that watchdog should close because input("Press enter to exit") is already here:
    sys.exit(3)
