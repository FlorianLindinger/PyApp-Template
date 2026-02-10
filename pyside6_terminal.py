"""
PySide6 "terminal-like" window that runs a Python script using a DIFFERENT Python runtime.

What this does:
- Creates a PySide6 window that mimics a basic Windows Terminal console (monospace output + input line).
- Launches an external Python interpreter (you choose the python.exe path or "py").
- Streams stdout/stderr into the window.
- Sends what you type to the process stdin (line-based).

Limitations:
- Not a full PTY/ConPTY terminal emulator. Cursor control, ANSI, full-screen TUIs won't behave like a real terminal.
- Best for line-oriented scripts (print/input), logs, REPL-ish output.

Usage:
  python qt_terminal_runner_pyside6.py <script_path> --python "C:\\Python311\\python.exe" --work_dir "C:\\path" -- arg1 arg2
  python qt_terminal_runner_pyside6.py <script_path> --python py --app_id "My.App.Id" -- --arg1 foo

Requires:
  pip install PySide6
"""

from __future__ import annotations

import ctypes
import os
import sys
import traceback
from typing import Optional

from PySide6.QtCore import QProcess, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

COLORS = {
    "WINDOW_BG": "#1e1e1e",
    "TEXT_MAIN": "#cccccc",
    "TEXT_DIM": "#888888",
    "STDOUT": "#d4d4d4",
    "STDERR": "#ff6b6b",
    "INPUT_ECHO": "#3794ff",
    "SUCCESS": "#00ff00",
    "SELECTION_BG": "#264f78",
    "SCROLLBAR_HANDLE": "#424242",
    "SCROLLBAR_HANDLE_HOVER": "#4f4f4f",
    "INPUT_BG": "#252526",
    "INPUT_BORDER": "#3c3c3c",
    "INPUT_FOCUS_BORDER": "#007fd4",
    "BUTTON_BG": "#0e639c",
    "BUTTON_HOVER": "#1177bb",
    "BUTTON_PRESSED": "#094771",
    "BUTTON_DISABLED": "#333333",
    "PROMPT": "#0e639c",
}

STYLESHEET = """
/* Global Window */
QMainWindow {{
    background-color: {WINDOW_BG};
}}
QWidget {{
    background-color: {WINDOW_BG};
    color: {TEXT_MAIN};
    font-family: 'Segoe UI', sans-serif;
    font-size: 14px;
}}

/* Headings/Labels */
QLabel {{
    color: {TEXT_MAIN};
    font-weight: 500;
}}

/* Output Area */
QPlainTextEdit {{
    background-color: {WINDOW_BG};
    color: {STDOUT};
    border: none;
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 14px;
    selection-background-color: {SELECTION_BG};
    padding: 10px;
}}
QPlainTextEdit:focus {{
    border: none;
}}

/* ScrollBar */
QScrollBar:vertical {{
    border: none;
    background: {WINDOW_BG};
    width: 14px;
    margin: 0px 0px 0px 0px;
}}
QScrollBar::handle:vertical {{
    background: {SCROLLBAR_HANDLE};
    min-height: 20px;
    border-radius: 7px;
    margin: 2px;
}}
QScrollBar::handle:vertical:hover {{
    background: {SCROLLBAR_HANDLE_HOVER};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: none;
}}

/* Input Area */
QLineEdit {{
    background-color: {INPUT_BG};
    color: {STDOUT};
    border: 1px solid {INPUT_BORDER};
    border-radius: 4px;
    padding: 8px;
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 14px;
    selection-background-color: {SELECTION_BG};
}}
QLineEdit:focus {{
    border: 1px solid {INPUT_FOCUS_BORDER};
}}

/* Buttons */
QPushButton {{
    background-color: {BUTTON_BG};
    color: white;
    border: none;
    padding: 8px 16px;
    border-radius: 4px;
    font-weight: bold;
}}
QPushButton:hover {{
    background-color: {BUTTON_HOVER};
}}
QPushButton:pressed {{
    background-color: {BUTTON_PRESSED};
}}
QPushButton:disabled {{
    background-color: {BUTTON_DISABLED};
    color: {TEXT_DIM};
}}
""".format(**COLORS)


class TerminalEmulator(QMainWindow):
    def __init__(
        self,
        python_exe: str,
        script_path: str,
        args: list[str],
        working_directory: Optional[str] = None,
        close_on_success: bool = True,
        no_input: bool = False,
    ):
        super().__init__()
        self.python_exe = python_exe
        self.script_path = script_path
        self.args = args
        self.working_directory = working_directory
        self.close_on_success = close_on_success
        self.no_input = no_input

        self.waiting_for_exit = False

        self.setWindowTitle("PySide6 Terminal Emulator")
        self.resize(1000, 700)
        self.setStyleSheet(STYLESHEET)

        self.proc = QProcess(self)
        self.proc.readyReadStandardOutput.connect(self._on_stdout)
        self.proc.readyReadStandardError.connect(self._on_stderr)
        self.proc.started.connect(self._on_started)
        self.proc.finished.connect(self._on_finished)
        self.proc.errorOccurred.connect(self._on_error)

        self._build_ui()
        self._start_process()

    def _build_ui(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        self.output.setUndoRedoEnabled(False)

        mono = QFont("Consolas")
        if not mono.exactMatch():
            mono = QFont("Courier New")
        mono.setStyleHint(QFont.StyleHint.Monospace)
        mono.setPointSize(11)
        self.output.setFont(mono)

        layout.addWidget(self.output, 1)

        if not self.no_input:
            input_row = QHBoxLayout()
            input_row.setSpacing(10)

            self.prompt = QLabel(">")
            self.prompt.setFont(mono)
            self.prompt.setStyleSheet(f"color: {COLORS['PROMPT']}; font-weight: bold;")
            input_row.addWidget(self.prompt)

            self.input = QLineEdit()
            self.input.setFont(mono)
            self.input.setPlaceholderText("Type command here...")
            self.input.returnPressed.connect(self._send_line)
            input_row.addWidget(self.input, 1)

            self.btn_send = QPushButton("Send")
            self.btn_send.setCursor(Qt.CursorShape.PointingHandCursor)
            self.btn_send.clicked.connect(self._send_line)
            input_row.addWidget(self.btn_send)

            layout.addLayout(input_row)

    def _append_text(self, text: str, color: Optional[str] = None) -> None:
        if not text:
            return
        self.output.moveCursor(QTextCursor.MoveOperation.End)
        cursor = self.output.textCursor()

        fmt = QTextCharFormat()
        if color:
            fmt.setForeground(QColor(color))
        else:
            # Default color matching the stylesheet
            fmt.setForeground(QColor(COLORS["STDOUT"]))

        cursor.insertText(text, fmt)
        self.output.moveCursor(QTextCursor.MoveOperation.End)

    def _append_line(self, line: str, color: Optional[str] = None) -> None:
        self._append_text(line + ("" if line.endswith("\n") else "\n"), color)

    def _start_process(self) -> None:
        # Validate paths early
        if self.python_exe != "py" and not os.path.isfile(self.python_exe):
            QMessageBox.critical(self, "Invalid Python", f"Python runtime not found:\n{self.python_exe}")
            return
        if not os.path.isfile(self.script_path):
            QMessageBox.critical(self, "Invalid Script", f"Script not found:\n{self.script_path}")
            return

        process_args = list(self.args)

        self.output.clear()

        # Unbuffered so output appears immediately.
        args = ["-u", self.script_path, *process_args]

        # Working directory
        if self.working_directory:
            workdir = self.working_directory
        else:
            workdir = os.path.dirname(os.path.abspath(self.script_path))
        self.proc.setWorkingDirectory(workdir)

        self.proc.start(self.python_exe, args)
        if not self.no_input:
            QTimer.singleShot(0, self.input.setFocus)

    def restart_process(self) -> None:
        self.stop_process()
        self._start_process()

    def stop_process(self) -> None:
        if self.proc.state() == QProcess.ProcessState.NotRunning:
            return
        self._append_line("\n[Stopping process...]")
        self.proc.terminate()
        if not self.proc.waitForFinished(1500):
            self.proc.kill()
            self.proc.waitForFinished(1500)

    def closeEvent(self, event) -> None:
        self.stop_process()
        super().closeEvent(event)

    def _send_line(self) -> None:
        if self.proc.state() != QProcess.ProcessState.Running:
            return

        line = self.input.text()
        self.input.clear()

        self._append_line(f"> {line}", color=COLORS["INPUT_ECHO"])

        data = (line + "\n").encode("utf-8", errors="replace")
        self.proc.write(data)

    def _on_stdout(self) -> None:
        data = bytes(self.proc.readAllStandardOutput()).decode("utf-8", errors="replace")
        self._append_text(data)

    def _on_stderr(self) -> None:
        data = bytes(self.proc.readAllStandardError()).decode("utf-8", errors="replace")
        self._append_text(data, color=COLORS["STDERR"])

    def _on_started(self) -> None:
        pass

    def _on_finished(self, exit_code: int, exit_status: QProcess.ExitStatus) -> None:
        current_title = self.windowTitle()
        if exit_code == 0:
            self.setWindowTitle(f"{current_title} (Finished)")
            if self.close_on_success:
                QTimer.singleShot(0, self.close)
            else:
                self._append_line("\n[Success] Press enter to exit", color=COLORS["SUCCESS"])
                self.waiting_for_exit = True
        else:
            self.setWindowTitle(f"{current_title} (Crashed: Code {exit_code})")
            self._append_line(f"\n[Process finished: exit_code={exit_code}]", color=COLORS["STDERR"])
            self._append_line("Press enter to exit", color=COLORS["STDERR"])
            self.waiting_for_exit = True

        self.setFocus()
        self.output.setFocus()

    def _on_error(self, err: QProcess.ProcessError) -> None:
        current_title = self.windowTitle()
        self.setWindowTitle(f"{current_title} (Error: {err})")
        self._append_line(f"\n[Process error: {err}]")

    def keyPressEvent(self, event) -> None:
        if getattr(self, "waiting_for_exit", False) and event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.close()
            return
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier and event.key() == Qt.Key.Key_L:
            self.output.clear()
            return
        super().keyPressEvent(event)


def get_argv_value_via_key_and_pop_both(argv: list[str], key: str | list[str]) -> Optional[str]:
    keys = [key] if isinstance(key, str) else key

    found_i = -1
    found_k: Optional[str] = None

    for k in keys:
        try:
            found_i = argv.index(k)
            found_k = k
            break
        except ValueError:
            continue

    if found_i == -1:
        return None

    if found_i == len(argv) - 1:
        raise ValueError(f"Expected a value after {found_k}, but none was provided.")

    value = argv[found_i + 1]
    del argv[found_i : found_i + 2]
    return value


def pop_flag(argv: list[str], flag: str) -> bool:
    if flag in argv:
        argv.remove(flag)
        return True
    return False


def _maybe_set_app_id(app_id: Optional[str]) -> None:
    if not app_id:
        return
    if os.name != "nt":
        return
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
    except Exception:
        pass


def main() -> None:
    if len(sys.argv) < 2:
        print(
            f"Usage: python {os.path.basename(__file__)} <script_path> "
            '--python "<Optional:python_exe or py>" --app_id "<Optional:app_id>" '
            '--work_dir "<Optional:working_directory>" -- "arg1" "arg2" ...'
        )
        print()
        input("Aborting. Press enter to exit...")
        raise SystemExit(2)

    script_path = sys.argv[1]
    remaining_args = sys.argv[2:]

    python_exe = get_argv_value_via_key_and_pop_both(remaining_args, "--python") or "py"
    app_id = get_argv_value_via_key_and_pop_both(remaining_args, "--app_id")
    work_dir = get_argv_value_via_key_and_pop_both(remaining_args, "--work_dir")
    close_on_success = pop_flag(remaining_args, "--close_on_success")
    no_input = pop_flag(remaining_args, "--no_input")

    # Optional passthrough separator
    if remaining_args and remaining_args[0] == "--":
        remaining_args.pop(0)

    _maybe_set_app_id(app_id)

    app = QApplication(sys.argv)
    w = TerminalEmulator(
        python_exe=python_exe,
        script_path=script_path,
        args=remaining_args,
        working_directory=work_dir,
        close_on_success=close_on_success,
        no_input=no_input,
    )
    w.show()

    raise SystemExit(app.exec())


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"[Error] {e}")
        print(traceback.format_exc())
        print()
        input("Aborting. Press enter to exit...")
        raise SystemExit(1)
