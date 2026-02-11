import os
import sys
import traceback

from PySide6.QtCore import QProcess, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QTextCharFormat, QTextCursor, QIcon
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

# =============================

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

FALLBACK_STYLESHEET = """
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

# =============================

class TerminalEmulator(QMainWindow):
    def __init__(
        self,
        python_exe_for_script_path: str,
        script_path: str,
        args: list[str],
        wdir_is_script_dir: bool = True,
        close_on_success: bool = True,
        close_on_failure: bool = False,
        close_on_crash: bool = False,
        no_input: bool = False,
        title: str = "Terminal",
        icon_path: str = None,
        stylesheet: str = None,
    ):
        super().__init__()

        self.args = args
        self.wdir_is_script_dir = wdir_is_script_dir
        self.close_on_success = close_on_success
        self.close_on_failure = close_on_failure
        self.close_on_crash = close_on_crash
        self.no_input = no_input
        self.script_path = script_path
        self.python_exe_for_script_path = python_exe_for_script_path
        self.waiting_for_exit = False

        self.setWindowTitle(title)
        self.resize(1000, 700)
        
        if icon_path and os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
            
        if stylesheet:
            self.setStyleSheet(stylesheet)

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

    def _append_text(self, text: str, color=None) -> None:
        if not text:
            return
        self.output.moveCursor(QTextCursor.MoveOperation.End)
        cursor = self.output.textCursor()

        fmt = QTextCharFormat()
        if color:
            fmt.setForeground(QColor(color))
        else:
            fmt.setForeground(QColor(COLORS["STDOUT"]))

        cursor.insertText(text, fmt)
        self.output.moveCursor(QTextCursor.MoveOperation.End)

    def _append_line(self, line: str, color=None) -> None:
        self._append_text(line + ("" if line.endswith("\n") else "\n"), color)

    def _show_critical_error(self, title: str, message: str) -> None:
        msg = QMessageBox(None)
        msg.setIcon(QMessageBox.Icon.Critical)
        msg.setWindowTitle(title)
        msg.setText(message)
        msg.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse | Qt.TextInteractionFlag.TextSelectableByKeyboard
        )
        msg.setWindowFlags(msg.windowFlags() | Qt.WindowType.Window)
        QApplication.alert(msg)
        msg.exec()

    def _start_process(self) -> None:
        process_args = list(self.args)
        self.output.clear()
        args = ["-u", self.script_path, *process_args]
        if self.wdir_is_script_dir:
            self.proc.setWorkingDirectory(os.path.dirname(self.script_path))
        self.proc.start(self.python_exe_for_script_path, args)
        if not self.no_input:
            QTimer.singleShot(0, self.input.setFocus)

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
            self.setWindowTitle(f"[Crashed: Code {exit_code}] {current_title}")
            self._append_line(f"\n[Process finished: exit_code={exit_code}]", color=COLORS["STDERR"])
            if self.close_on_failure:
                QTimer.singleShot(0, self.close)
            else:
                self._append_line("Press enter to exit", color=COLORS["STDERR"])
                self.waiting_for_exit = True

        self.setFocus()
        self.output.setFocus()

    def _on_error(self, err: QProcess.ProcessError) -> None:
        current_title = self.windowTitle()
        self.setWindowTitle(f"{current_title} (Error: {err})")
        
        tb_lines = traceback.format_stack()
        clean_tb = "".join(tb_lines[:-1])

        self._append_line(f"\n[Process error: {err}]")
        self._append_line("Traceback (most recent call last):")
        self._append_line(clean_tb)
        print(f"Process Error: {err}\n{clean_tb}", file=sys.stderr)

        if self.close_on_crash:
            QTimer.singleShot(0, self.close)
        else:
            self.waiting_for_exit = True

    def keyPressEvent(self, event) -> None:
        if getattr(self, "waiting_for_exit", False) and event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.close()
            return
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier and event.key() == Qt.Key.Key_L:
            self.output.clear()
            return
        super().keyPressEvent(event)

def str_to_bool(s):
    return s.lower() in ("1", "true", "y", "yes")

if __name__ == "__main__":

    try:
        if len(sys.argv) < 11:
            raise ValueError(f"Not enough arguments provided ({len(sys.argv)}/11).")
            
        python_exe_for_script_path = sys.argv[1]
        script_path = sys.argv[2]
        wdir_is_script_dir = str_to_bool(sys.argv[3])
        close_on_success = str_to_bool(sys.argv[4])
        close_on_failure = str_to_bool(sys.argv[5])
        close_on_crash = str_to_bool(sys.argv[6])
        terminal_needs_input = str_to_bool(sys.argv[7])
        title = sys.argv[8]
        icon_path = sys.argv[9] if sys.argv[9] else None
        stylesheet_arg = sys.argv[10]
        extra_args = sys.argv[11:]
        
        # Determine stylesheet content (path or fallback)
        if stylesheet_arg and os.path.exists(stylesheet_arg):
            try:
                with open(stylesheet_arg, "r", encoding="utf-8") as f:
                    stylesheet_content = f.read()
            except Exception:
                stylesheet_content = FALLBACK_STYLESHEET
        else:
            stylesheet_content = FALLBACK_STYLESHEET

        Q_app = QApplication(sys.argv)
            
        window = TerminalEmulator(
            python_exe_for_script_path=python_exe_for_script_path,
            script_path=script_path,
            args=extra_args,
            wdir_is_script_dir=wdir_is_script_dir,
            close_on_success=close_on_success,
            close_on_failure=close_on_failure,
            close_on_crash=close_on_crash,
            no_input=not terminal_needs_input,
            title=title,
            icon_path=icon_path,
            stylesheet=stylesheet_content,
        )
        
        window.show()
        sys.exit(Q_app.exec())
        
    except Exception as e:
        print(f"Terminal Emulator Launch Error: {e}")
        traceback.print_exc()
        if "Q_app" in globals() and Q_app is not None:
             # If UI failed but app started, maybe show message box
             sys.exit(1)
        else:
            sys.exit(1)
