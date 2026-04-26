# "%acccent_color_placeholder%" in QSS below will be replaced by fancy_terminal_accent_color_hex in developer_setting.py if present

# ===============
# individually imported settings

INPUT_PREPEND=">>> "
INPUT_PRINT_BG="%acccent_color_placeholder%" # None for default
INPUT_PRINT_COLOR="contrast" # None for default. "contrast" for a bg with contrast to INPUT_PRINT_BG
ERROR_PRINT_COLOR = "#FF5252" # None for default
ERROR_PRINT_BG = "#FFFFFF" # None for default. "contrast" for a bg with contrast to ERROR_PRINT_COLOR

# ===============
# For QSS below

LIGHT_GRAY = "#D3D3D3"
GRAY = "#C0C0C0"
SLIGHTLY_DARK_GRAY = "#B3B3B3"
DARK_GRAY = "#2E2E2E"
DARKER_GRAY = "#1C1C1C"
DARKEST_GRAY = "#101010"
ALMOST_BLACK = "#050505"

WINDOW_BG = "#1c1b1b"
TOP_BAR_BG = "#1a1919"

BUTTON_TEXT = "#FFFFFF"
BUTTON_BORDER = "#302e2e"
BUTTON_ACTIVELY_RUNNING_BORDER = "#24d62a"

BUTTON_BG = TOP_BAR_BG
BUTTON_ENABLED_BG = TOP_BAR_BG
BUTTON_HOVER_BG = "#000000"
BUTTON_ACTIVELY_RUNNING_BG = TOP_BAR_BG

UNCLICKABLE_BUTTON_BG = "#808080"
UNCLICKABLE_BUTTON_BORDER = "#808080"

MENU_BUTTON_BG = BUTTON_BG
MENU_BUTTON_HOVER_BG = BUTTON_HOVER_BG
MENU_BUTTON_BORDER = BUTTON_BORDER

# ===============

QSS = (
    "QPushButton, QToolButton {"
    "   padding: 4px 4px;"
    f"  background-color: {BUTTON_BG};"
    f"  color: {BUTTON_TEXT};"
    "   font-weight: 600;"
    "   border-radius: 7px;"
    f"  border: 2px solid {DARK_GRAY};"
    f"  border-bottom: 2px solid {ALMOST_BLACK};"
    "}"
    "QPushButton:hover, QToolButton:hover {"
    f"  background-color: {BUTTON_HOVER_BG};"
    "}"
    "QPushButton:checked, QToolButton:checked {"
    "  background-color: transparent;"
    "  border: 2px solid %acccent_color_placeholder%;"
    f"  color: {BUTTON_TEXT};"
    "}"
    "QPushButton[restarting='true'], QToolButton[restarting='true'] {"
    f"  border: 2px solid {BUTTON_ACTIVELY_RUNNING_BORDER};"
    f"  color: {BUTTON_TEXT};"
    "}"
    "QPushButton:disabled, QToolButton:disabled {"
    f"  color: {UNCLICKABLE_BUTTON_BG};"
    "   text-decoration: line-through;"
    f"  border: 2px solid {UNCLICKABLE_BUTTON_BG};"
    "}"
    "QMenu::section {"
    f"  color: {BUTTON_TEXT};"
    "   font-weight: 600;"
    "   padding: 6px 12px;"
    f"  background-color: {WINDOW_BG};"
    "}"
    "QMenu::separator {"
    "   height: 1px;"
    f"  background: {BUTTON_BORDER};"
    "   margin: 4px 8px;"
    "}"
    "QMenu QPushButton, QMenu QToolButton {"
    f"  border: 2px solid {BUTTON_BORDER};"
    "   border-radius: 7px;"
    f"  background-color: {BUTTON_BG};"
    f"  color: {BUTTON_TEXT};"
    "   padding: 4px 4px;"
    "   text-align: left;"
    "   font-weight: 600;"
    "}"
    "QMenu QPushButton:hover, QMenu QToolButton:hover {"
    f"  background-color: {BUTTON_HOVER_BG};"
    "}"
    "QMenu QPushButton:checked, QMenu QToolButton:checked {"
    "   background-color: transparent;"
    "  border: 1px solid %acccent_color_placeholder%;"
    f"  color: {BUTTON_TEXT};"
    "}"
    "QMenu QPushButton[restarting='true'], QMenu QToolButton[restarting='true'] {"
    f"  border: 1px solid {BUTTON_ACTIVELY_RUNNING_BORDER};"
    f"  color: {BUTTON_TEXT};"
    "}"
    "QMenu QPushButton:disabled, QMenu QToolButton:disabled {"
    f"  color: {UNCLICKABLE_BUTTON_BG};"
    "   text-decoration: line-through;"
    f"  border: 1px solid {UNCLICKABLE_BUTTON_BG};"
    "}"
    "QTextEdit {"  # terminal output unselected
    "  selection-background-color: %acccent_color_placeholder%;"
    "   border-radius: 11px;"
    f"  border: 3px solid {DARKEST_GRAY};"
    f"  background-color: {DARK_GRAY};"
    f"  border-bottom: 2px solid {SLIGHTLY_DARK_GRAY};"
    "}"
    "QTextEdit:focus {"  # terminal output selected
    " border-bottom: 2px solid %acccent_color_placeholder%;"
    "}"
    "QLineEdit {"  # terminal input unselected
    "   selection-background-color: %acccent_color_placeholder%;"
    "    border-radius: 7px;"
    f"   border: 1px solid {DARKEST_GRAY};"
    f"   background-color: {DARK_GRAY};"
    f"   border-bottom: 1px solid {SLIGHTLY_DARK_GRAY};"
    "}"
    "QLineEdit:focus {"  # terminal input selected
    f"  background-color: {DARKER_GRAY};"
    "  border-bottom: 1px solid %acccent_color_placeholder%;"
    "}"
)
