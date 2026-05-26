# todo: docstring

# ====================================
# import packages

import atexit
import os
import sys
import threading

# ====================================
# add root dir for debug cases where this script is called on its own:

root_dir = os.path.dirname(__file__) + "\\..\\.."
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

# ====================================
# import from files

from developer_settings import (
    input_prepend,
    log_input_prepend,
    log_print_prepend,
    play_sound_on_crash,
    play_sound_on_failure,
    play_sound_on_success,
    print_prepend,
    python_version,
    start_in_shortcut_folder,
)
from DONT_CHANGE.specific_scripts.common_variables import (
    CORRECT_START_SIGNAL_FILE_PATH,
    env_var_to_signal_startup_time_measurement,
    play_sound_on_crash_default,
    play_sound_on_failure_default,
    play_sound_on_success_default,
    process_id_file_path,
    python_script_path,
    start_time_dummy_main_script,
    windows_dir,
)

# ====================================
# process developer_settings settings

# change main_script if in startup time measurement mode
if os.environ.get(env_var_to_signal_startup_time_measurement):
    python_script_path = start_time_dummy_main_script

# raise error if script not found
if not os.path.exists(python_script_path):
    raise FileNotFoundError(f'[Error] Python script not found at "{python_script_path}"')

if start_in_shortcut_folder == True:
    wdir_is_script_dir = False
else:
    wdir_is_script_dir = True

if python_version in [None, False, ""]:
    python_version = ""
if log_print_prepend in [None, False, ""]:
    log_print_prepend = ""
if log_input_prepend in [None, False, ""]:
    log_input_prepend = ""
if print_prepend in [None, False, ""]:
    print_prepend = ""
if input_prepend in [None, False, ""]:
    input_prepend = ""

if play_sound_on_crash is True:
    play_sound_on_crash = play_sound_on_crash_default
elif play_sound_on_crash in [False, None, ""]:
    play_sound_on_crash = ""
elif not os.path.isabs(play_sound_on_crash):
    play_sound_on_crash = os.path.normpath(windows_dir + "\\Media\\" + play_sound_on_crash)
if play_sound_on_crash != "" and play_sound_on_crash[-4:] != ".wav":
    play_sound_on_crash += ".wav"
if play_sound_on_crash != "" and not os.path.exists(play_sound_on_crash):
    print(f"[Warning] Sound file does not exist: {play_sound_on_crash}")
if play_sound_on_success is True:
    play_sound_on_success = play_sound_on_success_default
elif play_sound_on_success in [False, None, ""]:
    play_sound_on_success = ""
elif not os.path.isabs(play_sound_on_success):
    play_sound_on_success = os.path.normpath(windows_dir + "\\Media\\" + play_sound_on_success)
if play_sound_on_success != "" and play_sound_on_success[-4:] != ".wav":
    play_sound_on_success += ".wav"
if play_sound_on_success != "" and not os.path.exists(play_sound_on_success):
    print(f"[Warning] Sound file does not exist: {play_sound_on_success}")
if play_sound_on_failure is True:
    play_sound_on_failure = play_sound_on_failure_default
elif play_sound_on_failure in [False, None, ""]:
    play_sound_on_failure = ""
elif not os.path.isabs(play_sound_on_failure):
    play_sound_on_failure = os.path.normpath(windows_dir + "\\Media\\" + play_sound_on_failure)
if play_sound_on_failure != "" and play_sound_on_failure[-4:] != ".wav":
    play_sound_on_failure += ".wav"
if play_sound_on_failure != "" and not os.path.exists(play_sound_on_failure):
    print(f"[Warning] Sound file does not exist: {play_sound_on_failure}")

# ====================================
#  define common code


def create_signal_file(path: str) -> None:
    if path == "":
        return

    folder = os.path.dirname(path)
    if folder:
        os.makedirs(folder, exist_ok=True)
    with open(path, "w", encoding="utf-8"):
        pass


class _ProcessIdRegistry:
    def __init__(self, path: str) -> None:
        self.path = path
        self._process_ids: set[int] = set()
        self._lock = threading.RLock()

    def add(self, process_id: int) -> None:
        if self.path == "" or process_id <= 0:
            return

        with self._lock:
            if process_id in self._process_ids:
                return
            self._process_ids.add(process_id)

            folder = os.path.dirname(self.path)
            if folder:
                os.makedirs(folder, exist_ok=True)
            with open(self.path, "a", encoding="utf-8") as pid_file:
                pid_file.write(f"{process_id}\n")

    def remove(self, process_id: int) -> None:
        if self.path == "" or process_id <= 0:
            return

        with self._lock:
            self._process_ids.discard(process_id)
            try:
                with open(self.path, encoding="utf-8") as pid_file:
                    lines = pid_file.readlines()
            except FileNotFoundError:
                return
            except Exception:
                return

            remaining_lines = []
            process_id_text = str(process_id)
            for line in lines:
                parts = line.strip().split(maxsplit=1)
                if parts and parts[0] == process_id_text:
                    continue
                remaining_lines.append(line)

            try:
                if any(line.strip() for line in remaining_lines):
                    with open(self.path, "w", encoding="utf-8") as pid_file:
                        pid_file.writelines(remaining_lines)
                else:
                    os.remove(self.path)
            except Exception:
                pass

    def cleanup(self) -> None:
        for process_id in list(self._process_ids):
            self.remove(process_id)


class CompletionAlerts:
    def __init__(
        self,
        *,
        title: str,
        app_id: str,
        log_path: str = "",
        play_sound_on_success: str,
        send_windows_notification_on_success: bool,
        play_sound_on_failure: str,
        send_windows_notification_on_failure: bool,
        play_sound_on_python_interpreter_crash: str,
        send_windows_notification_on_python_interpreter_crash: bool,
        open_log_file_after_success: bool = False,
        open_log_file_after_failure: bool = False,
        open_log_file_after_python_interpreter_crash: bool = False,
    ) -> None:
        self.title = title
        self.app_id = app_id
        self.log_path = log_path
        self.play_sound_by_kind = {
            "success": play_sound_on_success,
            "failure": play_sound_on_failure,
            "crash": play_sound_on_python_interpreter_crash,
        }
        self.notification_by_kind = {
            "success": send_windows_notification_on_success,
            "failure": send_windows_notification_on_failure,
            "crash": send_windows_notification_on_python_interpreter_crash,
        }
        self.open_log_file_by_kind = {
            "success": open_log_file_after_success,
            "failure": open_log_file_after_failure,
            "crash": open_log_file_after_python_interpreter_crash,
        }

    def run(self, kind: str, exit_code) -> None:
        messages = {
            "success": "Script finished successfully.",
            "failure": f"Script exited with code {exit_code}.",
            "crash": f"Python process crashed with code {exit_code}.",
        }

        if self.notification_by_kind.get(kind, False):
            _send_windows_notification(
                f"{self.title}: {kind.title()}",
                messages.get(kind, f"Script ended with code {exit_code}."),
                self.app_id,
            )
        sound_setting = self.play_sound_by_kind.get(kind)
        if sound_setting:
            _play_wav(sound_setting)
        if self.open_log_file_by_kind.get(kind, False) and self.log_path != "":
            try:
                os.startfile(self.log_path)  # type: ignore[attr-defined]  # noqa:S606
            except Exception:
                pass


def _play_wav(wav_path: str) -> None:
    try:
        import winsound

        winsound.PlaySound(
            wav_path,
            winsound.SND_FILENAME | winsound.SND_NODEFAULT,
        )
    except Exception:
        pass


def _send_windows_notification(notification_title: str, message: str, app_id: str) -> None:
    import subprocess

    powershell_script = r"""
$titleText = if ($args.Count -gt 0) { $args[0] } else { "Python script" }
$messageText = if ($args.Count -gt 1) { $args[1] } else { "" }
$appId = if ($args.Count -gt 2 -and $args[2]) { $args[2] } else { "PyAppTemplate" }
[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType=WindowsRuntime] | Out-Null
[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType=WindowsRuntime] | Out-Null
$titleXml = [System.Security.SecurityElement]::Escape($titleText)
$messageXml = [System.Security.SecurityElement]::Escape($messageText)
$xml = @"
<toast>
  <visual>
    <binding template="ToastGeneric">
      <text>$titleXml</text>
      <text>$messageXml</text>
    </binding>
  </visual>
  <audio silent="true"/>
</toast>
"@
$doc = [Windows.Data.Xml.Dom.XmlDocument]::new()
$doc.LoadXml($xml)
$toast = [Windows.UI.Notifications.ToastNotification]::new($doc)
[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier($appId).Show($toast)
"""
    try:
        subprocess.Popen(  # noqa:S603
            [
                "powershell.exe",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                powershell_script,
                notification_title,
                message,
                app_id,
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except Exception:
        pass


def _unsigned32(n: int) -> int:
    return n & 0xFFFFFFFF


def looks_like_interpreter_crash(returncode) -> bool:
    _WINDOWS_CRASH_CODES = {
        0xC0000005,  # access violation
        0xC00000FD,  # stack overflow
        0xC000001D,  # illegal instruction
        0xC0000096,  # privileged instruction
        0xC0000409,  # stack buffer overrun
    }

    return isinstance(returncode, int) and (_unsigned32(returncode) in _WINDOWS_CRASH_CODES)


# ====================================
#  execute common code

# tell the backend terminal to close because successful start
create_signal_file(CORRECT_START_SIGNAL_FILE_PATH)

# add pid to "currently running" file
if process_id_file_path != "":
    try:
        process_id_registry = _ProcessIdRegistry(process_id_file_path)
        process_id_registry.add(os.getpid())
        atexit.register(process_id_registry.cleanup)
    except Exception as e:
        print(f"[Warning] Failed to write script-wrapper PID file: {e}")

# ====================================
