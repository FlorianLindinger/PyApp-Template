"""Apply the configured completion behavior after the application (or the watchdog) ended.

Arguments: exit_mode app_id new_terminal_was_created log_path script_path
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from typing import NoReturn

fail_message = "[Error] Failed while processing program exit: {e}"


def _fail_while_loading(error) -> NoReturn:
    """This window may be the only place the problem is visible: show it and wait."""
    import traceback

    print("\n\n" + "=" * 30)
    print(fail_message.format(e=error))
    print("-" * 30)
    print(traceback.format_exc())
    print("=" * 30)
    input("[Error] Press Enter to exit")
    os._exit(1)


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
try:
    from backend.DONT_CHANGE import backend_settings as paths
    from backend.DONT_CHANGE.runtime._pyapp import (
        ExitMode,
        exit_code_is_success,
    )
    from backend.DONT_CHANGE.scripts.config import settings
    from backend.DONT_CHANGE.scripts.console_tools import (
        enable_ansi,
        input_warn,
        open_in_editor,
        print_warn,
        set_terminal_app_id,
        set_terminal_colors,
        set_terminal_icon,
        set_terminal_title,
    )
    from backend.DONT_CHANGE.scripts.launcher_ui import (
        get_log_path,
        print_traceback,
    )
    from backend.DONT_CHANGE.scripts.runtime_state import (
        exit_code_looks_like_interpreter_crash,
        unique_log_path,
    )
    from backend.DONT_CHANGE.scripts.traceback_render import render
except Exception as import_error:
    _fail_while_loading(import_error)

REPORT_PATH = os.path.join(os.environ.get("PYAPP_RUN_DIR", paths.TEMPORARY_DIR), "traceback.json")

OUTCOMES = {
    "success": {
        "icon": paths.SUCCESS_ICON_PATH,
        "default_sound": paths.DEFAULT_SOUND_AFTER_SUCCESS,
    },
    "failure": {
        "icon": paths.FAILURE_ICON_PATH,
        "default_sound": paths.DEFAULT_SOUND_AFTER_FAILURE,
    },
    "crash": {"icon": paths.CRASH_ICON_PATH, "default_sound": paths.DEFAULT_SOUND_AFTER_CRASH},
    "keyboard_interrupt": {
        "icon": paths.KEYBOARD_INTERRUPT_ICON_PATH,
        "default_sound": paths.DEFAULT_SOUND_AFTER_KEYBOARD_INTERRUPT,
    },
}

# ------------------------------------------------------------ reports


def load_report():
    """Return (report, problem description)."""
    try:
        with open(REPORT_PATH, encoding="utf-8") as stream:
            report = json.load(stream)
    except FileNotFoundError:
        return None, f'The traceback report was not created at "{REPORT_PATH}".'
    except (OSError, UnicodeError, ValueError) as error:
        return None, f'Could not read the traceback report "{REPORT_PATH}": {error}'
    if not isinstance(report, dict) or "chain" not in report:
        return None, f'The traceback report "{REPORT_PATH}" has an unknown format.'
    return report, None


def print_report(report):
    s = settings()
    if report:
        colors = bool(s.traceback_colors) and sys.stdout is not None and sys.stdout.isatty()
        if colors:
            enable_ansi()
        print("\n".join(render(report, colors=colors, date_format=s.error_date_format)))


def write_crash_log(report, message):
    """Write a uniquely named plain-text crash report."""
    s = settings()
    path = get_log_path(s.crash_log_path, s.crash_log_path_is_relative_to_start_folder_if_relative)
    if not path or (report is None and message is None):
        return
    path = unique_log_path(path, os.path.basename(os.environ.get("PYAPP_RUN_DIR", "")) or None)
    lines = ["=" * 30]
    if message:
        lines.append(message)
    if report:
        lines += render(report, colors=False, date_format=s.error_date_format)
    lines.append("=" * 30)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w" if s.overwrite_crash_log else "a", encoding="utf-8") as stream:
        stream.write("\n".join(lines) + "\n")


# ------------------------------------------------------------ recovery


def restart_program(app_id, new_terminal_was_created):
    """Start the program again with the same terminal behavior."""
    env = os.environ.copy()
    env["PYAPP_LAUNCH_MODE"] = "no_terminal" if new_terminal_was_created else "terminal"
    subprocess.Popen(
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


def local_module_exists(name):
    """True when the missing import is a module/package of the project itself (do not install)."""
    root = paths.PYTHON_SCRIPTS_DIR
    return os.path.isfile(os.path.join(root, name + ".py")) or os.path.isdir(os.path.join(root, name))


def handle_missing_module(missing, app_id, new_terminal_was_created):
    """Offer to install the distribution behind a ModuleNotFoundError, then restart."""
    s = settings()
    from backend.DONT_CHANGE.scripts.env import venv
    from backend.DONT_CHANGE.scripts.import_finder import distribution_for_import

    top = missing.split(".")[0]
    if local_module_exists(top):
        print_warn(
            f'"{top}" is part of your project, not a package to install. Check the file/folder name and the import.'
        )
        input_warn("Press Enter to exit")
        return
    distribution = distribution_for_import(top)
    app_python = venv.app_python_for_tools()
    global_packages = s.package_environment == "interpreter_site_packages"
    if global_packages and not s.allow_installing_into_global_python:
        print_warn("The app uses the selected interpreter's own packages; the launcher does not change them.")
        print(f'Install it yourself, e.g.:  "{app_python}" -m pip install {distribution}')
        print("(or set allow_installing_into_global_python = True in developer_settings.py)")
        input_warn("Press Enter to exit")
        return
    if distribution != top:
        print(f'[Info] The import "{top}" is provided by the package "{distribution}".')
    options = []
    if not global_packages:
        options.append(
            (
                "add",
                f'Add "{distribution}" to the packages in developer_settings.py and restart',
            )
        )
    options.append(("install", f'Install "{distribution}" without recording it and restart'))
    if not global_packages:
        options.append(
            (
                "find",
                "Find all imports of the project, review them, add the missing ones and restart",
            )
        )
    options.append(("terminal", "Open a package terminal, then restart"))
    options.append(("quit", "Quit"))
    while True:
        print()
        print_warn("Choose how to proceed:")
        for index, (_, label) in enumerate(options, 1):
            print(f"  {index}: {label}")
        answer = input_warn(f"Choose an option [1-{len(options)}]: ").strip()
        if not answer.isdigit() or not 1 <= int(answer) <= len(options):
            continue
        action = options[int(answer) - 1][0]
        if action == "quit":
            return
        try:
            if action == "add":
                venv.add_packages([distribution])
            elif action == "install":
                venv.install_without_recording([distribution], app_python)
            elif action == "find":
                from backend.DONT_CHANGE.scripts.dev.packages import (
                    find_imports_and_add,
                )

                find_imports_and_add()
            else:
                venv.open_package_terminal()
        except Exception as error:
            print_traceback(f"[Error] Package recovery failed: {error}")
            continue
        print("[Success] Restarting the program...")
        restart_program(app_id, new_terminal_was_created)
        return


# ------------------------------------------------------------ completion


def play_sound(setting, default, wait=True):
    if setting is True:
        wav = default
    elif setting in (False, None, ""):
        wav = ""
    elif not os.path.isabs(setting):
        wav = os.path.join(paths.WINDOWS_DIR, "Media", setting)
    else:
        wav = setting
    if wav and not wav.lower().endswith(".wav"):
        wav += ".wav"
    if not wav:
        return
    try:
        import winsound

        flags = winsound.SND_FILENAME | winsound.SND_NODEFAULT | (0 if wait else winsound.SND_ASYNC)
        winsound.PlaySound(wav, flags)
    except Exception as error:
        print(f"[Error] Failed to play .wav file: {error}")


def complete(outcome, log_path, report=None, message=None, keep_open=False):
    """Run the configured actions for success/failure/crash/keyboard_interrupt."""
    s = settings()
    close = getattr(s, "close_after_" + outcome)
    if log_path and getattr(s, "open_log_file_after_" + outcome):
        try:
            os.startfile(log_path)
        except Exception as error:
            print(f"[Error] Failed to open log: {error}")
    if getattr(s, "open_main_py_after_" + outcome):
        open_in_editor(paths.MAIN_PY_SCRIPT_PATH)
    if message:
        print(message)
    if outcome != "success":
        write_crash_log(report, message)
    sound = getattr(s, "play_sound_after_" + outcome)
    if close is False or keep_open:
        set_terminal_title(getattr(s, "title_after_" + outcome))
        set_terminal_colors(getattr(s, "terminal_colors_after_" + outcome))
        set_terminal_icon(OUTCOMES[outcome]["icon"])
        print_report(report)  # after set_terminal_colors, which clears the screen colors
        play_sound(sound, OUTCOMES[outcome]["default_sound"], wait=not keep_open)
        if not keep_open:
            input("Press Enter to exit")
    else:
        print_report(report)
        play_sound(sound, OUTCOMES[outcome]["default_sound"])


def main():
    settings()  # a broken settings file fails here, first; later calls reuse the import
    _, exit_mode, app_id, new_terminal_was_created, log_path, script_path = sys.argv
    exit_mode = int(exit_mode)
    new_terminal_was_created = new_terminal_was_created.lower() == "true"
    script_name = os.path.basename(script_path)
    if new_terminal_was_created:
        set_terminal_app_id(app_id)

    if "PYAPP_UNEXPECTED_EXIT" in os.environ:
        native = int(os.environ["PYAPP_UNEXPECTED_EXIT"])
        crashed = exit_code_looks_like_interpreter_crash(native)
        hint = " See the .output.log next to the log file for the interpreter's last output." if log_path else ""
        complete(
            "crash" if crashed else "failure",
            log_path,
            None,
            f'[{"Crash" if crashed else "Failure"}] "{script_name}" ended without a completion report (exit status {native}, 0x{native & 0xFFFFFFFF:08X}).{hint}',
        )
        return

    if exit_mode == ExitMode.SUCCESS:
        complete("success", log_path, None, "[Success] Program finished successfully")
        return

    report, problem = load_report()
    if exit_mode == ExitMode.WATCHDOG_ERROR:
        complete(
            "failure",
            log_path,
            report,
            "[Failure] The background watchdog failed (see below)." + ("" if report else f" {problem}"),
        )
        return
    if exit_mode == ExitMode.WRAPPER_ERROR:
        complete(
            "failure",
            log_path,
            report,
            "[Failure] The script wrapper failed (see below)." + ("" if report else f" {problem}"),
        )
        return
    if exit_mode != ExitMode.APP_EXIT:
        raise ValueError(f"Unknown exit mode {exit_mode} from the watchdog.")
    if report is None:
        complete(
            "failure",
            log_path,
            None,
            f'[Failure] "{script_name}" failed, but its traceback could not be loaded. {problem}',
        )
        return

    kind = report.get("exception_type") or "Exception"
    if kind == "SystemExit":
        code = report.get("system_exit_code")
        if exit_code_is_success(code):
            complete("success", log_path, None, "[Success] Program finished successfully")
        elif exit_code_looks_like_interpreter_crash(code):
            complete(
                "crash",
                log_path,
                report,
                f'[Crash] The interpreter appears to have crashed with exit code "{code}" while running "{script_name}".',
            )
        else:
            complete(
                "failure",
                log_path,
                report,
                f'[Failure] "{script_name}" exited with error code "{code}".',
            )
    elif kind == "ModuleNotFoundError" and report.get("missing_module"):
        missing = report["missing_module"]
        complete(
            "failure",
            log_path,
            report,
            f'[Missing Package] "{script_name}" could not import "{missing}" (see below).',
            keep_open=True,
        )
        handle_missing_module(missing, app_id, new_terminal_was_created)
    elif kind == "KeyboardInterrupt":
        complete(
            "keyboard_interrupt",
            log_path,
            report,
            f'[Interrupted] "{script_name}" was stopped with Ctrl+C.',
        )
    elif kind == "SyntaxError":
        complete(
            "failure",
            log_path,
            report,
            f'[Failure] "{script_name}" has a syntax error (see below).',
        )
    else:
        complete(
            "failure",
            log_path,
            report,
            f'[Failure] "{script_name}" raised {kind} (see below).',
        )


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print_traceback(fail_message.format(e=error))
        input_warn("[Error] Press Enter to exit")
        sys.exit(1)
    sys.exit(0)
