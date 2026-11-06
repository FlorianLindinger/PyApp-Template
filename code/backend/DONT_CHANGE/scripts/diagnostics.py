"""Record errors the launcher deliberately ignores, so they can be found later.

Cosmetic steps (window icon, title, colors, focus, ...) must never stop an app from starting,
so their errors are ignored. Instead of disappearing silently, each one is appended to
DONT_CHANGE/tmp/diagnostics.log (shown by the status dev tool). Set PYAPP_DEBUG=1 to also
print them.
"""

from __future__ import annotations

import os
import sys

from backend.DONT_CHANGE.backend_settings import DIAGNOSTICS_LOG_PATH

_MAX_BYTES = 1_000_000  # then the log is renamed to diagnostics.log.old and started again


def note_ignored(context: str) -> None:
    """Append the exception being handled (with traceback) to the diagnostics log; never raises."""
    try:
        import time
        import traceback

        text = traceback.format_exc().rstrip()
        entry = f"{time.strftime('%Y-%m-%d %H:%M:%S')}  pid {os.getpid()}  {os.path.basename(sys.argv[0] or '?')}: {context}\n{text}\n\n"
        if os.environ.get("PYAPP_DEBUG") == "1":
            print("[Debug] Ignored error: " + context + "\n" + text, file=sys.stderr)
        os.makedirs(os.path.dirname(DIAGNOSTICS_LOG_PATH), exist_ok=True)
        try:
            if os.path.getsize(DIAGNOSTICS_LOG_PATH) > _MAX_BYTES:
                os.replace(DIAGNOSTICS_LOG_PATH, DIAGNOSTICS_LOG_PATH + ".old")
        except OSError:
            pass
        with open(DIAGNOSTICS_LOG_PATH, "a", encoding="utf-8") as stream:
            stream.write(entry)
    except Exception:  # noqa: S110 - diagnostics must never break the launcher
        pass


def diagnostics_summary() -> str | None:
    """Short description of the diagnostics log for the status tool, or None if it is empty."""
    try:
        with open(DIAGNOSTICS_LOG_PATH, encoding="utf-8", errors="replace") as stream:
            entries = [block for block in stream.read().split("\n\n") if block.strip()]
    except OSError:
        return None
    if not entries:
        return None
    last = entries[-1].splitlines()[0]
    return f"{len(entries)} ignored error(s), last: {last}"
