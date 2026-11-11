"""Record errors the launcher deliberately ignores, so they can be found later.

Cosmetic steps (window icon, title, colors, focus, ...) must never stop an app from starting,
so their errors are ignored. Instead of disappearing silently, each one is appended to
DONT_CHANGE/tmp/diagnostics.log (shown by the status dev tool). Set PYAPP_DEBUG=1 to also
print them.
"""

from __future__ import annotations

import contextlib
import os
import sys
from pathlib import Path
from typing import Optional

from pyapp.DONT_CHANGE.backend_settings import DIAGNOSTICS_LOG_PATH

_MAX_BYTES = 1_000_000  # then the log is renamed to diagnostics.log.old and started again


def note_ignored(context: str) -> None:
    """Append the exception being handled (with traceback) to the diagnostics log; never raises."""
    # The one place where swallowing every error is the job: a failing log must not add a new error.
    with contextlib.suppress(Exception):
        import time
        import traceback

        text = traceback.format_exc().rstrip()
        entry = f"{time.strftime('%Y-%m-%d %H:%M:%S')}  pid {os.getpid()}  {Path(sys.argv[0] or '?').name}: {context}\n{text}\n\n"
        if os.environ.get("PYAPP_DEBUG") == "1":
            print("[Debug] Ignored error: " + context + "\n" + text, file=sys.stderr)
        (Path(DIAGNOSTICS_LOG_PATH).parent).mkdir(parents=True, exist_ok=True)
        with contextlib.suppress(OSError):
            if Path(DIAGNOSTICS_LOG_PATH).stat().st_size > _MAX_BYTES:
                Path(DIAGNOSTICS_LOG_PATH).replace(DIAGNOSTICS_LOG_PATH + ".old")
        with Path(DIAGNOSTICS_LOG_PATH).open("a", encoding="utf-8") as stream:
            stream.write(entry)


def diagnostics_summary() -> Optional[str]:
    """Short description of the diagnostics log for the status tool, or None if it is empty."""
    import re

    try:
        with Path(DIAGNOSTICS_LOG_PATH).open(encoding="utf-8", errors="replace") as stream:
            text = stream.read()
    except OSError:
        return None
    # One header line per entry, as note_ignored writes it. Not blank lines: a chained traceback
    # has them around "During handling of the above exception, another exception occurred:".
    headers = re.findall(r"(?m)^\d{4}-\d\d-\d\d \d\d:\d\d:\d\d  pid \d+  .*$", text)
    if not headers:
        return None
    return f"{len(headers)} ignored error(s), last: {headers[-1]}"
