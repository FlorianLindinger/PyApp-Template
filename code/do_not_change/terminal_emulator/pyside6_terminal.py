# todo: docstring

# ==========================================================================
#   Local Variables (relative paths are relative to folder of this file)
# ==========================================================================


def resolve_path(base, *relative_parts):
    """
    Joins a base path with relative parts and resolves to an absolute path.
    Removes the '..' to make the path clean and readable.
    """
    return os.path.abspath(os.path.join(base, *relative_parts))

import os
import sys
# 1. Detect Base Directory
if "__compiled__" in globals():
    # --- NUITKA COMPILED MODE ---
    # In standalone compiled mode, the .exe is usually inside a .dist folder.
    # We need to go up 1 level compared to the source script.
    file_dir =  os.path.dirname(sys.argv[0]) + "\\..\\"
else:
    # --- STANDARD PYTHON MODE ---
    # Get location of this .py file
    file_dir =  os.path.dirname(os.path.abspath(__file__)) + "\\"

# Standard relative steps
python_scripts_folder_path = resolve_path(file_dir, "..", "..") + "\\"
local_python_exe_for_script_path = resolve_path(
    file_dir, "..", "..", "py_env", "virt_env", "portable_Scripts", "python.bat"
)
settings_file_path = resolve_path(file_dir, "..", "..", "non-user_settings.ini")

python_exe_for_setup_path = resolve_path(file_dir, "..", "python_runtime", "python.exe")
setup_python_file_path = resolve_path(file_dir, "..", "specific_scripts", "setup.py")

# =============================
#      Terminal Appearance
# =============================

# ANSI Color Codes
RED = "\033[91m"
GREEN = "\033[92m"
RESET = "\033[0m"

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
#      Imports
# =============================

import ctypes
import os
import shutil
import subprocess
import sys
import tempfile
import traceback

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

# =============================
#      Definitions
# =============================

# path related


def format_path(path: str) -> str:
    """Ensures drive letters are capitalized for a more premium look on Windows."""
    abs_path = os.path.abspath(path)
    drive, rest = os.path.splitdrive(abs_path)
    if drive:
        return drive.upper() + rest
    return abs_path


# =============================

# PySide6 code


class TerminalEmulator(QMainWindow):
    def __init__(
        self,
        python_exe_for_script_path: str,
        script_path: str,
        args: list[str],
        wdir_is_script_dir=True,
        close_on_success: bool = True,
        no_input: bool = False,
        title: str = "Terminal",
    ):
        super().__init__()

        self.args = args
        self.wdir_is_script_dir = wdir_is_script_dir
        self.close_on_success = close_on_success
        self.no_input = no_input
        self.script_path = script_path
        self.python_exe_for_script_path = python_exe_for_script_path
        self.waiting_for_exit = False

        self.setWindowTitle(title)
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

    def _append_text(self, text: str, color=None) -> None:
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

    def _append_line(self, line: str, color=None) -> None:
        self._append_text(line + ("" if line.endswith("\n") else "\n"), color)

    def _show_critical_error(self, title: str, message: str) -> None:
        # parent=None forces a separate taskbar entry for the dialog
        msg = QMessageBox(None)
        msg.setIcon(QMessageBox.Icon.Critical)
        msg.setWindowTitle(title)
        msg.setText(message)
        msg.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse | Qt.TextInteractionFlag.TextSelectableByKeyboard
        )
        # Ensure it appears in the taskbar and can glow
        msg.setWindowFlags(msg.windowFlags() | Qt.WindowType.Window)
        QApplication.alert(msg)
        msg.exec()

    def _start_process(self) -> None:

        process_args = list(self.args)

        self.output.clear()

        # Unbuffered so output appears immediately.
        args = ["-u", self.script_path, *process_args]

        # Working directory
        if self.wdir_is_script_dir == True:
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
            self._append_line("Press enter to exit", color=COLORS["STDERR"])
            self.waiting_for_exit = True

        self.setFocus()
        self.output.setFocus()

    def _on_error(self, err: QProcess.ProcessError) -> None:
        current_title = self.windowTitle()
        self.setWindowTitle(f"{current_title} (Error: {err})")

        # 1. Capture the current stack trace
        # Using stack() shows how the code reached this error handler
        tb_lines = traceback.format_stack()
        clean_tb = "".join(tb_lines[:-1])  # Exclude this handler itself from the list

        # 2. Append the error and the trace to the terminal UI
        self._append_line(f"\n[Process error: {err}]")
        self._append_line("Traceback (most recent call last):")
        self._append_line(clean_tb)

        # 3. If you want to log it to the real console too
        print(f"Process Error: {err}\n{clean_tb}", file=sys.stderr)

    def keyPressEvent(self, event) -> None:
        if getattr(self, "waiting_for_exit", False) and event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.close()
            return
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier and event.key() == Qt.Key.Key_L:
            self.output.clear()
            return
        super().keyPressEvent(event)


# =============================

# file reading related


def setting_is_true(settings_dict, key, default):
    if key in settings_dict:
        if settings_dict[key].lower() in ("y", "yes", "true", "1"):
            return True
        else:
            return False
    else:
        return default


def read_key_value_file(file_path, key_val_separator="=", comment_chars=("#", ";")):
    key_val_dict = {}
    with open(file_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            # Skip empty lines and comments
            if not line or line.startswith(comment_chars):
                continue

            key, value = line.split(key_val_separator, 1)
            key_val_dict[key.strip()] = value.strip()
    return key_val_dict


# =============================

# print related

# def print_red(msg):
#     print(f"{RED}{msg}{RESET}")
# def print_green(msg):
#     print(f"{GREEN}{msg}{RESET}")
# def input_red(msg):
#     input(f"{RED}{msg}{RESET}")
# def input_green(msg):
#     input(f"{GREEN}{msg}{RESET}")


def wrap_print(msg: str, wrap_character: str = "="):
    size = len(msg)
    print(wrap_character * size)
    print(msg * size)
    print(wrap_character * size)
    return size


def get_python_interpreter() -> str | None:
    """Returns a valid Python executable path or command."""
    interpreters = []

    # If compiled, check global paths defined during setup
    if "__compiled__" in globals():
        # These are usually defined at the top level of this module
        # Note: We use globals() access because they might not be passed as args
        potential_runtime = globals().get("python_exe_for_setup_path")
        if potential_runtime and os.path.exists(potential_runtime):
            interpreters.append(potential_runtime)
    else:
        # In source mode, current executable is fine
        interpreters.append(sys.executable)

    # Fallback to common system names
    interpreters.extend(["py", "python", "python3"])

    for interp in interpreters:
        if os.path.isabs(interp):
            if os.path.exists(interp):
                return interp
        else:
            if shutil.which(interp):
                return interp

    return None


def print_error_in_new_terminal(
    exception,
    key_press_prompt_message="[Error] Press Enter to exit",
    window_title="Error",
    bg_color="4",  # Default: Red
    font_color="E",  # Default: Light Yellow
    wrapping_character="=",
):
    size = len(str(exception))

    msg = wrapping_character * size + "\n"
    msg += str(exception) + "\n"
    msg += wrapping_character * size + "\n"
    msg += traceback.format_exc()
    msg += wrapping_character * size + "\n"

    print_msg_in_new_terminal(
        msg=msg,
        key_press_prompt_message=key_press_prompt_message,
        window_title=window_title,
        bg_color=bg_color,
        font_color=font_color,
    )


def print_msg_in_new_terminal(
    msg: str,
    key_press_prompt_message="Press Enter to exit",
    window_title="Message",
    bg_color="0",  # Default: Black
    font_color="7",  # Default: White
) -> None:
    """
    Spawns a new terminal.
    bg_color/fg_color use Windows CMD hex codes (0-f).
    """
    with tempfile.NamedTemporaryFile("w", delete=False, suffix=".txt", encoding="utf-8") as f:
        path = f.name
        f.write(msg)

    # Combine hex codes for the 'color' command
    color_code = f"{bg_color}{font_color}"

    child_code = f"""
import sys, pathlib, os, ctypes
# Set Window Title
ctypes.windll.kernel32.SetConsoleTitleW("{window_title}")

# Set Global Colors and Refresh Screen
os.system('color {color_code}')
os.system('cls')

p = pathlib.Path(sys.argv[1])
try:
    print(p.read_text(encoding="utf-8", errors="replace"))
finally:
    try: os.remove(p)
    except OSError: pass

print()
input("{key_press_prompt_message}")
"""

    python_exe = get_python_interpreter()

    if python_exe:
        subprocess.Popen(
            [python_exe, "-c", child_code, path],
            creationflags=subprocess.CREATE_NEW_CONSOLE,
            close_fds=True,
        )
    else:
        # Fallback if no Python is found - create a batch file to show the message
        bat_content = f'@echo off\ntitle {window_title}\ncolor {color_code}\ncls\ntype "{path}"\necho.\npause'
        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".bat", encoding="utf-8") as bf:
            bat_path = bf.name
            bf.write(bat_content)

        subprocess.Popen(
            [bat_path],
            creationflags=subprocess.CREATE_NEW_CONSOLE,
            close_fds=True,
        )
        # We can't easily auto-delete the .bat file while it's running,
        # but it's in temp and small.


# =============================

# Windows terminal related


def set_terminal_name(name: str) -> None:
    """Safely set the terminal title using Windows API."""
    try:
        # Clean the name
        safe_name = name.replace("\n", "").replace("\r", "")

        if os.name == "nt":
            ctypes.windll.kernel32.SetConsoleTitleW(safe_name)
        elif sys.stdout.isatty():
            sys.stdout.write(f"\033]0;{safe_name}\007")
            sys.stdout.flush()
    except Exception:
        pass


def get_terminal_name():
    # Create a buffer to hold the text
    buffer = ctypes.create_unicode_buffer(1024)
    # Get the title
    ctypes.windll.kernel32.GetConsoleTitleW(buffer, len(buffer))
    return buffer.value


# =============================

# wrapper code

error_catcher_wrapper_template = r"""
import subprocess, sys, ctypes, traceback, os

RED = {RED}
GREEN = {GREEN}
RESET = {RESET}
python_exe_for_script_path = r"{python_exe_for_script_path}"
script_path = r"{script_path}"
args = {remaining_args}
close_on_crash = {close_on_crash}
close_on_failure = {close_on_failure}
close_on_success = {close_on_success}
wdir_is_script_dir = {wdir_is_script_dir}

def print_red(msg):
    print(f"{{RED}}{{msg}}{{RESET}}")
def input_red(msg):
    input(f"{{RED}}{{msg}}{{RESET}}")
def input_green(msg):
    input(f"{{GREEN}}{{msg}}{{RESET}}")

def set_terminal_name(name: str) -> None:
    try:
        #Clean the name
        safe_name = name.replace("\n", "").replace("\r", "")
        
        if os.name == "nt":
            ctypes.windll.kernel32.SetConsoleTitleW(safe_name)
        elif sys.stdout.isatty():
            sys.stdout.write(f"\033]0;{{safe_name}}\007")
            sys.stdout.flush()
    except Exception:
        pass

def get_terminal_name():
    try:
        buffer = ctypes.create_unicode_buffer(1024)
        ctypes.windll.kernel32.GetConsoleTitleW(buffer, len(buffer))
        return buffer.value
    except Exception:
        return "Terminal"

try:
    if wdir_is_script_dir == True:
        cwd=os.path.dirname(script_path)
    else:
        cwd=None
    
    result = subprocess.run(
        [python_exe_for_script_path, script_path] + args, 
        cwd=cwd
    )
    
    if result.returncode == 0:
        if close_on_success:
            sys.exit(0)
        else:
            set_terminal_name(f"[Success] {{get_terminal_name()}}")
            print()
            input_green("[Success] Press Enter to exit.")
    else:
        if close_on_failure:
            sys.exit(result.returncode)
        else:
            set_terminal_name(f"[Failure] {{get_terminal_name()}}")
            print()
            print_red(f"[Failure] Script exited with code: {{result.returncode}}")
            input_red("[Python Failure Return] Press Enter to exit.")
            
except Exception as e:
    if close_on_crash:
        sys.exit(1)
    else:
        set_terminal_name(f"[Crash] {{get_terminal_name()}}")
        print()
        print_red("="*40)
        print_red(f"CRITICAL LAUNCH ERROR: {{e}}")
        print_red("="*40)
        traceback.print_exc()
        print_red("="*40)
        print(f"[Info] Python Exe/Command: {{python_exe_for_script_path}}")
        print(f"[Info] Script: {{script_path}}")
        print()
        input_red("[Python Crash] See above. Press Enter to exit.")
"""
# =============================

# miscellaneous


def _set_app_id(app_id) -> None:
    if not app_id:
        return
    if os.name != "nt":
        return
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
    except Exception:
        pass


# ====================================
#    definition of main function
# ====================================


def main() -> None:
    # ======================
    # setup

    # print usage if wrong and abort
    if len(sys.argv) < 2:
        exe_name = os.path.basename(sys.argv[0])
        raise ValueError(
            f'[Error] Too few arguments.\n\nUsage: {exe_name} "<create_terminal=1/0>" "<optional:app_id>" "arg1" "arg2" ...'
        )

    # get args from calling this script
    create_terminal = sys.argv[1]  # 1 or 0
    if len(sys.argv) > 2:
        app_id = sys.argv[2]
        # change app id of current process (for taskbar grouping with shortcut)
        _set_app_id(app_id)
    remaining_args = sys.argv[3:]

    # run setup python file
    if setup_python_file_path not in ["", None, False]:
        # raise if setup/python script not found
        if not os.path.exists(setup_python_file_path):
            raise FileNotFoundError(f'[Error] Python setup script not found at "{format_path(setup_python_file_path)}"')
        if not os.path.exists(python_exe_for_setup_path):
            raise FileNotFoundError(
                f'[Error] Python exe for setup script not found at "{format_path(python_exe_for_setup_path)}"'
            )
        # run setup
        p = subprocess.Popen(
            [python_exe_for_setup_path, setup_python_file_path],
            creationflags=subprocess.CREATE_NEW_CONSOLE,
        )
        p.wait()  # wait for setup to finish

    # raise error if settings not found
    if not os.path.exists(settings_file_path):
        raise FileNotFoundError(f'[Error] Settings file not found at "{format_path(settings_file_path)}"')

    # import and process non-user_settings
    settings = read_key_value_file(settings_file_path)
    terminal_needs_input = setting_is_true(settings, "terminal_needs_input", True)
    close_on_success = setting_is_true(settings, "close_on_success", True)
    close_on_crash = setting_is_true(settings, "close_on_crash", False)
    close_on_failure = setting_is_true(settings, "close_on_failure", False)
    if "program_name" in settings:
        title = settings["program_name"]
    else:
        title = "Terminal"  # default value
    use_global_python = setting_is_true(settings, "use_global_python", False)
    if use_global_python == True:
        python_exe_for_script_path = "py"
    else:
        python_exe_for_script_path = format_path(local_python_exe_for_script_path)
        # raise error if python or script or settings not found
        if not os.path.exists(python_exe_for_script_path):
            raise FileNotFoundError(f'[Error] Python executable/command not found at "{python_exe_for_script_path}"')
    start_in_shortcut_folder = setting_is_true(settings, "start_in_shortcut_folder", False)
    wdir_is_script_dir = not start_in_shortcut_folder
    if "python_code_name" in settings:
        python_code_name = settings["python_code_name"]
        script_path = python_scripts_folder_path + python_code_name
    else:
        raise ValueError(f'[Error] Setting "python_code_name" not found in "{format_path(settings_file_path)}"')

    # make abs path and nice looking format
    script_path = format_path(script_path)

    # raise error if script not found
    if not os.path.exists(script_path):
        raise FileNotFoundError(f'[Error] Python script not found at "{script_path}"')

    # ======================
    # launch terminal

    # run main python script in windowless or termnial emulator
    if create_terminal == "1":
        try:
            # launch termnial emulator
            Q_app = QApplication(sys.argv)
            window = TerminalEmulator(
                python_exe_for_script_path=python_exe_for_script_path,
                script_path=script_path,
                args=remaining_args,
                wdir_is_script_dir=wdir_is_script_dir,
                close_on_success=close_on_success,
                no_input=not terminal_needs_input,
                title=title,
            )
            window.show()
            # Start the event loop to keep the window and its processes alive
            exit_code = Q_app.exec()
            raise SystemExit(exit_code)

        except Exception as e:
            # dont use "close_on_crash" setting since this crash is not crash of python script
            print_error_in_new_terminal(e)
            
            if "Q_app" in globals() and Q_app is not None:
                raise SystemExit(Q_app.exec())
            else:
                raise SystemExit(1)

    else:
        # launch windows terminal

        # The 'error_catcher_wrapper' code to run inside the new window
        error_catcher_wrapper = error_catcher_wrapper_template.format(
            python_exe_for_script_path=python_exe_for_script_path,
            script_path=script_path,
            remaining_args=repr(remaining_args),
            close_on_crash=close_on_crash,
            close_on_failure=close_on_failure,
            close_on_success=close_on_success,
            wdir_is_script_dir=wdir_is_script_dir,
            RED=repr(RED),
            GREEN=repr(GREEN),
            RESET=repr(RESET),
        )

        # launch this error_catcher_wrapper (handles exceptions/prints/prompts) in the new console
        python_exe = get_python_interpreter()
        if not python_exe:
            # If no python is found, we at least try to show the error in a box
            # or print it before failing.
            print("[Error] No Python interpreter found to launch the terminal wrapper.")
            sys.exit(1)

        p = subprocess.Popen([python_exe, "-c", error_catcher_wrapper], creationflags=subprocess.CREATE_NEW_CONSOLE)
        set_terminal_name(title)  # chante terminal title
        p.wait()  # wait for file to finish

        # return (SystemExit does not raise Exception)
        raise SystemExit(p.returncode)


# ====================================
#      execution of main function
# ====================================

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        # print error in new terminal (because this script might be launched without terminal)
        print_error_in_new_terminal(e)

        # return with errorcode 1
        raise SystemExit(1)
