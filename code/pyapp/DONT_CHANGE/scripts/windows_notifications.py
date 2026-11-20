"""Windows toast notifications using the installed Windows PowerShell WinRT bridge.

No Python packages or registry changes are needed. Setup must have created the Start Menu
shortcut with its AppUserModelID. Windows/Do not disturb retain control over delivery.

Clicking the notification opens the crash log (or the log); its buttons open either one. Each is
a file:/// link that Windows opens with the file's default program, so nothing has to be
registered. Every notification of the app has the same tag, so a new one replaces the previous
one in the notification center instead of piling up.
"""

from __future__ import annotations

import base64
import os
import re
import subprocess
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Dict, Optional, Union
from xml.etree import ElementTree as ET

from pyapp.DONT_CHANGE import backend_settings as paths
from pyapp.DONT_CHANGE.scripts.console_tools import print_warn
from pyapp.DONT_CHANGE.scripts.diagnostics import note_ignored

# All executable PowerShell text is fixed. User text travels as XML in environment variables,
# never as script source. In particular $(), quotes and XML metacharacters cannot execute code.
TOAST_SCRIPT = r"""
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
try {
    [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType=WindowsRuntime] > $null
    [Windows.UI.Notifications.ToastNotification, Windows.UI.Notifications, ContentType=WindowsRuntime] > $null
    [Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType=WindowsRuntime] > $null
    $xml = [Windows.Data.Xml.Dom.XmlDocument]::new()
    $xml.LoadXml([Environment]::GetEnvironmentVariable('PYAPP_TOAST_XML'))
    $notifier = [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier(
        [Environment]::GetEnvironmentVariable('PYAPP_TOAST_APP_ID'))
    # Windows PowerShell can project the Enabled enum (zero) as null; compare its numeric value.
    $setting = [int]$notifier.Setting
    if ($setting -ne 0) {
        [Console]::WriteLine('Windows notification blocked (NotificationSetting code ' + $setting + ')' +
            '. Check Settings > System > Notifications (including this app), and Do not disturb.')
        exit 2
    }
    $toast = [Windows.UI.Notifications.ToastNotification]::new($xml)
    # The same tag and group replace the previous notification of this app instead of adding one.
    $toast.Tag = 'completion'
    $toast.Group = 'pyapp'
    # Removed from the notification center after a day, so old results do not linger.
    $toast.ExpirationTime = [DateTimeOffset]::Now.AddDays(1)
    $notifier.Show($toast)
} catch {
    [Console]::WriteLine('Windows notification failed: ' + $_.Exception.Message +
        '. Run Setup with Start Menu shortcuts enabled; check Windows notification settings.')
    exit 1
}
"""


# How long the end of a run waits for the helper's answer (usually well under a second).
WAIT_SECONDS = 3


def notification_image() -> Optional[str]:
    """The app's icon.png; while it is still the shipped placeholder, the bundled default icon."""
    try:
        from pyapp.DONT_CHANGE.scripts.image_tools import get_png_image_id

        if Path(paths.ICON_PNG_PATH).is_file() and get_png_image_id(paths.ICON_PNG_PATH) != paths.ICON_PLACEHOLDER_ID:
            return paths.ICON_PNG_PATH
    except Exception:
        note_ignored("read icon.png for the notification")
    default = Path(paths.DEFAULT_ICON_DIR) / "default_icon.png"
    return str(default) if default.is_file() else None


def _file_link(path: Optional[str]) -> Optional[str]:
    """A file:/// link to an existing file, or None (a link to nothing would open an error)."""
    if not path:
        return None
    try:
        file = Path(path).resolve()
        return file.as_uri() if file.is_file() else None
    except (OSError, ValueError):
        return None


def toast_xml(
    title: str,
    message: str,
    *,
    log_path: Optional[str] = None,
    crash_log_path: Optional[str] = None,
    image_path: Optional[str] = None,
    open_path: Optional[str] = None,
) -> str:
    """Build plain-text XML, including a silent audio node so play_sound_after_* remains authoritative.

    Clicking opens the crash log, else the log; a button opens each that exists. image_path (a
    PNG) is shown as the notification's large icon.
    """
    log_link, crash_link = _file_link(log_path), _file_link(crash_log_path)
    # open_path (pyapp_api.notify): what a click opens; it can also be a folder.
    open_link = Path(open_path).resolve().as_uri() if open_path and Path(open_path).exists() else None
    attributes = {}
    if open_link or crash_link or log_link:
        attributes = {"activationType": "protocol", "launch": open_link or crash_link or log_link or ""}
    toast = ET.Element("toast", attributes)
    visual = ET.SubElement(toast, "visual")
    binding = ET.SubElement(visual, "binding", {"template": "ToastGeneric"})
    ET.SubElement(binding, "text").text = title
    ET.SubElement(binding, "text").text = message
    image_link = _file_link(image_path)
    if image_link:
        ET.SubElement(binding, "image", {"placement": "appLogoOverride", "src": image_link})
    buttons = [(label, link) for label, link in (("Open crash log", crash_link), ("Open log", log_link)) if link]
    if buttons:
        actions = ET.SubElement(toast, "actions")
        for label, link in buttons:
            ET.SubElement(actions, "action", {"content": label, "activationType": "protocol", "arguments": link})
    ET.SubElement(toast, "audio", {"silent": "true"})
    return ET.tostring(toast, encoding="unicode")


def show(
    title: str,
    message: str,
    app_id: str,
    *,
    log_path: Optional[str] = None,
    crash_log_path: Optional[str] = None,
    open_path: Optional[str] = None,
) -> Optional[str]:
    """Return an actionable problem, or None when Windows accepted the request (not proof of delivery)."""
    if not app_id:
        return "Windows notification needs an app ID. Run Setup and start using a generated shortcut."
    xml = toast_xml(
        title,
        message,
        log_path=log_path,
        crash_log_path=crash_log_path,
        image_path=notification_image(),
        open_path=open_path,
    )
    env = os.environ.copy()
    env.update(PYAPP_TOAST_XML=xml, PYAPP_TOAST_APP_ID=app_id)
    encoded = base64.b64encode(TOAST_SCRIPT.encode("utf-16-le")).decode("ascii")
    # The system Windows PowerShell executable runs a fixed script; all configured text is data.
    process = subprocess.Popen(  # noqa: S603
        [paths.POWERSHELL_EXE, "-NoProfile", "-NonInteractive", "-WindowStyle", "Hidden", "-EncodedCommand", encoded],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf-8",
        errors="replace",
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    try:
        stdout, stderr = process.communicate(timeout=WAIT_SECONDS)
    except subprocess.TimeoutExpired:
        # A slow PowerShell start (antivirus scan, busy PC) must not hold up the end of the run. It
        # keeps running and still shows the notification; only a "blocked" message would be missed.
        return None
    if process.returncode:
        return (stdout or stderr or "").strip() or f"Windows notification helper exited with {process.returncode}."
    return None


def complete(
    s: Union[ModuleType, SimpleNamespace],
    outcome: str,
    message: Optional[str],
    log_path: Optional[str],
    crash_log_path: Optional[str],
) -> None:
    """Apply per-outcome notification switches/templates even when the terminal closes immediately."""
    if not getattr(s, "windows_notification_on_" + outcome, False):
        return
    values = {
        "outcome": outcome,
        "message": message or outcome.replace("_", " "),
        "log_path": log_path or "",
        "crash_log_path": crash_log_path or "",
    }
    try:
        title = render_text(s.windows_notification_title, values)
        text = render_text(getattr(s, "windows_notification_message_on_" + outcome), values)
        if not s.start_menu_shortcuts:
            print_warn("Windows notifications need Start Menu shortcuts. Enable start_menu_shortcuts and run Setup.")
            return
        problem = show(
            title,
            text,
            os.environ.get("PYAPP_NOTIFICATION_APP_ID", ""),
            log_path=log_path,
            crash_log_path=crash_log_path,
        )
        if problem:
            print_warn(problem)
    except Exception:
        # A blocked/missing PowerShell or toast service must not interrupt reporting/recovery.
        note_ignored("Windows completion notification")
        print_warn(
            "Windows notification failed. Check Windows PowerShell, Setup and Settings > System > Notifications."
        )


def render_text(text: str, values: Dict[str, str]) -> str:
    """Replace exit-time fields once; keep other braces and braces inside substituted values literal.

    program_name and other static expressions are already evaluated by the settings file's
    f-strings. A general str.format() here would reinterpret literal braces in those values.
    """
    return re.sub(r"(?<!\{)\{(outcome|message|log_path|crash_log_path)\}(?!\})", lambda match: values[match[1]], text)
