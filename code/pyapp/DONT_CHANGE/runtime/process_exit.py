"""Apply the configured completion behavior after the application (or the watchdog) ended.

Arguments: exit_mode app_id new_terminal_was_created log_path script_path
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path
from typing import Any, Dict, List, NoReturn, Optional, Tuple

fail_message = "Failed while processing program exit: {e}"


def _fail_while_loading(error: BaseException) -> NoReturn:
    """This window may be the only place the problem is visible: show it and wait."""
    import traceback

    print()
    print("ERROR  " + fail_message.format(e=error))
    print(traceback.format_exc())
    import contextlib

    # EOFError: started without a usable stdin (the watchdog's hidden run); nothing to wait for.
    with contextlib.suppress(EOFError, KeyboardInterrupt):
        input("Press Enter to close this window.")
    os._exit(1)


# Last, so app modules named like standard-library modules (code/random.py, ...) cannot shadow them.
sys.path.append(os.path.normpath(str((Path(__file__).parent / ".." / ".." / "..").absolute())))
try:
    from pyapp.DONT_CHANGE import backend_settings as paths
    from pyapp.DONT_CHANGE.runtime._pyapp import (
        ExitMode,
        exit_code_is_success,
        variable_dump,
    )
    from pyapp.DONT_CHANGE.scripts.config import main_script_path, settings
    from pyapp.DONT_CHANGE.scripts.console_tools import (
        ANSI_BOLD,
        ask,
        browser_terminal_ui,
        enable_ansi,
        foreground_terminal,
        in_browser_terminal,
        print_choices,
        print_error,
        print_info,
        print_success,
        print_warn,
        set_terminal_app_id,
        set_terminal_colors,
        set_terminal_icon,
        set_terminal_title,
        styled,
        unminimize_terminal,
        wait_for_enter,
    )
    from pyapp.DONT_CHANGE.scripts.diagnostics import note_ignored
    from pyapp.DONT_CHANGE.scripts.launcher_ui import (
        get_log_path,
        print_traceback,
    )
    from pyapp.DONT_CHANGE.scripts.runtime_state import (
        exit_code_looks_like_interpreter_crash,
        unique_log_path,
    )
    from pyapp.DONT_CHANGE.scripts.traceback_render import render, rule_line
except Exception as import_error:
    _fail_while_loading(import_error)

REPORT_PATH = str(Path(os.environ.get("PYAPP_RUN_DIR", paths.TEMPORARY_DIR)) / "traceback.json")

# Failures and Ctrl+C: black background (bright white text) so the colored traceback stays readable.
FAILURE_COLORS = "0F"

OUTCOMES = {
    "success": {
        "icon": paths.SUCCESS_ICON_PATH,
    },
    "failure": {
        "icon": paths.FAILURE_ICON_PATH,
    },
    # Ctrl+C shows the failure icon too and has no sound.
    "keyboard_interrupt": {
        "icon": paths.FAILURE_ICON_PATH,
    },
}

# ------------------------------------------------------------ reports


def load_report() -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Return (report, problem description)."""
    try:
        with Path(REPORT_PATH).open(encoding="utf-8") as stream:
            report = json.load(stream)
    except FileNotFoundError:
        return None, f'The traceback report was not created at "{REPORT_PATH}".'
    except (OSError, UnicodeError, ValueError) as error:
        return None, f'Could not read the traceback report "{REPORT_PATH}": {error}'
    if not isinstance(report, dict) or "chain" not in report:
        return None, f'The traceback report "{REPORT_PATH}" has an unknown format.'
    return report, None


def _report_style() -> Tuple[bool, int]:
    """(colors, width) for tracebacks in this window."""
    colors = sys.stdout is not None and sys.stdout.isatty()
    if colors:
        enable_ansi()
    return colors, max(40, min(120, shutil.get_terminal_size((100, 30)).columns - 1))


def error_summary(report: Dict[str, Any], limit: int = 200) -> str:
    """The last exception's own line, e.g. "ZeroDivisionError: division by zero" (shortened)."""
    chain = report.get("chain") or []
    lines = (chain[-1].get("exception_only") or []) if chain else []
    text = next((line for line in lines if line and not line.startswith(" ")), "") or str(
        report.get("exception_type") or "Exception"
    )
    return text if len(text) <= limit else text[: limit - 3] + "..."


def print_report(report: Optional[Dict[str, Any]]) -> None:
    if report:
        colors, width = _report_style()
        print("\n".join(render(report, colors=colors, date_format=settings().error_date_format, width=width)))


def append_printed_output(crash_log: str, log_path: Optional[str]) -> None:
    """Add what the app printed below the report, so that one file tells the whole story."""
    if not log_path or not Path(log_path).is_file():
        return  # logging is off for this kind of start, so the prints were not recorded
    title = os.linesep + "Everything the program printed before this (from the normal log):" + os.linesep * 2
    try:
        with Path(crash_log).open("ab") as target, Path(log_path).open("rb") as source:
            target.write(title.encode("utf-8"))
            shutil.copyfileobj(source, target)
    except OSError:
        note_ignored("append the printed output to the crash log")  # the report itself is already saved


def print_crash_log_path(path: str) -> None:
    """Show the saved filename, with an OSC 8 file link in Windows Terminal; other output stays plain."""
    target = Path(path).absolute()
    label = str(target)
    if os.environ.get("WT_SESSION") and sys.stdout is not None and sys.stdout.isatty() and not in_browser_terminal():
        enable_ansi()
        label = f"\x1b]8;;{target.as_uri()}\x1b\\{label}\x1b]8;;\x1b\\"
    # The browser terminal recognizes this labeled path and opens it through its local host.
    print(styled("Crash log:", ANSI_BOLD) + " " + label)


def write_crash_log(
    report: Optional[Dict[str, Any]], message: Optional[str], log_path: Optional[str] = None
) -> Optional[str]:
    """Write a uniquely named plain-text crash report and return its path (None if none was written)."""
    s = settings()
    if not s.enable_crash_log:
        return None
    path = get_log_path(s.crash_log_path, s.crash_log_path_is_relative_to_start_folder_if_relative)
    if not path or (report is None and message is None):
        return None
    path = unique_log_path(path, Path(os.environ.get("PYAPP_RUN_DIR", "")).name or None)
    lines: List[str] = ["=" * 30]
    if message:
        lines.append(message)
    if report:
        lines += render(report, colors=False, date_format=s.error_date_format)
    lines.append("=" * 30)
    (Path(path).parent).mkdir(parents=True, exist_ok=True)
    with Path(path).open("w", encoding="utf-8") as stream:
        stream.write("\n".join(lines) + "\n")
    append_printed_output(path, log_path)
    return path


# ------------------------------------------------------------ recovery


def restart_program(app_id: str, new_terminal_was_created: bool) -> None:
    """Start the program again with the same terminal behavior."""
    env = os.environ.copy()
    env["PYAPP_LAUNCH_MODE"] = "no_terminal" if new_terminal_was_created else "terminal"
    if env.get(paths.BROWSER_UI_ENV_VAR):  # started by the browser terminal shortcut: stay in the browser
        env["PYAPP_LAUNCH_MODE"] = "browser"
    # Run the launcher restart helper or open the configured local log file.
    subprocess.Popen(  # noqa: S603
        [
            sys.executable,
            "-I",
            "-S",
            "-X",
            "utf8",
            paths.ENTRYPOINT_PATH,
            paths.START_PROGRAM_PATH,
            app_id,
        ],
        env=env,
    )


def local_module_exists(name: str) -> bool:
    """True when the missing import is a module/package of the project itself (do not install)."""
    roots = (paths.PYTHON_SCRIPTS_DIR, str(Path(main_script_path()).parent))
    return any((Path(root) / (name + ".py")).is_file() or (Path(root) / name).is_dir() for root in roots)


def save_and_open_variables(report: Dict[str, Any], crash_log: Optional[str] = None) -> None:
    """Persist values only on request, preferably in the crash log, and open the resulting text file."""
    if not report.get("variables"):
        print_info("No Python traceback variables are available for this error.")
        return
    try:
        saved = report.get("variables_saved_path")
        # Without crash logging, use system temp rather than the launcher's short-lived run folder.
        destination = Path(
            saved or crash_log or str(Path(tempfile.gettempdir()) / f"pyapp-variables-{uuid.uuid4().hex}.txt")
        )
        if not saved or not destination.is_file():
            destination.parent.mkdir(parents=True, exist_ok=True)
            with destination.open("a" if crash_log else "w", encoding="utf-8", errors="backslashreplace") as stream:
                stream.write("\n\n" + variable_dump(report))
            report["variables_saved_path"] = str(destination)
        print_info("Variables saved: " + destination.resolve().as_uri())
    except OSError as error:
        print_error(f"Could not save the variable snapshot: {error}")
        return
    try:
        os.startfile(str(destination))  # noqa: S606 - explicitly requested local diagnostic text file
    except OSError as error:
        print_error(f"The snapshot was saved, but could not be opened: {error}")


def wait_for_report(report: Optional[Dict[str, Any]], crash_log: Optional[str] = None) -> None:
    """Keep the normal Enter-to-close behavior, adding an optional variable export for tracebacks."""
    if not report or not report.get("variables"):
        wait_for_enter()
        return
    while True:
        try:
            answer = (
                ask("Enter = close, v = save all traceback locals/globals and open (values are not redacted):")
                .strip()
                .lower()
            )
        except (EOFError, KeyboardInterrupt):
            return
        if not answer or answer in ("q", "n"):
            return
        if answer == "v":
            save_and_open_variables(report, crash_log)


def handle_missing_module(
    missing: str,
    app_id: str,
    new_terminal_was_created: bool,
    report: Optional[Dict[str, Any]] = None,
    crash_log: Optional[str] = None,
) -> None:
    """Offer to install the distribution behind a ModuleNotFoundError, then restart."""
    from pyapp.DONT_CHANGE.scripts.env import venv
    from pyapp.DONT_CHANGE.scripts.errors import SetupError
    from pyapp.DONT_CHANGE.scripts.import_finder import distribution_for_import

    top = missing.split(".", maxsplit=1)[0]
    if local_module_exists(top):
        print_warn(
            f'"{top}" is part of your project, not a package to install. Check the file/folder name and the import.'
        )
        wait_for_report(report, crash_log)
        return
    distribution = distribution_for_import(top)
    if distribution != top:
        print_info(f'The import "{top}" is provided by the package "{distribution}".')
    # Asked before the menu: a package that cannot be installed here gets one plain sentence
    # instead of an "Add" choice that ends in uv's long resolver error. Offline or with an unclear
    # answer this is None and the menu offers everything.
    try:
        problem = venv.install_problem(distribution)
    except Exception:
        note_ignored("checking whether the missing package can be installed")
        problem = None
    if problem:
        advice = (
            "Check the import in your code."
            if problem.startswith("there is no package")
            else "Use another package (often a newer major version of it) or an older python_version."
        )
        headline = f'"{distribution}" is not installed and cannot be: {problem}\n{advice}'
        options: List[Tuple[str, str]] = []
    else:
        headline = f'The package for "{top}" is not installed.'
        options = [
            ("add", f'Add "{distribution}" to the packages in developer_settings.py and restart'),
            ("install", f'Install "{distribution}" without recording it and restart'),
        ]
    options += [
        ("find", "Find all imports of the project, review them, add the missing ones and restart"),
        ("terminal", "Open a package terminal, then restart"),
        ("quit", "Quit"),
    ]
    first_round = True
    while True:
        print()
        if not first_round:
            # After a failed choice: separates its output (uv's error) from the menu shown again.
            colors, width = _report_style()
            print(rule_line(width, colors))
            print()
        first_round = False
        print_warn(headline)
        print_choices(label for _, label in options)
        # Enter: the last option, quit.
        variables_hint = ", v = save/open variables" if report and report.get("variables") else ""
        answer = ask(f"What now? [1-{len(options)}, Enter = quit{variables_hint}]").strip() or str(len(options))
        if answer.lower() == "v" and report and report.get("variables"):
            save_and_open_variables(report, crash_log)
            continue
        if not answer.isdecimal() or not 1 <= int(answer) <= len(options):
            continue
        action = options[int(answer) - 1][0]
        if action == "quit":
            return
        # Separates the menu from the output of what was chosen (uv, the import finder, ...).
        colors, width = _report_style()
        print(rule_line(width, colors))
        try:
            if action == "add":
                venv.add_packages([distribution])
            elif action == "install":
                venv.install_without_recording([distribution], paths.VENV_PYTHON_EXE)
            elif action == "find":
                from pyapp.DONT_CHANGE.scripts.dev_tools.packages import (
                    find_imports_and_add,
                )

                find_imports_and_add()
            else:
                venv.open_package_terminal()
        except SetupError as error:
            # An expected failure (e.g. a version conflict with other packages): uv has already
            # printed why, so a launcher traceback would only bury that reason.
            print()
            print_error(f"{error}\nuv's message above says why.")
            continue
        except Exception as error:
            print_traceback(f"Package recovery failed: {error}")
            continue
        print_success("Restarting the program ...")
        restart_program(app_id, new_terminal_was_created)
        return


# ------------------------------------------------------------ completion


def play_sound(wav: str, wait: bool = True) -> None:
    try:
        import winsound

        flags = winsound.SND_FILENAME | winsound.SND_NODEFAULT | (0 if wait else winsound.SND_ASYNC)
        winsound.PlaySound(wav, flags)
    except Exception as error:
        print_error(f"Failed to play .wav file: {error}")


def complete(
    outcome: str,
    log_path: Optional[str],
    report: Optional[Dict[str, Any]] = None,
    message: Optional[str] = None,
    keep_open: bool = False,
) -> Optional[str]:
    """Run the configured actions for success/failure/crash/keyboard_interrupt."""
    s = settings()
    close = getattr(s, "close_after_" + outcome)
    if log_path and getattr(s, "open_log_file_after_" + outcome):
        try:
            # Run the launcher restart helper or open the configured local log file.
            os.startfile(log_path)  # noqa: S606
        except Exception as error:
            print_error(f"Failed to open log: {error}")
    stays_open = close is False or keep_open
    if stays_open or in_browser_terminal():
        # First: changing the window colors repaints everything already printed.
        set_terminal_title(getattr(s, "title_after_" + outcome))
        if stays_open and outcome in ("failure", "keyboard_interrupt"):  # both show a traceback
            set_terminal_colors(FAILURE_COLORS)
        set_terminal_icon(OUTCOMES[outcome]["icon"])
    if message and in_browser_terminal():
        # A desktop notification in the browser terminal, if switched on there.
        browser_terminal_ui(notify=message, failed=outcome != "success", status=outcome)
    if message:
        print()
        if outcome != "success":
            colors, width = _report_style()
            print(rule_line(width, colors))
        {"success": print_success, "keyboard_interrupt": print_warn}.get(outcome, print_error)(message)
    # The report first: it is what this window is for, and writing the crash log can fail
    # (missing drive, full disk, a date code that makes an invalid file name).
    print_report(report)
    crash_log = None
    if outcome != "success":
        try:
            crash_log = write_crash_log(report, message, log_path)
        except OSError as error:
            print_error(f"Failed to write the crash log: {error}")
            crash_log = None
        if crash_log:
            print_crash_log_path(crash_log)
        if crash_log and outcome == "failure" and s.open_crash_log_after_failure:
            try:
                # Run the launcher restart helper or open the configured local log file.
                os.startfile(crash_log)  # noqa: S606
            except Exception as error:
                print_error(f"Failed to open crash log: {error}")
    if outcome in ("success", "failure") and getattr(s, "play_sound_after_" + outcome):
        wav = getattr(s, "sound_after_" + outcome)
        if wav:
            from pyapp.DONT_CHANGE.scripts.file_tools import make_abs_path_relative_to_file

            play_sound(
                make_abs_path_relative_to_file(os.path.expandvars(wav), paths.DEV_SETTINGS_PATH), wait=not keep_open
            )
    from pyapp.DONT_CHANGE.scripts import taskbar_status, windows_notifications

    windows_notifications.complete(s, outcome, message, log_path, crash_log)
    if stays_open and outcome in ("success", "failure") and getattr(s, "foreground_after_" + outcome, False):
        try:
            if in_browser_terminal():
                browser_terminal_ui(foreground=True)
            else:
                unminimize_terminal()
                foreground_terminal()
        except Exception:
            # Attention is cosmetic; reporting and recovery must still run if Windows denies it.
            note_ignored("foreground after " + outcome)
    taskbar_status.finish(s, outcome, stays_open)
    if stays_open and not keep_open:
        wait_for_report(report, crash_log)
    return crash_log


def main() -> None:
    settings()  # a broken settings file fails here, first; later calls reuse the import
    _, exit_mode, app_id, new_terminal_was_created, log_path, script_path = sys.argv
    exit_mode = int(exit_mode)
    new_terminal_was_created = new_terminal_was_created.lower() == "true"
    suffix = (
        paths.BROWSER_APP_ID_SUFFIX
        if in_browser_terminal()
        else (paths.NO_TERMINAL_APP_ID_SUFFIX if new_terminal_was_created else "")
    )
    os.environ["PYAPP_NOTIFICATION_APP_ID"] = app_id + suffix if app_id else ""
    script_name = Path(script_path).name
    recovery_notice = os.environ.get("PYAPP_CRASH_RECOVERY_NOTICE", "")
    if recovery_notice:
        print_info(recovery_notice)
    if new_terminal_was_created and app_id:
        # Started by the "(no Terminal)" shortcut: group this window with that shortcut.
        set_terminal_app_id(app_id + paths.NO_TERMINAL_APP_ID_SUFFIX)

    if "PYAPP_UNEXPECTED_EXIT" in os.environ:
        native = int(os.environ["PYAPP_UNEXPECTED_EXIT"])
        crashed = exit_code_looks_like_interpreter_crash(native)
        hint = " See the .output.log next to the log file for the interpreter's last output." if log_path else ""
        complete(
            "failure",
            log_path,
            None,
            f'"{script_name}" {"crashed" if crashed else "ended unexpectedly"} without a completion report (exit status {native}, 0x{native & 0xFFFFFFFF:08X}).{hint}',
        )
        return

    if exit_mode == ExitMode.SUCCESS:
        complete("success", log_path, None, f'"{script_name}" finished successfully.')
        return

    report, problem = load_report()
    if exit_mode == ExitMode.WATCHDOG_ERROR:
        complete(
            "failure",
            log_path,
            report,
            "The launcher's background watchdog failed (see below)." + ("" if report else f" {problem}"),
        )
        return
    if exit_mode == ExitMode.WRAPPER_ERROR:
        complete(
            "failure",
            log_path,
            report,
            "The launcher's script wrapper failed (see below)." + ("" if report else f" {problem}"),
        )
        return
    if exit_mode != ExitMode.APP_EXIT:
        raise ValueError(f"Unknown exit mode {exit_mode} from the watchdog.")
    if report is None:
        complete(
            "failure",
            log_path,
            None,
            f'"{script_name}" failed, but its traceback could not be loaded. {problem}',
        )
        return

    kind = report.get("exception_type") or "Exception"
    if kind == "SystemExit":
        code = report.get("system_exit_code")
        if exit_code_is_success(code):
            complete("success", log_path, None, f'"{script_name}" finished successfully.')
        elif exit_code_looks_like_interpreter_crash(code):
            complete(
                "failure",
                log_path,
                report,
                f'The Python interpreter crashed while running "{script_name}" (exit code {code}).',
            )
        else:
            complete(
                "failure",
                log_path,
                report,
                f'"{script_name}" exited with error code {code}.',
            )
    elif kind == "ModuleNotFoundError" and report.get("missing_module"):
        missing = report["missing_module"]
        crash_log = complete(
            "failure",
            log_path,
            report,
            f'"{script_name}" failed: {error_summary(report)}',
            keep_open=True,
        )
        handle_missing_module(missing, app_id, new_terminal_was_created, report, crash_log)
    elif kind == "KeyboardInterrupt":
        complete(
            "keyboard_interrupt",
            log_path,
            report,
            f'"{script_name}" was stopped with Ctrl+C.',
        )
    else:
        # SyntaxError and every other exception: the error itself on the first line.
        complete("failure", log_path, report, f'"{script_name}" failed: {error_summary(report)}')


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print_traceback(fail_message.format(e=error))
        wait_for_enter()
        sys.exit(1)
    sys.exit(0)
