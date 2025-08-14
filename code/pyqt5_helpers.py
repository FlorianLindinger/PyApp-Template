###########################
# todo:
###########################

from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QComboBox, QFileDialog, QTextEdit, QCheckBox, QSizePolicy, QSplitter,
    QSlider, QLineEdit, QRadioButton, QButtonGroup, QFrame, QProgressBar,
    QScrollArea,QTabWidget,QMessageBox
)
from PyQt5.QtGui import QImage, QPixmap, QIcon
from PyQt5.QtCore import Qt, QTimer,QObject,QThread,pyqtSignal,pyqtSlot

import cv2
import numpy as np
import traceback
import serial.tools.list_ports
import sys
import time

class helper_Q_worker_single(QObject):
    """looped_function takes as input what was sent to the thread and sends out the output of the function if that is not None
    """
    data_out_signal = pyqtSignal(
        object)  # define here as a function of the class in order to call its method connect later and not in init

    def __init__(self, function, *args):
        super().__init__()
        self.function = function
        self.args = args

    def run(self):
        output = self.function(*self.args)
        self.data_out_signal.emit(output)


def Q_thread_single(self, function, connected_function, *args):

    thread = QThread()
    worker = helper_Q_worker_single(function=function, *args)
    worker.moveToThread(thread)
    worker.data_out_signal.connect(connected_function)
    thread.started.connect(worker.run)
    thread.start()
    if hasattr(self, "_single_execution_threads"):
        self._single_execution_threads.append((thread, worker))
    else:
        self._single_execution_threads = [(thread, worker)]


class helper_Q_worker_loop(QObject):
    """looped_function takes as input what was sent to the thread and sends out the output of the function if that is not None
    """
    data_out_signal = pyqtSignal(
        object)  # define here as a function of the class in order to call its method connect later and not in init

    def __init__(self, looped_function):
        super().__init__()
        self.looped_function = looped_function
        self.exit_signal = False
        self.paused = False
        self.received_data = None

    @pyqtSlot(object)  # Other thread → this thread
    def send_to_thread(self, data):
        """used for other threads to send data to this thread"""
        self.received_data = data  # Store latest received message

    def run(self):
        """start main loop"""
        while True:
            if self.exit_signal == True:
                return
            elif self.paused == True:
                time.sleep(0.1)
            else:
                output = self.looped_function(self.received_data)
                if output != None:
                    self.data_out_signal.emit(output)


class Q_thread_loop:
    def __init__(self, looped_function, connected_function, start_running=True):
        self._thread = QThread()
        self._worker = helper_Q_worker_loop(looped_function=looped_function)
        self._worker.moveToThread(self._thread)
        self._worker.data_out_signal.connect(connected_function)
        self._thread.started.connect(self._worker.run)
        if start_running == True:
            self._worker.paused = False
        else:
            self._worker.paused = True
        self._thread.start()

    def resume(self):
        self._worker.paused = False

    def pause(self):
        self._worker.paused = True

    def send(self, data):
        self._worker.send_to_thread(data)

    def quit(self):
        self._worker.exit_signal = True
        self._thread.quit()
        self._thread.wait()


# class MainWindow(QWidget):
#     def __init__(self):
#         super().__init__()


#         layout = QVBoxLayout(self)
#         self.line = QLineEdit()
#         self.label = QLabel("Waiting for ticks...")

#         layout.addWidget(self.label)
#         layout.addWidget(self.line)

#         def fun(_):
#             if _ is not None:
#                 time.sleep(2)
#                 print(_)
#                 return str(_)
#             time.sleep(2)
#             print(1)
#             return str(time.time())

#         def fun2():
#             time.sleep(5)
#             return 52

#         Q_thread_single(self, fun2, self.update_label)

#         self.thread1 = Q_thread_loop(fun, self.update_label)

#         # GUI → Thread
#         self.line.returnPressed.connect(
#             lambda: self.thread1.send(self.line.text()))

#     def update_label(self, text):
#         self.label.setText(str(text))

#     def closeEvent(self, event):
        
#         self.thread1.quit()
#         event.accept()
# app = QApplication(sys.argv)
# window = MainWindow()
# window.show()
# sys.exit(app.exec_())


class new_tab_button(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 0, 0, 0)
        self.button = QPushButton("+")
        self.button.setFixedSize(20, 20)
        self.button.setFlat(True)
        layout.addWidget(self.button)
        self.setLayout(layout)


class TabDemo(QWidget):
    def __init__(self):
        super().__init__()
        self.resize(400, 300)

        # Main layout
        main_layout = QVBoxLayout(self)

        # Tab widget
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.setMovable(True)

        self.tabs.setTabPosition(QTabWidget.North)

        main_layout.addWidget(self.tabs)

        # Buttons layout
        buttons_layout = QHBoxLayout()
        main_layout.addLayout(buttons_layout)

        # Add Tab button
        self.btn_add = QPushButton("Add Tab")
        buttons_layout.addWidget(self.btn_add)
        self.btn_add.clicked.connect(self.add_tab)

        # Remove Tab button
        self.btn_remove = QPushButton("Remove Tab")
        buttons_layout.addWidget(self.btn_remove)

        # Add an initial tab
        self.add_tab()

        self.tabs.tabBarDoubleClicked.connect(self.start_rename)

        self.tabs._current_index = None
        self.tabs._current_editor = None

    def start_rename(self, index):
        if index < 0:
            return

        if self.tabs._current_editor:
            self.commit_rename()

        tab_rectangle = self.tabs.tabBar().tabRect(index)
        editor = QLineEdit(self.tabs.tabText(index), self.tabs.tabBar())
        editor.setGeometry(tab_rectangle)
        editor.setFocus()
        editor.selectAll()

        self.tabs._current_editor = editor
        self.tabs._current_index = index

        editor.returnPressed.connect(self.commit_rename)
        editor.focusOutEvent = lambda e: (
            self.commit_rename(), QLineEdit.focusOutEvent(editor, e))

        editor.show()

    def commit_rename(self):
        if self.tabs._current_editor and self.tabs._current_index is not None:
            new_name = self.tabs._current_editor.text()

            if new_name:
                self.tabs.setTabText(self.tabs._current_index, new_name)
        self.tabs._current_editor.deleteLater()

        self.tabs._current_index = None
        self.tabs._current_editor = None

    def add_tab(self):
        count = self.tabs.count() + 1
        tab = QWidget()
        tab_layout = QVBoxLayout(tab)
        tab_layout.addWidget(QLabel(f"Content of Tab {count}"))
        self.tabs.addTab(tab, "New Tab")
        self.tabs.setCurrentWidget(tab)


################################################


title = "test"
icon_path = r"icons\icon.ico"
default_com_port = "com9"
window_pixels_h, window_pixels_v = 1000, 700


def get_available_com_ports_tuple() -> list[str]:
    return [(elem.device, elem.description) for elem in serial.tools.list_ports.comports()]  # nopep8 #type:ignore


def get_frame():
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    cv2.putText(frame, "Aspect Ratio Preserved", (50, 240),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
    return frame


def Q_horizontal_line(height_pxl=2):
    line = QFrame()
    line.setFrameShape(QFrame.HLine)
    line.setFrameShadow(QFrame.Sunken)
    line.setFixedHeight(height_pxl)
    return line


def Q_vertical_line(width_pxl=2):
    line = QFrame()
    line.setFrameShape(QFrame.WLine)
    line.setFrameShadow(QFrame.Sunken)
    line.setFixedWidth(width_pxl)
    return line


def Q_handle_label_positioning(self, label="", label_pos="left", moveable=False, align=None):
    layout = QVBoxLayout()
    layout.setContentsMargins(0, 0, 0, 0)
    if label in ["", None]:
        layout.addWidget(self.widget)
    else:
        self.label = QLabel(label)
        if label_pos == "top":
            layout.addLayout(self.label)
        if label_pos in ["left", "right"]:
            if moveable == True:
                widget_line = QSplitter(Qt.Horizontal)
            else:
                widget_line = QHBoxLayout()
                if align is None:
                    self.widget.setSizePolicy(
                        QSizePolicy.Expanding, QSizePolicy.Expanding)
                if align == "right":
                    widget_line.addStretch()
            if label_pos == "left":
                widget_line.addWidget(self.label)
                widget_line.addWidget(self.widget)
            else:
                widget_line.addWidget(self.widget)
                widget_line.addWidget(self.label)
            if moveable == True:
                layout.addWidget(widget_line)
            else:
                if align == "left":
                    widget_line.addStretch()
                layout.addLayout(widget_line)
        else:
            layout.addWidget(self.widget)
        if label_pos == "bottom":
            layout.addLayout(self.label)
    self.setLayout(layout)


class Q_colored_pbar(QWidget):
    def __init__(self, label_text="", unit="", min_val=0, max_val=100, label=True, label_right=True):
        super().__init__()

        self.label = label
        self.progress = QProgressBar()
        self.progress.setRange(min_val, max_val)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)  # hide default text inside bar

        layout = QHBoxLayout()
        if label == True:
            self.label_text = label_text
            self.unit = unit
            self.label = QLabel(f"{label_text} {unit}")
            if label_right == True:
                layout.addWidget(self.progress)
                layout.addWidget(self.label)
            else:
                layout.addWidget(self.label)
                layout.addWidget(self.progress)
        else:
            layout.addWidget(self.progress)
        self.setLayout(layout)

    def set_value(self, value):
        self.progress.setValue(value)
        if self.label == True:
            self.label.setText(f"{self.label_text}{value}{self.unit}")

        # Change color based on value
        if value < 25:
            color = "green"
        elif value < 50:
            color = "yellow"
        elif value < 75:
            color = "orange"
        elif value < 100:
            color = "red"
        else:
            color = "magenta"

        self.progress.setStyleSheet(f"""
            QProgressBar {{
                border: 1px solid gray;
                border-radius: 3px;
            }}
            QProgressBar::chunk {{
                background-color: {color};
            }}
        """)


class Q_updating_dropdown(QWidget):
    """updates for opening dropdown"""

    def __init__(self, get_list_function, start_value="", on_select_function=None, label="", label_pos="left"):
        super().__init__()

        self.on_select_function = on_select_function
        self.get_list_function = get_list_function

        self.widget = QComboBox()
        self.widget.setEditable(False)
        self.widget.addItem(str(start_value))
        self.widget.currentTextChanged.connect(self.on_select_function)
        self.widget.original_showPopup = self.widget.showPopup
        self.widget.showPopup = self.new_showPopup

        Q_handle_label_positioning(self, label, label_pos)

    def new_showPopup(self):
        self.widget.clear()
        self.widget.addItems(self.get_list_function())
        self.widget.original_showPopup()

    def trigger(self):
        self.on_select_function(self.get())

    def set(self, value):
        self.widget.blockSignals(True)
        self.widget.setCurrentText(value)
        self.widget.blockSignals(False)

    def get(self):
        return self.widget.currentText()

    def set_and_trigger(self, value):
        self.set(value)
        self.trigger()


class Q_com_port_dropdown(QWidget):
    """updates available com ports for opening dropdown"""

    def __init__(self, start_value="", on_select_function=None, label="", label_pos="left"):
        super().__init__()

        self.on_select_function = on_select_function

        self.widget = QComboBox()
        self.widget.setEditable(False)
        self.widget.addItem(str(start_value).upper())
        self.widget.currentTextChanged.connect(self.on_select_function)
        self.widget.original_showPopup = self.widget.showPopup
        self.widget.showPopup = self.new_showPopup

        Q_handle_label_positioning(self, label, label_pos)

    def new_showPopup(self):
        self.widget.clear()
        ports_list = get_available_com_ports_tuple()
        for com_port, description in ports_list:
            self.widget.addItem(f"{com_port}: {description}", com_port)
        self.widget.original_showPopup()


class Q_slider(QWidget):
    def __init__(self, min_val=0, max_val=100, start_val=None, on_change_function=None, set_to_edge_for_out_of_range_setbox=True, setbox_pos="top right", label="", label_pos="top left"):
        super().__init__()

        self.on_change_function = on_change_function
        self.set_to_edge_for_out_of_range_setbox = set_to_edge_for_out_of_range_setbox

        if setbox_pos is None:
            setbox_pos = ""
        if label_pos is None:
            label_pos = ""
        if ("top" in setbox_pos or "bottom" in setbox_pos) and "left" not in setbox_pos and "right" not in setbox_pos:
            setbox_pos += "right"
        if ("top" in label_pos or "bottom" in label_pos) and "left" not in label_pos and "right" not in label_pos:
            label_pos += "left"

        self.min_val = min_val
        self.max_val = max_val

        # slider
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(self.min_val, self.max_val)
        if start_val != None:
            self.slider.setValue(start_val)
        self.slider.valueChanged.connect(self._on_slider_changed)

        # setbox
        self.setbox = QLineEdit()
        if start_val != None:
            self.setbox.setText(str(start_val))
        self.setbox.editingFinished.connect(self._on_line_edit_finished)

        # label
        label = QLabel(label)

        # top line
        top_line = QHBoxLayout()
        if "top" in label_pos and "left" in label_pos:
            top_line.addWidget(label)
        if "top" in setbox_pos and "left" in setbox_pos:
            top_line.addWidget(self.setbox)
        if "top" in label_pos and "right" in label_pos:
            top_line.addWidget(label)
        if "top" in setbox_pos and "right" in setbox_pos:
            top_line.addWidget(self.setbox)

        # slider line
        slider_line = QSplitter(Qt.Horizontal)
        if "top" not in label_pos and "bottom" not in label_pos and "left" in label_pos:
            slider_line.addWidget(label)
        if "top" not in setbox_pos and "bottom" not in setbox_pos and "left" in setbox_pos:
            slider_line.addWidget(self.setbox)
        slider_line.addWidget(self.slider)
        if "top" not in label_pos and "bottom" not in label_pos and "right" in label_pos:
            slider_line.addWidget(label)
        if "top" not in setbox_pos and "bottom" not in setbox_pos and "right" in setbox_pos:
            slider_line.addWidget(self.setbox)

        # bottom line
        bottom_line = QHBoxLayout()
        if "bottom" in label_pos and "left" in label_pos:
            bottom_line.addWidget(label)
        if "bottom" in setbox_pos and "left" in setbox_pos:
            bottom_line.addWidget(self.setbox)
        if "bottom" in label_pos and "right" in label_pos:
            bottom_line.addWidget(label)
        if "bottom" in setbox_pos and "right" in setbox_pos:
            bottom_line.addWidget(self.setbox)

        # vertically stack lines
        layout = QVBoxLayout()
        if top_line.count() > 0:
            layout.addLayout(top_line)
        layout.addWidget(slider_line)
        if bottom_line.count() > 0:
            layout.addLayout(bottom_line)
        self.setLayout(layout)

    def _on_slider_changed(self, value):
        self.setbox.setText(str(value))
        self.on_change_function(value)

    def _on_line_edit_finished(self):
        try:
            val = round(float(self.setbox.text()))
            if self.min_val <= val <= self.max_val:
                self.slider.setValue(val)
            else:
                if self.set_to_edge_for_out_of_range_setbox == True:
                    if val > self.max_val:
                        self.slider.setValue(self.max_val)
                        self.setbox.setText(str(self.max_val))
                    else:
                        self.slider.setValue(self.min_val)
                        self.setbox.setText(str(self.min_val))
                else:
                    # reset to current slider value if out of range
                    self.setbox.setText(str(self.slider.value()))
        except ValueError:
            # reset to current slider value if invalid input
            self.setbox.setText(str(self.slider.value()))


class Q_command_line(QWidget):
    def __init__(self, on_enter_function, placeholder_text="", clear_command="clear", output=None, label="", label_pos="left"):
        super().__init__()

        self.clear_command = clear_command
        self.output = output
        self.on_enter_function = on_enter_function

        self.widget = QLineEdit()
        self.widget.history = []
        self.widget.history_index = -1
        self.widget.returnPressed.connect(self._handle_enter)
        self.widget.setPlaceholderText(placeholder_text)
        self.widget.original_keyPressEvent = self.widget.keyPressEvent
        self.widget.keyPressEvent = self.new_keyPressEvent

        Q_handle_label_positioning(self, label, label_pos)

    def _handle_enter(self):
        text = self.widget.text().strip()
        if text:
            self.widget.history.append(text)
            self.widget.history_index = -1
            if text == self.clear_command and self.output is not None:
                self.output.clear()
            else:
                if self.output is not None:
                    self.output.log(text)
                self.on_enter_function(text)
            self.widget.clear()

    def new_keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            # Let the base class handle it and emit returnPressed
            self.widget.original_keyPressEvent(event)
            return
        elif event.key() == Qt.Key_Up:
            if self.widget.history:
                if self.widget.history_index == -1:
                    self.widget.history_index = len(self.widget.history)
                if self.widget.history_index > 0:
                    self.widget.history_index -= 1
                    self.widget.setText(
                        self.widget.history[self.widget.history_index])
            return
        elif event.key() == Qt.Key_Down:
            if self.widget.history:
                if self.widget.history_index == -1:
                    # Already on cleared line, do nothing
                    pass
                elif self.widget.history_index < len(self.widget.history) - 1:
                    self.widget.history_index += 1
                    self.widget.setText(
                        self.widget.history[self.widget.history_index])
                else:
                    self.widget.history_index = -1
                    self.widget.clear()
            return
        self.widget.original_keyPressEvent(event)


class Q_terminal(QWidget):
    """Meant for output only. Use Q_command_line for input."""

    def __init__(self, label="", label_pos="left"):
        super().__init__()

        self.widget = QTextEdit()
        self.widget.setReadOnly(True)
        self.widget.setMinimumHeight(20*3)

        Q_handle_label_positioning(self, label, label_pos)

    def log(self, text):
        self.widget.append(str(text))

    def clear(self):
        self.widget.clear()


class Q_dropdown(QWidget):
    def __init__(self, values=[], on_select_function=None, label="", label_pos="left"):
        super().__init__()

        self.on_select_function = on_select_function

        self.widget = QComboBox()
        self.widget.setEditable(False)
        self.widget.addItems(values)
        self.widget.currentTextChanged.connect(self.on_select_function)

        Q_handle_label_positioning(self, label, label_pos)

    def trigger(self):
        self.on_select_function(self.get())

    def set(self, value):
        self.widget.blockSignals(True)
        self.widget.setCurrentText(value)
        self.widget.blockSignals(False)

    def get(self):
        return self.widget.currentText()

    def set_and_trigger(self, value):
        self.set(value)
        self.trigger()


class Q_button(QWidget):
    def __init__(self, on_click_function, text, label="", label_pos="left"):
        super().__init__()

        self.on_click_function = on_click_function

        self.widget = QPushButton(text)
        self.widget.clicked.connect(self.on_click_function)

        Q_handle_label_positioning(self, label, label_pos)


class Q_input_line(QWidget):
    def __init__(self, label="", label_pos="left", placeholder_text="", on_enter_function=lambda x: None, on_change_function=lambda x: None):
        super().__init__()

        self.on_enter_function = on_enter_function
        self.on_change_function = on_change_function

        self.widget = QLineEdit()
        self.widget.setPlaceholderText(placeholder_text)
        self.widget.returnPressed.connect(
            lambda: self.on_enter_function(self.widget.text()))
        self.widget.textEdited.connect(self.on_change_function)

        Q_handle_label_positioning(self, label, label_pos)

    def trigger(self):
        self.on_enter_function(self.get())

    def set(self, value):
        self.widget.blockSignals(True)
        self.widget.setText(value)
        self.widget.blockSignals(False)

    def get(self):
        return self.widget.text()

    def set_and_trigger(self, value):
        self.set(value)
        self.trigger()


# make maker class which has like trigger and set_and_trigger
# and set and get

class Q_check_box(QWidget):
    def __init__(self, on_switch_function, label="", label_pos="right", align="left"):
        super().__init__()

        self.on_switch_function = on_switch_function

        self.widget = QCheckBox()
        self.widget.stateChanged.connect(self.on_switch_function)

        Q_handle_label_positioning(self, label, label_pos, align=align)

    def trigger(self):
        self.on_switch_function(self.get())

    def set(self, value):
        self.widget.blockSignals(True)
        self.widget.setChecked(value)
        self.widget.blockSignals(False)

    def get(self):
        return self.widget.isChecked()

    def set_and_trigger(self, value):
        self.set(value)
        self.trigger()


class Q_output_line(QWidget):
    def __init__(self, label="", label_pos="left", placeholder_text=""):
        super().__init__()

        self.widget = QLineEdit()
        self.widget.setPlaceholderText(placeholder_text)
        self.widget.setEditable(False)

        Q_handle_label_positioning(self, label, label_pos)


# self.sidebar.setFixedWidth(self.sidebar_width)  # initial width

# # Toggle animation sets:
# self.animation.setStartValue(self.sidebar.width())
# self.animation.setEndValue(0)  # collapse to zero width, not hide

# # Main content:
# self.main_content.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

if __name__ == "__main__":
    app = QApplication([])
    demo = TabDemo()
    demo.show()
    app.exec()


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle(title)
        self.setWindowIcon(QIcon(icon_path))
        self.resize(int(1920/2), int(1080/2))

        ############################################

        self.button = Q_button(lambda x: None, "Click Me")

        self.dropdown1 = Q_com_port_dropdown(
            default_com_port, lambda: 1, label="dropdown0")

        self.dropdown2 = Q_updating_dropdown(lambda: [
                                             "Option 1", "Option 2", "Option 3"], on_select_function=lambda: 1, label="dropdown1")

        self.dropdown3 = Q_dropdown(values=[
                                    "Option 1", "Option 2", "Option 3"], on_select_function=lambda: 1, label="dropdown2")

        self.switch = Q_check_box(lambda x: None, "Enable Option")

        self.text_input = Q_input_line(
            label="line1", placeholder_text="placeholder")

        self.slider = Q_slider(0, 100, label="slider",
                               on_change_function=self.on_slider_change)

        self.colored_bar = Q_colored_pbar()

        self.terminal_output = Q_terminal()

        self.command_line = Q_command_line(
            on_enter_function=lambda x: None, output=self.terminal_output, placeholder_text="placeholder")

        self.file_path_button = QPushButton("Select File")
        self.file_path_button.clicked.connect(self.on_open_file_path_menu)
        self.file_path_box = QLineEdit()
        self.file_path_box.setReadOnly(True)

        self.folder_path_button = QPushButton("Select Folder")
        self.folder_path_button.clicked.connect(self.on_open_folder_path_menu)
        self.folder_path_box = QLineEdit()
        self.folder_path_box.setReadOnly(True)

        self.radio_label = QLabel("Whatever:")
        self.radio1 = QRadioButton("Choice 1")
        self.radio2 = QRadioButton("Choice 2")
        self.radio3 = QRadioButton("Choice 3")
        self.radio_group = QButtonGroup()
        self.radio_group.addButton(self.radio1, id=1)
        self.radio_group.addButton(self.radio2, id=2)
        self.radio_group.addButton(self.radio3, id=3)
        self.radio1.setChecked(True)
        self.radio_group.buttonClicked[int].connect(self.on_radio_selected)

        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)  # Start at 0%
        self.progress_bar.setFormat("%p%")  # shows "42%"
        self.progress_bar.setTextVisible(True)
        # self.progress_bar.setMaximum(0)  # no max means it's in 'busy' mode

        ############################################

        # Create the control sidebar widget with its layout
        # sidebar vertically stacked content

        sidebar = QVBoxLayout()
        sidebar.setSpacing(4)  # or some spacing you prefer
        sidebar.setContentsMargins(4, 4, 4, 4)

        sidebar.addWidget(self.button)
        sidebar.addWidget(Q_horizontal_line())
        sidebar.addWidget(self.dropdown1)
        sidebar.addWidget(Q_horizontal_line())
        sidebar.addWidget(self.dropdown2)
        sidebar.addWidget(self.dropdown3)
        sidebar.addWidget(Q_horizontal_line())
        sidebar.addWidget(self.switch)
        sidebar.addWidget(Q_horizontal_line())
        sidebar.addWidget(self.folder_path_button)
        sidebar.addWidget(self.folder_path_box)
        sidebar.addWidget(Q_horizontal_line())
        sidebar.addWidget(self.file_path_button)
        sidebar.addWidget(self.file_path_box)
        sidebar.addWidget(Q_horizontal_line())
        sidebar.addWidget(self.text_input)
        sidebar.addWidget(Q_horizontal_line())
        sidebar.addWidget(self.slider)
        sidebar.addWidget(Q_horizontal_line())
        sidebar.addWidget(self.radio_label)
        sidebar.addWidget(self.radio1)
        sidebar.addWidget(self.radio2)
        sidebar.addWidget(Q_horizontal_line())
        sidebar.addWidget(self.progress_bar)
        sidebar.addWidget(Q_horizontal_line())
        sidebar.addWidget(self.colored_bar)
        sidebar.addWidget(Q_horizontal_line())
        sidebar.addWidget(self.command_line)
        sidebar.addWidget(self.terminal_output)

        # Make sidebar vertically scrollable
        self.sidebar_widget = QWidget()
        self.sidebar_widget.setLayout(sidebar)
        sidebar_scroll_area = QScrollArea()
        # make it resize itself horizontally
        sidebar_scroll_area.setWidgetResizable(True)
        sidebar_scroll_area.setWidget(self.sidebar_widget)

        self.toggle_button = QPushButton(">")
        self.toggle_button.setFixedSize(30, 25)
        self.toggle_button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.toggle_button.clicked.connect(self.toggle_sidebar)

        ############################################

        # Image viewer setup
        self.image = QLabel()
        self.image.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.image.setAlignment(Qt.AlignCenter)

        # image_title that does not expand
        self.image_title = QLabel("My Image Title")
        self.image_title.setAlignment(Qt.AlignCenter)
        self.image_title.setStyleSheet("font-weight: bold; font-size: 16px;")
        self.image_title.setSizePolicy(
            self.image_title.sizePolicy().horizontalPolicy(), QSizePolicy.Fixed)

        self.image_title_line = QHBoxLayout()
        self.image_title_line.addWidget(self.toggle_button)
        self.image_title_line.addWidget(self.image_title)

        # image box
        image_box = QWidget()
        image_box_layout = QVBoxLayout(image_box)
        image_box_layout.addLayout(self.image_title_line)
        image_box_layout.addWidget(self.image)

        ############################################

        # Vertical splitter
        right_vertical = QSplitter(Qt.Vertical)
        right_vertical.addWidget(image_box)
        right_vertical.setStretchFactor(0, 5)  # Give image more space
        right_vertical.setStretchFactor(1, 1)  # Terminal less space

        ############################################

        # Horizontal splitter for sidebar and right area
        main_horizontal = QSplitter(Qt.Horizontal)
        main_horizontal.addWidget(sidebar_scroll_area)
        main_horizontal.addWidget(right_vertical)
        main_horizontal.setStretchFactor(0, 1)  # Sidebar smaller by default
        main_horizontal.setStretchFactor(1, 4)  # Right side bigger

        ############################################

        # Main layout
        main_layout = QHBoxLayout()
        main_layout.addWidget(main_horizontal)
        self.setLayout(main_layout)

        # Timer to update OpenCV image
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_content)
        self.timer.start(10)

        ############################################
        # code specific initialization:
        ############################################
        self.current_frame = None
        self.image.resizeEvent = self.on_window_resize

        self.folder_path = None
        self.file_path = None

    ########################################
    # Methods:
    ########################################

    ########################################
    # GUI event handlers:

    def toggle_sidebar(self):
        self.sidebar_widget.setVisible(not self.sidebar_widget.isVisible())
        if self.toggle_button.text() == "<":
            self.toggle_button.setText(">")
        else:
            self.toggle_button.setText("<")

    def on_radio_selected(self, id):
        pass

    def on_slider_change(self, value):
        self.progress_bar.setValue(value)
        self.colored_bar.set_value(value)
        self.terminal_output.log(value)
        pass

    def on_open_file_path_menu(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select File")
        self.file_path_box.setText(path)
        pass

    def on_open_folder_path_menu(self):
        path = QFileDialog.getExistingDirectory(self, "Select Folder")
        self.folder_path_box.setText(path)
        pass

    ########################################
    # update content related:

    def on_window_resize(self, event):
        self.repaint_image()
        pass
        event.accept()  # mark event as handled

    def set_image_title(self, text):
        self.image_title.setText(text)

    def update_content(self):
        try:
            self.current_frame = get_frame()
            self.repaint_image()
        except Exception as e:
            self.terminal_output.log("--------------------")
            self.terminal_output.log(f"[ERROR] {str(e)}:")
            self.terminal_output.log(traceback.format_exc)
            self.terminal_output.log("--------------------")

    def repaint_image(self):
        if self.current_frame is None:
            return

        rgb_image = cv2.cvtColor(self.current_frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        qt_image = QImage(rgb_image.data, w, h,
                          bytes_per_line, QImage.Format_RGB888)

        pixmap = QPixmap.fromImage(qt_image)

        # Scale pixmap to label size, keeping aspect ratio
        scaled_pixmap = pixmap.scaled(
            self.image.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        self.image.setPixmap(scaled_pixmap)

    ########################################


app = QApplication(sys.argv)
window = MainWindow()
window.resize(window_pixels_h, window_pixels_v)
window.show()
sys.exit(app.exec_())
