"""Windows toast notifications using the installed Windows PowerShell WinRT bridge.

No Python packages or registry changes are needed. Setup must have created the Start Menu
shortcut with its AppUserModelID. Windows/Do not disturb retain control over delivery.
"""

from __future__ import annotations

import base64
import os
import re
import subprocess
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
    $notifier.Show($toast)
} catch {
    [Console]::WriteLine('Windows notification failed: ' + $_.Exception.Message +
        '. Run Setup with Start Menu shortcuts enabled; check Windows notification settings.')
    exit 1
}
"""


def toast_xml(title: str, message: str) -> str:
    """Build plain-text XML, including a silent audio node so play_sound_after_* remains authoritative."""
    toast = ET.Element("toast")
    visual = ET.SubElement(toast, "visual")
    binding = ET.SubElement(visual, "binding", {"template": "ToastGeneric"})
    ET.SubElement(binding, "text").text = title
    ET.SubElement(binding, "text").text = message
    ET.SubElement(toast, "audio", {"silent": "true"})
    return ET.tostring(toast, encoding="unicode")


def show(title: str, message: str, app_id: str) -> Optional[str]:
    """Return an actionable problem, or None when Windows accepted the request (not proof of delivery)."""
    if not app_id:
        return "Windows notification needs an app ID. Run Setup and start using a generated shortcut."
    env = os.environ.copy()
    env.update(PYAPP_TOAST_XML=toast_xml(title, message), PYAPP_TOAST_APP_ID=app_id)
    encoded = base64.b64encode(TOAST_SCRIPT.encode("utf-16-le")).decode("ascii")
    # The system Windows PowerShell executable runs a fixed script; all configured text is data.
    result = subprocess.run(  # noqa: S603
        [paths.POWERSHELL_EXE, "-NoProfile", "-NonInteractive", "-WindowStyle", "Hidden", "-EncodedCommand", encoded],
        env=env,
        check=False,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        timeout=15,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    if result.returncode:
        return (
            result.stdout or result.stderr
        ).strip() or f"Windows notification helper exited with {result.returncode}."
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
        problem = show(title, text, os.environ.get("PYAPP_NOTIFICATION_APP_ID", ""))
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
