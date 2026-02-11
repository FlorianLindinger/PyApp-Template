import sys
import time

import numpy as np

for i in range(100):
    print(i)
    time.sleep(0.02)
    
import os
print(os.getcwd())

    
# asd

# test2.py script finishes naturally
sys.exit(0)




import sys
import ctypes
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel

# Tell Windows to use this AppID for this process
myAppID = "test2"
ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myAppID)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("My Custom App")
        self.resize(400, 300)
        
        # Optional: Set a specific window icon here if you want
        # self.setWindowIcon(QIcon("icon.ico")) 

if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    # 3. Important: If you use a custom icon, set it for the app as well
    # app.setWindowIcon(QIcon("icon.ico"))
    
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

# import time
# import sys
# import ctypes

# ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("test2")

# for i in range(50):
#     print(i)
#     time.sleep(0.1)

# input("Press Enter to exit...")
# sys.exit()

# # app/app.py
# import sys
# # import ctypes
# import traceback

# # APPID = "test3"

# # if sys.platform.startswith("win"):
# #     ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APPID)

# try:
#     from PyQt5.QtWidgets import QApplication, QMainWindow

#     def main():
#         app = QApplication(sys.argv)
#         win = QMainWindow()
#         win.setWindowTitle("My PyQt5 App")
#         win.resize(900, 600)
#         win.show()
#         sys.exit(app.exec_())

#     if __name__ == "__main__":
#         main()

# except Exception as e:
#     print(traceback.format_exc())
#     input("Press Enter to exit...")
#     sys.exit(1)
    
    
    
    


# import sys
# import traceback
# import os

# # def set_appusermodel_id(appid: str) -> None:
# #     if sys.platform.startswith("win"):
# #         import ctypes
# #         ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(appid)

# # set_appusermodel_id("test2")  # must match the launcher’s ID

# # from PyQt5.QtWidgets import QApplication
# # app = QApplication(sys.argv)

# # input("Press enter to exit")

# # print(os.getcwd())
# # os.chdir(os.path.dirname(os.path.abspath(__file__)))
# # print(os.getcwd())

# try:
#     from GUI_code import pyqt5_helpers

#     pyqt5_helpers.Q_start()

#     widget = pyqt5_helpers.Q_sidebar_GUI()

#     widget.sidebar.add(pyqt5_helpers.QLabel("test"))
#     widget.sidebar.add(pyqt5_helpers.Q_file_path(label="test"))

#     # widget.sidebar.add(QLabel("test"))


#     pyqt5_helpers.Q_end(widget)
# except SystemExit:
#     pass
# except:
#     print(traceback.format_exc())
#     input("Press enter to exit")

# # input("Press enter to exit")


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
