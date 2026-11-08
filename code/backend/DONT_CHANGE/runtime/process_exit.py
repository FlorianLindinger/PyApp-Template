"""Apply the configured completion behavior after the application (or the watchdog) ended.

Arguments: exit_mode app_id new_terminal_was_created log_path script_path
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, NoReturn, Optional

fail_message = "Failed while processing program exit: {e}"


def _fail_while_loading(error: BaseException) -> NoReturn:
    """This window may be the only place the problem is visible: show it and wait."""
    import traceback

    print()
    print("ERROR  " + fail_message.format(e=error))
    print(traceback.format_exc())
    input("Press Enter to close this window.")
    os._exit(1)


sys.path.insert(0, os.path.normpath(str((Path(__file__).parent / ".." / ".." / "..").absolute())))
try:
    from backend.DONT_CHANGE import backend_settings as paths
    from backend.DONT_CHANGE.runtime._pyapp import (
        ExitMode,
        exit_code_is_success,
    )
    from backend.DONT_CHANGE.scripts.config import main_script_path, settings
    from backend.DONT_CHANGE.scripts.console_tools import (
        ask,
        enable_ansi,
        print_choices,
        print_error,
        print_info,
        print_success,
        print_warn,
        set_terminal_app_id,
        set_terminal_colors,
        set_terminal_icon,
        set_terminal_title,
        wait_for_enter,
    )
    from backend.DONT_CHANGE.scripts.launcher_ui import (
        get_log_path,
        print_traceback,
    )
    from backend.DONT_CHANGE.scripts.runtime_state import (
        exit_code_looks_like_interpreter_crash,
        unique_log_path,
    )
    from backend.DONT_CHANGE.scripts.traceback_render import render, rule_line
except Exception as import_error:
    _fail_while_loading(import_error)

REPORT_PATH = str(Path(os.environ.get("PYAPP_RUN_DIR", paths.TEMPORARY_DIR)) / "traceback.json")

# Failures: black background (bright white text) so the colored traceback stays readable.
FAILURE_COLORS = "0F"

OUTCOMES = {
    "success": {
        "icon": paths.SUCCESS_ICON_PATH,
        "sound": paths.DEFAULT_SOUND_AFTER_SUCCESS,
        "title": paths.TITLE_AFTER_SUCCESS,
    },
    "failure": {
        "icon": paths.FAILURE_ICON_PATH,
        "sound": paths.DEFAULT_SOUND_AFTER_FAILURE,
        "title": paths.TITLE_AFTER_FAILURE,
    },
    # Ctrl+C shows the failure icon too and has no sound.
    "keyboard_interrupt": {
        "icon": paths.FAILURE_ICON_PATH,
        "sound": "",
        "title": paths.TITLE_AFTER_KEYBOARD_INTERRUPT,
    },
}

# ------------------------------------------------------------ reports


def load_report():
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


def _report_style():
    """(colors, width) for tracebacks in this window."""
    colors = sys.stdout is not None and sys.stdout.isatty()
    if colors:
        enable_ansi()
    return colors, max(40, min(120, shutil.get_terminal_size((100, 30)).columns - 1))


def error_summary(report: Dict[str, Any], limit: int = 200):
    """The last exception's own line, e.g. "ZeroDivisionError: division by zero" (shortened)."""
    chain = report.get("chain") or []
    lines = (chain[-1].get("exception_only") or []) if chain else []
    text = next((line for line in lines if line and not line.startswith(" ")), "") or str(
        report.get("exception_type") or "Exception"
    )
    return text if len(text) <= limit else text[: limit - 3] + "..."


def print_report(report: Optional[Dict[str, Any]]):
    if report:
        colors, width = _report_style()
        print("\n".join(render(report, colors=colors, date_format=settings().error_date_format, width=width)))


def write_crash_log(report: Optional[Dict[str, Any]], message: Optional[str]):
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
    return path


# ------------------------------------------------------------ recovery


def restart_program(app_id: str, new_terminal_was_created: bool):
    """Start the program again with the same terminal behavior."""
    env = os.environ.copy()
    env["PYAPP_LAUNCH_MODE"] = "no_terminal" if new_terminal_was_created else "terminal"
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


def local_module_exists(name: str):
    """True when the missing import is a module/package of the project itself (do not install)."""
    roots = (paths.PYTHON_SCRIPTS_DIR, str(Path(main_script_path()).parent))
    return any((Path(root) / (name + ".py")).is_file() or (Path(root) / name).is_dir() for root in roots)


def handle_missing_module(missing: str, app_id: str, new_terminal_was_created: bool):
    """Offer to install the distribution behind a ModuleNotFoundError, then restart."""
    from backend.DONT_CHANGE.scripts.env import venv
    from backend.DONT_CHANGE.scripts.import_finder import distribution_for_import

    top = missing.split(".")[0]
    if local_module_exists(top):
        print_warn(
            f'"{top}" is part of your project, not a package to install. Check the file/folder name and the import.'
        )
        wait_for_enter()
        return
    distribution = distribution_for_import(top)
    if distribution != top:
        print_info(f'The import "{top}" is provided by the package "{distribution}".')
    options = [
        ("add", f'Add "{distribution}" to the packages in developer_settings.py and restart'),
        ("install", f'Install "{distribution}" without recording it and restart'),
        ("find", "Find all imports of the project, review them, add the missing ones and restart"),
        ("terminal", "Open a package terminal, then restart"),
        ("quit", "Quit"),
    ]
    while True:
        print()
        print_warn(f'The package for "{top}" is not installed.')
        print_choices(label for _, label in options)
        answer = ask(f"What now? [1-{len(options)}]").strip()
        if not answer.isdigit() or not 1 <= int(answer) <= len(options):
            continue
        action = options[int(answer) - 1][0]
        if action == "quit":
            return
        try:
            if action == "add":
                venv.add_packages([distribution])
            elif action == "install":
                venv.install_without_recording([distribution], paths.VENV_PYTHON_EXE)
            elif action == "find":
                from backend.DONT_CHANGE.scripts.dev.packages import (
                    find_imports_and_add,
                )

                find_imports_and_add()
            else:
                venv.open_package_terminal()
        except Exception as error:
            print_traceback(f"Package recovery failed: {error}")
            continue
        print_success("Restarting the program ...")
        restart_program(app_id, new_terminal_was_created)
        return


# ------------------------------------------------------------ completion


def play_sound(wav: str, wait: bool = True):
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
):
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
    if stays_open:
        # First: changing the window colors repaints everything already printed.
        set_terminal_title(OUTCOMES[outcome]["title"].format(program_name=s.program_name))
        if outcome == "failure":
            set_terminal_colors(FAILURE_COLORS)
        set_terminal_icon(OUTCOMES[outcome]["icon"])
    if message:
        print()
        if outcome != "success":
            colors, width = _report_style()
            print(rule_line(width, colors))
        {"success": print_success, "keyboard_interrupt": print_warn}.get(outcome, print_error)(message)
    if outcome != "success":
        crash_log = write_crash_log(report, message)
        if crash_log and outcome == "failure" and s.open_crash_log_after_failure:
            try:
                # Run the launcher restart helper or open the configured local log file.
                os.startfile(crash_log)  # noqa: S606
            except Exception as error:
                print_error(f"Failed to open crash log: {error}")
    print_report(report)
    if OUTCOMES[outcome]["sound"] and getattr(s, "play_sound_after_" + outcome):
        play_sound(OUTCOMES[outcome]["sound"], wait=not keep_open)
    if stays_open and not keep_open:
        wait_for_enter()


def main():
    settings()  # a broken settings file fails here, first; later calls reuse the import
    _, exit_mode, app_id, new_terminal_was_created, log_path, script_path = sys.argv
    exit_mode = int(exit_mode)
    new_terminal_was_created = new_terminal_was_created.lower() == "true"
    script_name = Path(script_path).name
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
        complete(
            "failure",
            log_path,
            report,
            f'"{script_name}" failed: {error_summary(report)}',
            keep_open=True,
        )
        handle_missing_module(missing, app_id, new_terminal_was_created)
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
