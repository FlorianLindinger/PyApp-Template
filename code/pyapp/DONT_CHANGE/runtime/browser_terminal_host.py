"""Run the browser terminal (DONT_CHANGE/browser_terminal) for the launcher.

Usage: python -I -S -X utf8 browser_terminal_host.py --config <file> -- <command> [arguments]

The browser_terminal package is self-contained so it can be copied into other projects; this
wrapper connects it to the launcher: errors it ignores go to the launcher's diagnostics log.
"""

import sys
from pathlib import Path

# Last, so app modules named like standard-library modules (code/random.py, ...) cannot shadow them.
sys.path.append(str(Path(__file__).resolve().parents[3]))
from pyapp.DONT_CHANGE.browser_terminal import host
from pyapp.DONT_CHANGE.scripts.diagnostics import note_ignored

if __name__ == "__main__":
    host.report_ignored = note_ignored
    sys.exit(host.main())
