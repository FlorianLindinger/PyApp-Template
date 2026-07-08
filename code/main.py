

# ==============================
import sys
import time

print("Ready")
while True:
    msg = input()
    if msg == "error1":
        raise ImportError("error")
    elif msg == "error2":
        raise SyntaxError("error")
    elif msg == "error3":
        raise KeyboardInterrupt("error")
    elif msg == "error4":
        sys.exit(1)
    elif msg == "error5":
        import definitely_missing_package_abc123 #noqa #type:ignore
    elif msg == "error6":
        try:
            raise ValueError("inner")
        except ValueError as e:
            raise RuntimeError("outer") from e
    elif msg == "error7":
        1 / 0 #noqa # type:ignore
    elif msg == "error8":
        sys.exit("exit with message")
        
        
    elif msg == "exit_crash_code":
        sys.exit(0xC0000005)

    elif msg == "exit_crash_code_signed":
        sys.exit(-1073741819)

    elif msg == "fake_crash_code":
        import os
        os._exit(0xC0000005)
        
    elif msg == "stderr":
        print("this is stderr", file=sys.stderr)
        
    elif msg == "unicode":
        print("unicode test: äöü ß €")
    
    elif msg == "crash1":
        import os

        os._exit(1)
    elif msg == "crash2":
        import os

        os.abort()
    elif msg == "crash3":
        import ctypes

        ctypes.string_at(0)
    elif msg == "crash4":
        a = []
        while True:
            a.append(b"x" * 10_000_000)
    elif msg == "exit":
        break
    elif msg == "sleep":
        time.sleep(4)
        print(msg)
    elif msg in ["np", "numpy"]:
        import numpy  # noqa

        print("imported numpy")

    elif msg == "tv":
        print('Terminal_window.toggle_button_visible_state("stop")')
    elif msg == "te":
        print('Terminal_window.toggle_button_clickable_state("stop")')
    else:
        print(msg)

sys.exit()

# ==============================

# import tkinter as tk

# print("test")


# def main() -> None:
#     """Create and run a basic Tkinter window."""

#     # Create the main application window.
#     root = tk.Tk()

#     # Set the initial window size: width x height.
#     root.geometry("400x250")

#     # Start Tkinter's event loop.
#     root.mainloop()

# if __name__ == "__main__":
#     main()

# ==============================

# import sys

# from PySide6.QtWidgets import QApplication, QMainWindow


# class MainWindow(QMainWindow):
#     def __init__(self):
#         super().__init__()


# if __name__ == "__main__":
#     app = QApplication()  # sys.argv)

#     window = MainWindow()
#     window.show()
#     sys.exit(app.exec())

# ==============================


# # # ==============================================================================
# # # Add code at the bottom that runs with the start of the program.
# # # ==============================================================================
# # # Optional: Imports and converts user variables (e.g., name: value) in settings.yaml (access value via dictionary: s["name"]). Alternatively use settings.py directly.
# # from settings import s # <-needs pyyaml package
# # # ==============================================================================

# # import time

# # for i in range(50):
# #     print(i)
# #     time.sleep(0.1)
