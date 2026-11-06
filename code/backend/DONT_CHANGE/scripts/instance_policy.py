"""instance_policy: what happens when the app is started while it is already running."""

from __future__ import annotations

import ctypes

from backend.DONT_CHANGE.scripts.diagnostics import note_ignored

MB_YESNO = 0x04
MB_ICONINFORMATION = 0x40
MB_ICONQUESTION = 0x20
MB_SETFOREGROUND = 0x10000
MB_TOPMOST = 0x40000
IDYES = 6


def message_box(text: str, title: str, flags: int) -> int:
    """Windows dialog; works for launches with and without a terminal."""
    return ctypes.windll.user32.MessageBoxW(None, text, title, flags | MB_SETFOREGROUND | MB_TOPMOST)


def ask_yes_no(text: str, title: str) -> bool:
    return message_box(text, title, MB_YESNO | MB_ICONQUESTION) == IDYES


def decide(policy: str, records: list, program_name: str) -> str:
    """Return "start", "cancel" or "replace" for the given running instances (may show a dialog).

    Never called while holding the process-registry lock, so other launchers are not blocked
    while a dialog is open.
    """
    if not records or policy == "allow":
        return "start"
    if policy == "replace":
        return "replace"
    count = len(records)
    running = f"{program_name} is already running" + (f" ({count} instances)." if count > 1 else ".")
    if policy == "prevent":
        message_box(running, program_name, MB_ICONINFORMATION)
        return "cancel"
    if policy == "focus":
        from backend.DONT_CHANGE.scripts.windows_focus import focus_instance

        for record in records:
            try:
                if focus_instance(record) == "focused":
                    return "cancel"
            except Exception:
                note_ignored("focus_instance")
        question = running + "\n\nIt has no window to show. Close it and start again?"
        return "replace" if ask_yes_no(question, program_name) else "cancel"
    if policy == "ask":
        question = running + "\n\nClose the running instance(s) and start again?"
        return "replace" if ask_yes_no(question, program_name) else "cancel"
    raise ValueError(f"Unknown instance_policy: {policy!r}")
