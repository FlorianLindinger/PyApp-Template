"""Shared helpers for script launch backends."""

import atexit
import os
import re
import subprocess
import sys
import threading
from datetime import datetime, timezone

WINDOWS_CRASH_CODES = {
    0xC0000005,  # access violation
    0xC00000FD,  # stack overflow
    0xC000001D,  # illegal instruction
    0xC0000096,  # privileged instruction
    0xC0000409,  # stack buffer overrun
}

ANSI_ESCAPE_RE = re.compile(
    r"\x1b(?:"
    r"\[[0-?]*[ -/]*[@-~]"
    r"|\][^\x07]*(?:\x07|\x1b\\)"
    r"|[@-Z\\-_]"
    r")"
)


def _strip_ansi_escape_sequences(text: str) -> str:
    return ANSI_ESCAPE_RE.sub("", text)


def arg_to_bool(index: int, default: bool = False, argv: list[str] | None = None) -> bool:
    if argv is None:
        argv = sys.argv
    if len(argv) <= index:
        return default
    return argv[index].strip().lower() in {"1", "true", "yes", "on"}


def arg_to_wav_path(index: int, argv: list[str] | None = None) -> str:
    if argv is None:
        argv = sys.argv
    if len(argv) <= index:
        return ""
    wav_path = argv[index].strip()
    if wav_path != "" and os.path.splitext(wav_path)[1].lower() != ".wav":
        raise ValueError(f'[Error] Sound argument must be empty or a .wav file: "{wav_path}"')
    return wav_path


def unsigned32(n: int) -> int:
    return n & 0xFFFFFFFF


def looks_like_interpreter_crash(returncode) -> bool:
    return isinstance(returncode, int) and (unsigned32(returncode) in WINDOWS_CRASH_CODES)


class ProcessIdRegistry:
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


class TerminalLogger:
    def __init__(self, path: str, overwrite: bool, timestamp_format: str) -> None:
        self.path = self._prepare_log_path(path) if path else ""
        self.timestamp_format = timestamp_format
        self._at_line_start = True
        self._lock = threading.RLock()
        self._log_file = None
        if self.path:
            self._log_file = open(self.path, "w" if overwrite else "a", encoding="utf-8", buffering=1)  # noqa
            atexit.register(self.close)

    @staticmethod
    def _prepare_log_path(path: str) -> str:
        path = datetime.now(tz=timezone.utc).strftime(path)
        folder = os.path.dirname(path)
        if folder:
            os.makedirs(folder, exist_ok=True)
        return path

    def _add_timestamps(self, text: str) -> str:
        if not self.timestamp_format or text == "":
            return text

        output: list[str] = []
        for char in text:
            if self._at_line_start:
                output.append(datetime.now(tz=timezone.utc).strftime(self.timestamp_format))
            output.append(char)
            self._at_line_start = char == "\n"
        return "".join(output)

    def write(self, text: str) -> None:
        if self._log_file is None or text == "":
            return

        with self._lock:
            text = _strip_ansi_escape_sequences(text)
            self._log_file.write(self._add_timestamps(text))
            self._log_file.flush()

    def close(self) -> None:
        if self._log_file is not None:
            try:
                self._log_file.close()
            except Exception:
                pass
            self._log_file = None


def play_windows_sound(wav_path: str) -> None:
    if os.name != "nt":
        return

    try:
        import winsound

        sound = wav_path
        if not os.path.isabs(sound):
            sound = os.path.join(r"C:\Windows\Media", sound)
        winsound.PlaySound(
            sound,
            winsound.SND_FILENAME | winsound.SND_NODEFAULT,
        )
    except Exception:
        pass


def send_windows_notification(notification_title: str, message: str, app_id: str) -> None:
    if os.name != "nt":
        return

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
            send_windows_notification(
                f"{self.title}: {kind.title()}",
                messages.get(kind, f"Script ended with code {exit_code}."),
                self.app_id,
            )
        sound_setting = self.play_sound_by_kind.get(kind)
        if sound_setting:
            play_windows_sound(sound_setting)
        if self.open_log_file_by_kind.get(kind, False) and self.log_path != "":
            try:
                os.startfile(self.log_path)  # type: ignore[attr-defined]  # noqa:S606
            except Exception:
                pass
