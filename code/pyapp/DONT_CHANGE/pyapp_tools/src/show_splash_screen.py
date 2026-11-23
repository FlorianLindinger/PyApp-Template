"""Preview the current app's splash without starting the app or preparing its environment.

Usage: show_splash_screen.bat [--seconds SECONDS]
Stays open until closed; --seconds optionally enables automatic closing.
Works even when show_splash_screen_for_no_terminal_start is disabled in developer_settings.py.
"""

from __future__ import annotations

import argparse
import math
import subprocess
import sys

from _paths import CODE_DIR


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--seconds", type=float, help="Automatically close after this many seconds (default: stay open)."
    )
    args = parser.parse_args()
    if args.seconds is not None and (not math.isfinite(args.seconds) or not 0 < args.seconds <= 60):
        parser.error("--seconds must be greater than 0 and at most 60")

    sys.path.append(str(CODE_DIR))
    from pyapp.DONT_CHANGE.scripts.config import settings
    from pyapp.DONT_CHANGE.scripts.desktop.splash import helper_command

    s = settings()
    print(f"Showing the splash: {s.program_name}. Click it or press Escape to close.", flush=True)
    # The same process and arguments as a no-terminal start, plus the preview flag (closes on a click or Escape).
    subprocess.run(helper_command(s, args.seconds or 0.0, preview=True), check=False)  # noqa: S603


if __name__ == "__main__":
    main()
