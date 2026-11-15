"""Settings of the browser terminal: change the values below.

They are the defaults for every terminal this package shows. A program that starts the terminal
can still pass its own theme, font or scroll speed (see host.complete_config); those win. The
page's own switches (gear menu) remember what was chosen there; the switches here only set how
they start in a browser that has never changed them. A value of the wrong type is ignored, and
the built-in default is used instead.
"""

from __future__ import annotations

from typing import Dict

# --- Text ---
# Font names in CSS order: the first one installed is used.
FONT_FAMILY = '"Cascadia Mono", Consolas, "Courier New", monospace'
# Font size in pixels at the start and after Ctrl+0.
FONT_SIZE = 15
# Cursor: "block", "underline" or "bar"; and whether it blinks.
CURSOR_STYLE = "block"
CURSOR_BLINK = True
# Colors that replace entries of the classic console palette, e.g. {"background": "#1e1e1e",
# "foreground": "#d4d4d4", "red": "#f14c4c"} (names as in ui.DEFAULT_THEME).
COLORS: Dict[str, str] = {}

# --- Zoom (Ctrl+wheel, touchpad pinch, Ctrl+plus/minus/0) ---
# Smallest and largest font size zoom reaches.
MIN_FONT_SIZE = 6
MAX_FONT_SIZE = 72
# One step of Ctrl+plus/minus or a mouse wheel notch, in percent (always at least one pixel).
ZOOM_STEP_PERCENT = 15
# How fast a touchpad pinch zooms: 1 is the default, 2 twice as fast, 0.5 half as fast.
PINCH_ZOOM_SPEED = 1.0

# --- Scrolling ---
# Lines per mouse wheel step, as a multiple of the browser's own; Alt+wheel scrolls this many times faster.
SCROLL_LINES = 5
FAST_SCROLL_FACTOR = 5
# Lines kept for scrolling back (the classic console keeps 9001).
SCROLLBACK_LINES = 9001
# Default for the live Wrap lines switch; off uses a horizontally scrollable 1,000-column terminal.
WRAP_OUTPUT = True

# Toolbar controls to show, in their normal order. [] hides the toolbar buttons.
# Open buttons also require their corresponding configured paths. The running-status
# indicator stays visible. These settings also work when this folder runs on its own.
BUTTONS = ["search", "save", "clear", "wrap", "code", "settings", "logs", "crash_logs", "info", "view", "bookmark"]

# --- New output (the page's gear menu changes and remembers these) ---
# Light up new output for a moment.
HIGHLIGHT_NEW_OUTPUT = True
# Follow new output to the bottom (pauses while scrolled up).
FOLLOW_NEW_OUTPUT = True
# Bring the browser to the front when the program asks for input.
FRONT_ON_INPUT = False
# Shortest time between two "on every output" notifications, in seconds.
NOTIFY_EVERY_MIN_SECONDS = 1.0

# --- Opening files and folders (the page's buttons, clicked paths in the output) ---
# Bring the editor or Explorer window to the front once it opens, waiting at most this long (seconds).
FOCUS_OPENED_WINDOWS = True
FOCUS_WAIT_SECONDS = 10.0
