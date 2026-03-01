import argparse
import ctypes
import os
import shutil
import subprocess
import sys
import traceback
from ctypes import wintypes

try:
    from typing import override  # Python 3.12+
except ImportError:
    from typing_extensions import override  # Python 3.11 and earlier


from PySide6.QtCore import QProcess, QSignalBlocker, Qt, QTimer
from PySide6.QtGui import QAction, QColor, QIcon, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QScrollBar,
    QSizePolicy,
    QSystemTrayIcon,
    QTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
    QWidgetAction,
)

# Shared Color Palette

ERROR_PRINT = "#FF5252"
INPUT_PRINT = "#6BB6FF"
OUTPUT_PRINT = "#FFFFFF"

WINDOW_BG = "#1c1b1b"
TOP_BAR_BG = "#1a1919"

BUTTON_TEXT = "#FFFFFF"

BUTTON_BORDER = "#302e2e"
BUTTON_ENABLED_BORDER = "#d63c24"
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

CSS = (
    "QPushButton, QToolButton {"
    "  padding: 4px 10px;"
    f"  border: 1px solid {BUTTON_BORDER};"
    "  border-radius: 6px;"
    f"  background-color: {BUTTON_BG};"
    f"  color: {BUTTON_TEXT};"
    "  font-weight: 600;"
    "}"
    "QPushButton:hover, QToolButton:hover {"
    f"  background-color: {BUTTON_HOVER_BG};"
    "}"
    "QPushButton:checked, QToolButton:checked {"
    "  background-color: transparent;"
    f"  border: 1px solid {BUTTON_ENABLED_BORDER};"
    f"  color: {BUTTON_TEXT};"
    "}"
    "QPushButton[restarting='true'], QToolButton[restarting='true'] {"
    f"  border: 1px solid {BUTTON_ACTIVELY_RUNNING_BORDER};"
    f"  color: {BUTTON_TEXT};"
    "}"
    "QPushButton:disabled, QToolButton:disabled {"
    f"  color: {UNCLICKABLE_BUTTON_BG};"
    "  text-decoration: line-through;"
    f"  border: 1px solid {UNCLICKABLE_BUTTON_BG};"
    "}"
    "QMenu::section {"
    f"  color: {BUTTON_TEXT};"
    "  font-weight: 600;"
    "  padding: 6px 12px;"
    f"  background-color: {WINDOW_BG};"
    "}"
    "QMenu::separator {"
    "  height: 1px;"
    f"  background: {BUTTON_BORDER};"
    "  margin: 4px 8px;"
    "}"
    "QMenu QPushButton, QMenu QToolButton {"
    f"  border: 1px solid {BUTTON_BORDER};"
    "  border-radius: 6px;"
    f"  background-color: {BUTTON_BG};"
    f"  color: {BUTTON_TEXT};"
    "  padding: 4px 10px;"
    "  text-align: left;"
    "  font-weight: 600;"
    "}"
    "QMenu QPushButton:hover, QMenu QToolButton:hover {"
    f"  background-color: {BUTTON_HOVER_BG};"
    "}"
    "QMenu QPushButton:checked, QMenu QToolButton:checked {"
    "  background-color: transparent;"
    f"  border: 1px solid {BUTTON_ENABLED_BORDER};"
    f"  color: {BUTTON_TEXT};"
    "}"
    "QMenu QPushButton[restarting='true'], QMenu QToolButton[restarting='true'] {"
    f"  border: 1px solid {BUTTON_ACTIVELY_RUNNING_BORDER};"
    f"  color: {BUTTON_TEXT};"
    "}"
    "QMenu QPushButton:disabled, QMenu QToolButton:disabled {"
    f"  color: {UNCLICKABLE_BUTTON_BG};"
    "  text-decoration: line-through;"
    f"  border: 1px solid {UNCLICKABLE_BUTTON_BG};"
    "}"
)


class Input_line(QLineEdit):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.history: list[str] = []
        self.history_index: int = 0
        self.current_text_buffer: str = ""

    def add_to_history(self, text: str) -> None:
        if text.strip() and (not self.history or self.history[-1] != text):
            self.history.append(text)
        self.history_index = len(self.history)
        self.current_text_buffer = ""

    @override
    def keyPressEvent(self, event) -> None:
        if not self.history:
            super().keyPressEvent(event)
            return

        if event.key() == Qt.Key.Key_Up:
            if self.history_index == len(self.history):
                self.current_text_buffer = self.text()

            if self.history_index > 0:
                self.history_index -= 1
                self.setText(self.history[self.history_index])

        elif event.key() == Qt.Key.Key_Down:
            if self.history_index < len(self.history) - 1:
                self.history_index += 1
                self.setText(self.history[self.history_index])
            elif self.history_index == len(self.history) - 1:
                self.history_index += 1
                self.setText(self.current_text_buffer)

        else:
            super().keyPressEvent(event)


class Terminal_window(QMainWindow):
    def __init__(
        self,
        script_path: str,
        icon_path: str | None = None,
        title: str | None = None,
        width: int = 900,
        height: int = 600,
        button_settings: dict[str, dict] | None = None,
    ) -> None:

        #######################
        # local settings

        base_default_button_settings: dict[str, bool] = {
            "visible": True,
            "clickable": True,
            "pinned": True,
            "unpin_able": True,
            "starting_state": False,  # For checkable buttons
        }

        # don't have to define empty dicts:
        altered_default_button_settings: list[tuple[str, dict[str, bool]]] = [
            ("show_input", {"pinned": False, "starting_state": True}),
            ("autoscroll", {"starting_state": True}),
            ("foreground_on_print", {"pinned": False}),
            ("highlight_on_print", {"pinned": False}),
            ("confirm_close", {"pinned": False}),
            ("restart", {}),
            ("clear", {}),
            ("stop", {"visible": True}),
            ("to_tray", {"clickable": True}),
            ("open_script", {"pinned": False}),
        ]

        self._pin_symbol_on = "\N{PUSHPIN}"
        self._pin_symbol_off = "\N{ROUND PUSHPIN}"

        #######################
        # initialize window

        super().__init__()

        #######################
        # process parameters

        script_path = os.path.abspath(script_path)
        self.script_path = script_path

        # Create the final default settings dictionary (label: settings_dict) with fallback base_default_button_settings if not defined in altered_default_button_settings
        default_button_settings: dict[str, dict[str, bool]] = {
            label: {**base_default_button_settings, **overrides} for label, overrides in altered_default_button_settings
        }
        if button_settings is None:
            button_settings = {}
        # add default settings to undefined button_settings
        for label, default in default_button_settings.items():
            button_settings[label] = {**default, **button_settings.get(label, {})}
        for label, dictionary in button_settings.items():
            if label not in default_button_settings:
                button_settings[label] = {**base_default_button_settings, **dictionary}
        self.button_settings = button_settings

        if not os.path.isfile(script_path):
            print(f"[Error] File not found: {script_path}")
            print("Aborting. Press enter to exit.")
            input()
            sys.exit(1)

        if icon_path is None:
            fallback_icon = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "fallback_terminal_icon.ico",
            )
            if os.path.isfile(fallback_icon):
                icon_path = fallback_icon
            else:
                icon_path = None
        self.start_icon_path = icon_path
        self.set_icon(icon_path)

        if title is None:
            title = f"{os.path.basename(script_path)}"
        self.start_title = title
        self.set_title(title)

        self.start_width = width
        self.start_height = height
        self.set_size(width, height)

        ###################
        # terminal output

        self._terminal_output = QTextEdit()
        self._terminal_output.setReadOnly(True)
        self._terminal_output_entries: list[tuple[str, QColor | None, bool]] = []

        ###################
        # top bar

        self._top_bar_widget = QWidget(self)
        self._top_bar_widget.setStyleSheet(CSS)
        self._top_bar = QHBoxLayout(self._top_bar_widget)
        self._top_bar.setContentsMargins(8, 6, 8, 6)
        self._top_bar.setSpacing(6)

        ###################
        # setup buttons

        self._clear_button = self._add_button("Clear", "clear")
        self._clear_button.clicked.connect(self.clear_terminal)
        self._clear_button.setToolTip("Clear the terminal")

        self._restart_button = self._add_button("Restart", "restart")
        self._restart_button.clicked.connect(self.restart_script)
        self._restart_button.setToolTip("Restart the script")

        self._stop_button = self._add_button("Stop", "stop")
        self._stop_button.clicked.connect(self.stop_script)
        self._stop_button.setToolTip("Stop the running script")

        self._autoscroll_button = self._add_button("Autoscroll", "autoscroll", True)
        self._autoscroll_button.setToolTip("Disable auto-scrolling to bottom")

        self._to_tray_button = self._add_button("To Tray", "to_tray")
        self._to_tray_button.clicked.connect(self.set_window_system_tray)
        self._to_tray_button.setToolTip("Minimize window to system tray")

        self._show_input_button = self._add_button("Show Input", "show_input", True)
        self._show_input_button.clicked.connect(self.set_show_input_state)
        self._show_input_button.setToolTip("Show user input lines")

        self._foreground_on_print_button = self._add_button("Fg on Print", "foreground_on_print", True)
        self._foreground_on_print_button.setToolTip("Bring window to foreground when script prints")

        self._highlight_on_print_button = self._add_button("Hl on Print", "highlight_on_print", True)
        self._highlight_on_print_button.setToolTip("Flash taskbar icon when script prints")

        self._confirm_close_button = self._add_button("Confirm Close", "confirm_close", True)
        self._confirm_close_button.setToolTip("Ask for confirmation before closing the window")

        self._open_script_button = self._add_button("Open Script", "open_script")
        self._open_script_button.setToolTip("Open the Python script that this terminal emulator is running")
        self._open_script_button.clicked.connect(self.open_python_script_in_editor)

        ###################
        # set up menu

        # menu dropdown

        self._menu_dropdown = QMenu(self)
        self._menu_dropdown.addSection("Top Bar Controls")
        self._menu_dropdown.setStyleSheet(CSS)
        self._menu_dropdown.aboutToShow.connect(self._refresh_menu_controls)

        self._menu_pin_buttons: dict[str, QToolButton] = {}
        self._menu_buttons: dict[str, QPushButton] = {}
        self._menu_entries: dict[str, QWidgetAction] = {}
        for label, button in self._buttons.items():
            # row_widget inside thte menu dropdown consists of the button and the pin button.
            menu_row_widget = QWidget(self._menu_dropdown)
            menu_row_layout = QHBoxLayout(menu_row_widget)
            menu_row_layout.setContentsMargins(8, 2, 8, 2)
            menu_row_layout.setSpacing(6)

            menu_row_button = QPushButton(button.text())
            menu_row_button.setToolTip(button.toolTip())
            menu_row_button.setEnabled(button.isEnabled())
            if button.isCheckable():
                menu_row_button.setCheckable(True)
                menu_row_button.setChecked(button.isChecked())

            if label == "restart":
                menu_row_button.setObjectName("restart_menu_button")

            menu_row_button.setMinimumWidth(130)
            menu_row_button.clicked.connect(lambda _=False, button_name=label: self._press_button_in_menu(button_name))
            menu_row_layout.addWidget(menu_row_button, 1)
            self._menu_buttons[label] = menu_row_button

            if button_settings[label]["unpin_able"] == True:
                menu_row_pin_button = QToolButton()
                menu_row_pin_button.setCheckable(True)
                menu_row_pin_button.setChecked(button_settings[label]["pinned"])
                menu_row_pin_button.clicked.connect(
                    lambda checked, button_label=label: self.set_button_pinned_state(button_label, checked)
                )
                menu_row_pin_button.setToolTip("Pin or unpin from top bar")
                self._menu_pin_buttons[label] = menu_row_pin_button
                menu_row_layout.addWidget(menu_row_pin_button)

            menu_row_action = QWidgetAction(self._menu_dropdown)
            menu_row_action.setDefaultWidget(menu_row_widget)
            self._menu_dropdown.addAction(menu_row_action)

            # set visible states
            menu_row_action.setVisible(button_settings[label]["visible"])

            self._menu_entries[label] = menu_row_action

        # menu button

        self._menu_button = QToolButton(self._top_bar_widget)
        self._menu_button.setToolTip("Show all controls")
        self._menu_button.setText("Menu")
        self._menu_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self._menu_button.setMenu(self._menu_dropdown)
        self._menu_button.setMinimumWidth(56)
        self._menu_button.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        # self._menu_button.clicked.connect(lambda _=False: self._refresh_menu_controls())

        ###################
        # set up input bar

        self.input_line = Input_line()
        self.input_line.setPlaceholderText("Type input for the running script and press Enter...")
        self.input_line.returnPressed.connect(self.enter_input)

        input_row = QHBoxLayout()
        input_row.addWidget(QLabel(">"))
        input_row.addWidget(self.input_line)

        ###################
        # set up layout

        layout = QVBoxLayout()
        layout.addWidget(self._top_bar_widget)
        layout.addWidget(self._terminal_output)
        layout.addLayout(input_row)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        ###################
        # set up system tray

        self._window_is_in_tray = False
        self.tray_icon = QSystemTrayIcon(self)
        if self.start_icon_path:
            self.tray_icon.setIcon(QIcon(self.start_icon_path))
        else:
            # use fallback or just window icon
            self.tray_icon.setIcon(self.windowIcon())

        self.tray_menu = QMenu()
        restore_action = QAction("Restore", self)
        restore_action.triggered.connect(self.undo_set_window_system_tray)
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(QApplication.quit)

        self.tray_menu.addAction(restore_action)
        self.tray_menu.addSeparator()
        self.tray_menu.addAction(quit_action)
        self.tray_icon.setContextMenu(self.tray_menu)

        self.tray_icon.activated.connect(self._on_tray_icon_activated)

        ###################
        # set up quit handler

        app = QApplication.instance()
        if app:
            app.aboutToQuit.connect(self._cleanup)

        ###################
        # build top bar and dropdown menu

        self._refresh_menu_controls()
        self._refresh_top_bar()

        #######################
        # miscelaneous attributes

        self._window_is_closing = False
        self._go_to_bottom_on_next_text_print = False

        ###################
        # set up thread for running python script and start script

        self.process = QProcess(self)
        self.process.readyReadStandardOutput.connect(self._read_stdout)
        self.process.readyReadStandardError.connect(self._read_stderr)
        self.process.finished.connect(self._on_finished)

        self.start_script()

    ##################
    # methods
    ##################

    #################
    # buttons methods
    #################

    ###############
    # specific button state setters

    def set_autoscroll_state(self, state: bool) -> None:
        if self.get_autoscroll_state() != state:
            self._autoscroll_button.setChecked(state)
            self._restyle(self._autoscroll_button)

    def set_show_input_state(self, state: bool) -> None:
        if self.get_show_input_state() != state:
            self._show_input_button.setChecked(state)
            self._restyle(self._show_input_button)
            self._refresh_terminal_output()

    def set_highlight_on_print_state(self, state: bool) -> None:
        if self.get_highlight_on_print_state() != state:
            self._highlight_on_print_button.setChecked(state)
            self._restyle(self._highlight_on_print_button)

    def set_foreground_on_print_state(self, state: bool) -> None:
        if self.get_foreground_on_print_state() != state:
            self._foreground_on_print_button.setChecked(state)
            self._restyle(self._foreground_on_print_button)

    ###############
    # specific button state getters

    def get_highlight_on_print_state(self) -> bool:
        return self._highlight_on_print_button.isChecked()

    def get_foreground_on_print_state(self) -> bool:
        return self._foreground_on_print_button.isChecked()

    def get_autoscroll_state(self) -> bool:
        return self._autoscroll_button.isChecked()

    def get_show_input_state(self) -> bool:
        return self._show_input_button.isChecked()

    ###############
    # specific button state togglers

    def toggle_autoscroll(self) -> None:
        self.set_autoscroll_state(not self.get_autoscroll_state())

    def toggle_show_input(self) -> None:
        self.set_show_input_state(not self.get_show_input_state())

    def toggle_highlight_on_print(self) -> None:
        self.set_highlight_on_print_state(not self.get_highlight_on_print_state())

    def toggle_foreground_on_print(self) -> None:
        self.set_foreground_on_print_state(not self.get_foreground_on_print_state())

    ###############
    # general button miscellaneous

    def press_button(self, label: str) -> None:
        btn = self.get_button_widget(label)
        if btn.isCheckable():
            btn.setChecked(not btn.isChecked())
        else:
            btn.click()

    ###############
    # general button related setters

    def set_button_clickable_state(self, label: str, enabled: bool) -> None:
        self._buttons[label].setEnabled(enabled)
        self._menu_buttons[label].setEnabled(enabled)

    def set_button_state_and_trigger_on_change(self, label: str, enabled: bool) -> None:
        if self._buttons[label].isChecked() != enabled:
            self.press_button(label)

    def set_button_pinned_state(self, label: str, checked: bool) -> None:
        self._button_pin_states[label] = checked
        self._refresh_menu_controls()
        self._refresh_top_bar()

    def set_button_visible_state(self, label: str, visible: bool) -> None:
        self._button_visible_states[label] = visible
        self._menu_entries[label].setVisible(visible)
        self._refresh_top_bar()

    ###############
    # general button related getters

    def get_button_widget(self, label: str) -> QPushButton:
        return self._buttons[label]

    def get_button_clickable_state(self, label: str) -> bool:
        return self._buttons[label].isEnabled()

    def get_button_pinned_state(self, label: str) -> bool:
        return self._button_pin_states[label]

    def get_button_state(self, label: str) -> bool:
        return self._buttons[label].isChecked()

    def get_button_visible_state(self, label: str) -> bool:
        return self._buttons[label].isVisible()

    ###############
    # general button related togglers

    def toggle_button_clickable_state(self, label: str):
        self.set_button_clickable_state(label, not self.get_button_clickable_state(label))

    def toggle_button_pinned_state(self, label: str):
        self.set_button_pinned_state(label, not self.get_button_pinned_state(label))

    def toggle_button_state(self, label: str):
        self.set_button_state_and_trigger_on_change(label, not self.get_button_state(label))

    def toggle_button_visible_state(self, label: str):
        self.set_button_visible_state(label, not self.get_button_visible_state(label))

    #################
    # terminal (output field) related

    def clear_terminal(self) -> None:
        self._terminal_output_entries.clear()
        self._terminal_output.clear()

    def terminal_print(
        self,
        text: str,
        color: QColor | None = None,
        is_user_input: bool = False,
        always_go_to_bottom_for_user_input: bool = True,
        error=False,
    ) -> None:

        if error == True:
            color = QColor(ERROR_PRINT)

        self._terminal_output_entries.append((text, color, is_user_input))

        if is_user_input and always_go_to_bottom_for_user_input:
            self.go_to_terminal_bottom()
            # Only force-follow if we will actually insert text
            self._go_to_bottom_on_next_text_print = self.get_show_input_state()

        if is_user_input and not self.get_show_input_state():
            self._go_to_bottom_on_next_text_print = False
            return

        self._insert_text(text, color)

    def go_to_terminal_bottom(self) -> None:
        sb = self._terminal_output.verticalScrollBar()
        with QSignalBlocker(sb):
            sb.setValue(sb.maximum())

    ###############
    # input bar related

    def clear_input(self) -> None:
        self.input_line.clear()

    def enter_input(self) -> None:
        text = self.input_line.text()
        if not self.process or self.process.state() != QProcess.ProcessState.Running:
            return

        self.process.write((text + "\n").encode())
        self.terminal_print(f"{text}\n", QColor(INPUT_PRINT), is_user_input=True)
        self.input_line.add_to_history(text)
        self.clear_input()

    ###############
    # window related general setters

    def set_icon(self, icon_path: str | None) -> None:
        """resets to start icon if icon_path is None"""
        if icon_path is not None:
            self.icon_path = icon_path
            self.setWindowIcon(QIcon(icon_path))
        elif self.start_icon_path is not None:
            self.icon_path = self.start_icon_path
            self.setWindowIcon(QIcon(self.start_icon_path))

    def set_title(self, title: str | None) -> None:
        if title is not None:
            self.setWindowTitle(title)
        elif self.start_title is not None:
            self.setWindowTitle(self.start_title)

    def set_size(self, width: int | None, height: int | None) -> None:
        if width is None:
            width = self.start_width
        if height is None:
            height = self.start_height

        self.resize(width, height)

    ###############
    # window related general getters

    def get_icon(self) -> str:
        return self.icon_path

    def get_title(self) -> str:
        return self.windowTitle()

    def get_size(self) -> tuple[int, int]:
        return self.size().width(), self.size().height()

    ###############
    # taskbar/system tray related

    def set_window_system_tray(self) -> None:
        self._window_is_in_tray = True
        self.hide()
        self.tray_icon.show()

    def undo_set_window_system_tray(self) -> None:
        self._window_is_in_tray = False
        self.show()
        self.activateWindow()
        self.raise_()
        self.tray_icon.hide()

    def set_window_minimized(self) -> None:
        if self._window_is_in_tray == True:
            self.undo_set_window_system_tray()
        self.showMinimized()

    def set_window_normal(self) -> None:
        if self._window_is_in_tray == True:
            self.undo_set_window_system_tray()
        self.showNormal()

    def set_window_maximized(self) -> None:
        if self._window_is_in_tray == True:
            self.undo_set_window_system_tray()
        self.showMaximized()

    ###############
    # highlighting related

    def window_is_active(self) -> bool:
        return QApplication.applicationState() == Qt.ApplicationState.ApplicationActive

    def bring_window_to_front(self) -> None:
        """
        Force the window to the foreground on Windows, bypassing focus stealing prevention.
        """
        if self._window_is_closing:
            return

        # Ensure window is shown and not minimized
        if self.isMinimized():
            self.set_window_normal()

        self.show()
        self.raise_()
        self.activateWindow()

        # Windows-specific force focus
        if os.name == "nt":
            try:
                hwnd = int(self.winId())
                # SW_RESTORE = 9
                ctypes.windll.user32.ShowWindow(hwnd, 9)
                ctypes.windll.user32.SetForegroundWindow(hwnd)
            except Exception:
                pass

    def highlight_in_taskbar(self) -> None:
        QApplication.alert(self)

    def flash_in_taskbar(self, flashes: int = 5, timeout_ms: int = 0, until_foreground: bool = False) -> None:
        """
        Windows-only. Flashes the taskbar button.

        flashes:
        - if until_foreground=False: number of flashes (best-effort; OS may stop early if focused)
        - if until_foreground=True: keep flashing until window becomes foreground

        timeout_ms:
        - 0 lets Windows choose the default cursor blink rate.
        - otherwise sets the flash rate in ms (Windows may still clamp/ignore).
        """
        if os.name != "nt":
            # Fallback for non-Windows
            QApplication.alert(self)
            return

        hwnd = int(self.winId())
        user32 = ctypes.windll.user32

        FLASHW_TRAY = 0x00000002
        FLASHW_TIMERNOFG = 0x0000000C  # TIMER | (no foreground stop)

        class FLASHWINFO(ctypes.Structure):
            _fields_ = [
                ("cbSize", wintypes.UINT),
                ("hwnd", wintypes.HWND),
                ("dwFlags", wintypes.DWORD),
                ("uCount", wintypes.UINT),
                ("dwTimeout", wintypes.DWORD),
            ]

        # If you want EXACT count, do NOT use TIMER/TIMERNOFG because then uCount is ignored.
        if until_foreground:
            flags = FLASHW_TRAY | FLASHW_TIMERNOFG
            count = 0  # ignored when TIMERNOFG is used
        else:
            flags = FLASHW_TRAY
            count = max(1, int(flashes))

        info = FLASHWINFO(
            cbSize=ctypes.sizeof(FLASHWINFO),
            hwnd=hwnd,
            dwFlags=flags,
            uCount=count,
            dwTimeout=max(0, int(timeout_ms)),
        )
        user32.FlashWindowEx(ctypes.byref(info))

    def stop_flash_in_taskbar(self) -> None:
        """Windows-only. Stops any ongoing FlashWindowEx flashing."""
        if os.name != "nt":
            return

        hwnd = int(self.winId())
        user32 = ctypes.windll.user32

        FLASHW_STOP = 0

        class FLASHWINFO(ctypes.Structure):
            _fields_ = [
                ("cbSize", wintypes.UINT),
                ("hwnd", wintypes.HWND),
                ("dwFlags", wintypes.DWORD),
                ("uCount", wintypes.UINT),
                ("dwTimeout", wintypes.DWORD),
            ]

        info = FLASHWINFO(
            cbSize=ctypes.sizeof(FLASHWINFO),
            hwnd=hwnd,
            dwFlags=FLASHW_STOP,
            uCount=0,
            dwTimeout=0,
        )
        user32.FlashWindowEx(ctypes.byref(info))

    ###############
    # script related

    def open_python_script_in_editor(self):
        try:
            if not os.path.exists(self.script_path):
                print(f"Could not find file at path: {self.script_path}")

            vscode_exe_path = shutil.which("code")
            if vscode_exe_path is not None:
                subprocess.Popen([vscode_exe_path, self.script_path])  # noqa:S603
            else:
                # Fallback
                subprocess.Popen(["notepad.exe", self.script_path])  # noqa:S603
        except Exception as m:
            self.terminal_print(traceback.format_exc(), error=True)

    def start_script(self) -> None:
        if self.process.state() != QProcess.ProcessState.NotRunning:
            self.stop_script()

        # Clear restart button state if it was clicked
        for btn in [self._buttons["restart"], self._menu_buttons["restart"]]:
            if btn:
                btn.setProperty("restarting", "false")
                btn.style().unpolish(btn)
                btn.style().polish(btn)

        python_exe = sys.executable or "python"
        self.process.start(python_exe, [self.script_path])
        self.input_line.setEnabled(True)
        self.set_button_clickable_state("stop", True)
        if not self.process.waitForStarted(3000):
            self.terminal_print("Failed to start process.\n", error=True)
            self.input_line.setEnabled(False)
            self.set_button_clickable_state("stop", False)

    def stop_script(self) -> None:
        if self.process.state() != QProcess.ProcessState.NotRunning:
            self.process.terminate()
            if not self.process.waitForFinished(2000):
                self.process.kill()
                self.process.waitForFinished(1000)

    def restart_script(self) -> None:
        # Set restarting visual state
        for btn in [self._restart_button, self._menu_buttons.get("restart")]:
            if btn:
                btn.setProperty("restarting", "true")
                btn.style().unpolish(btn)
                btn.style().polish(btn)

        QApplication.processEvents()
        self.stop_script()
        self.clear_terminal()
        self.set_title(None)
        self.set_icon(None)
        self.start_script()

    ###############
    # backend

    def _restyle(self, w: QWidget) -> None:
        w.style().unpolish(w)
        w.style().polish(w)
        w.update()

    def _sync_menu_button_checked(self, label: str, checked: bool) -> None:
        menu_btn = self._menu_buttons.get(label)
        if not menu_btn:
            return

        menu_btn.blockSignals(True)
        menu_btn.setChecked(checked)
        menu_btn.blockSignals(False)

        # force visual refresh on the MENU button
        menu_btn.style().unpolish(menu_btn)
        menu_btn.style().polish(menu_btn)
        menu_btn.update()

    def _press_button_in_menu(self, label: str) -> None:
        self.press_button(label)
        self._refresh_menu_controls()

    def _add_button(self, button_text: str, button_label: str, checkable: bool = False):
        # add attributes if missing
        if not hasattr(self, "_buttons"):
            self._buttons: dict[str, QPushButton] = {}
        if not hasattr(self, "_button_pin_states"):
            self._button_pin_states: dict[str, bool] = {}
        if not hasattr(self, "_button_visible_states"):
            self._button_visible_states: dict[str, bool] = {}

        button = QPushButton(button_text, self._top_bar_widget)
        button.hide()  # <-- important: prevent overlap until layout adds it
        button.setMinimumWidth(32)
        button.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        if checkable == True:
            button.setCheckable(True)
            button.setChecked(self.button_settings[button_label]["starting_state"])
            button.toggled.connect(lambda checked, lab=button_label: self._sync_menu_button_checked(lab, checked))
        button.setEnabled(self.button_settings[button_label]["clickable"])
        self._button_pin_states[button_label] = self.button_settings[button_label]["pinned"]
        self._button_visible_states[button_label] = self.button_settings[button_label]["visible"]

        # add button to list
        self._buttons[button_label] = button

        return button

    def _on_tray_icon_activated(self, reason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.undo_set_window_system_tray()

    def _insert_text(self, text: str, color: QColor | None = None) -> None:
        if self.get_highlight_on_print_state():
            self.highlight_in_taskbar()
            if not self.window_is_active():
                self.flash_in_taskbar(flashes=5, until_foreground=False)
        if self.get_foreground_on_print_state():
            self.bring_window_to_front()

        sb: QScrollBar = self._terminal_output.verticalScrollBar()

        follow = self.get_autoscroll_state() or self._go_to_bottom_on_next_text_print

        old_scroll = sb.value()
        old_cursor = self._terminal_output.textCursor()  # keep selection/caret if you want

        # Insert at document end using a document cursor
        doc_cursor = QTextCursor(self._terminal_output.document())
        doc_cursor.movePosition(QTextCursor.MoveOperation.End)

        fmt = QTextCharFormat()
        if color is not None:
            fmt.setForeground(color)

        doc_cursor.insertText(text, fmt)

        # Always clear one-shot flag
        self._go_to_bottom_on_next_text_print = False

        if follow:
            # Scroll to bottom (don't rely on ensureCursorVisible in non-follow mode)
            sb.setValue(sb.maximum())
            return

        # Autoscroll OFF:
        # Restore view AFTER Qt updates layout; also avoid calling ensureCursorVisible().
        def restore_view() -> None:
            # restore scroll first
            with QSignalBlocker(sb):
                sb.setValue(old_scroll)

        # optional: restore cursor without forcing scroll
        # (this can still move view in some cases; remove if it causes jumping)
        self._terminal_output.setTextCursor(old_cursor)
        with QSignalBlocker(sb):
            sb.setValue(old_scroll)

        QTimer.singleShot(0, restore_view)

    def _refresh_terminal_output(self) -> None:
        self._terminal_output.clear()
        for text, color, is_user_input in self._terminal_output_entries:
            if is_user_input and not self.get_show_input_state():
                continue
            self._insert_text(text, color)

    def _refresh_menu_controls(self) -> None:
        # Sync pin buttons
        for label, pin_button in self._menu_pin_buttons.items():
            is_pinned = self._button_pin_states.get(label, False)

            pin_button.setChecked(is_pinned)
            pin_button.setText(self._pin_symbol_on if is_pinned else self._pin_symbol_off)

        # Sync menu dropdown buttons state
        for label, button_in_menu in self._menu_buttons.items():
            button_in_menu.setChecked(self._buttons[label].isChecked())

    def _refresh_top_bar(self) -> None:
        # remove all items from the layout except the menu button
        while self._top_bar.count() > 0:
            _item = self._top_bar.takeAt(0)

        # re add menu button in top bar
        self._menu_button.show()
        self._top_bar.addWidget(self._menu_button)

        # show pinned buttons, hide unpinned (prevents overlap)
        for label, button in self._buttons.items():
            if self._button_pin_states[label] and self._button_visible_states[label]:
                button.show()
                self._top_bar.addWidget(button)
            else:
                button.hide()

        self._top_bar.addStretch()

    def _read_stdout(self) -> None:
        msg = bytes(self.process.readAllStandardOutput()).decode(errors="replace")  # type: ignore

        if msg.startswith("Terminal_window."):
            rest = msg[len("Terminal_window."):]
            try:
                eval(f"self.{rest}")
            except Exception as m:
                self.terminal_print(traceback.format_exc(), error=True)

        else:
            self.terminal_print(msg)

    def _read_stderr(self) -> None:
        data = bytes(self.process.readAllStandardError()).decode(errors="replace")  # type: ignore
        self.terminal_print(data, error=True)

    def _on_finished(self, exit_code: int, _exit_status: QProcess.ExitStatus) -> None:
        self.terminal_print(f"\n\n[process exited with code {exit_code}]\n", error=(exit_code != 0))
        self.input_line.setEnabled(False)
        self.set_button_clickable_state("stop", False)

    def _cleanup(self) -> None:
        if self._window_is_closing:
            return
        self._window_is_closing = True

        try:
            self.tray_icon.hide()
        except RuntimeError:
            pass

        if self.process.state() != QProcess.ProcessState.NotRunning:
            self.process.terminate()
            if not self.process.waitForFinished(1000):
                self.process.kill()
                self.process.waitForFinished(1000)

    ###############
    # Qt overrides

    @override
    def closeEvent(self, event) -> None:
        if self._confirm_close_button.isChecked():
            reply = QMessageBox.question(
                self,
                "Confirm Exit",
                "Are you sure you want to close the terminal?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.No:
                event.ignore()
                return

        self._cleanup()
        super().closeEvent(event)


###########################


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Simple PySide6 terminal emulator for running a Python script.")
    parser.add_argument("script_path", help="Path to the Python script to run")
    parser.add_argument(
        "--icon",
        help="Path to window icon file (.ico). If omitted, fallback_terminal_icon.ico is used when available.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    script_path = args.script_path
    icon_path = args.icon

    app = QApplication(sys.argv)
    window = Terminal_window(script_path, icon_path=icon_path)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
