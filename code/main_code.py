import time

# import settings

for i in range(50):
    print(i)
    time.sleep(0.05)
while True:
    msg = input()
    if msg == "error":
        raise Exception("error")
    elif msg == "crash1":
        raise RuntimeError("intentional crash test")
    elif msg == "crash2":
        import os

        os._exit(1)
    elif msg == "crash3":
        import os

        os.abort()
    elif msg == "crash4":
        import ctypes

        ctypes.string_at(0)  # dereference NULL -> segfault on most platforms
    elif msg == "crash5":
        a = []
        while True:
            a.append(b"x" * 10_000_000)
    elif msg == "exit":
        break
    elif msg == "sleep":
        time.sleep(4)
        print(msg)
    elif msg in ["np","numpy"]:
        import numpy

    elif msg == "tv":
        print('Terminal_window.toggle_button_visible_state("stop")')
    elif msg == "te":
        print('Terminal_window.toggle_button_clickable_state("stop")')
    else:
        print(msg)



import sys

sys.exit()


import sys

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMainWindow


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        if sys.argv[1] != "":
            self.setWindowIcon(QIcon(sys.argv[1]))
        if sys.argv[2] != "":
            self.setWindowTitle(sys.argv[2])


if __name__ == "__main__":
    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


# # # ==============================================================================
# # # Add code at the bottom that runs with the start of the program.
# # # ==============================================================================
# # # Optional: Imports and converts user variables (e.g., name: value) in settings.yaml (access value via dictionary: s["name"]). Alternatively use settings.py directly.
# # from settings import s # <-needs pyyaml package # noqa isort: skip type: ignore fmt: off
# # # ==============================================================================

# # import time

# # for i in range(50):
# #     print(i)
# #     time.sleep(0.1)
