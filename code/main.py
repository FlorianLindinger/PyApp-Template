# ==============================
import os
import sys
import time

if os.environ["PROGRAM_HAS_TERMINAL"] == "0":
    import tkinter as tk
    from tkinter import ttk



    root = tk.Tk()
    root.title(os.environ["PROGRAM_NAME"])
    root.iconbitmap(os.environ["ICON_PATH"])
    root.geometry("400x250")

    pending_messages: list[str] = []
    is_open = [True]

    output_text = tk.Text(root, height=10, state="disabled")
    output_text.pack(fill="both", expand=True, padx=12, pady=(12, 6))

    input_frame = ttk.Frame(root)
    input_frame.pack(fill="x", padx=12, pady=(0, 12))
    message_entry = ttk.Entry(input_frame)
    message_entry.pack(side="left", fill="x", expand=True)
    message_entry.focus_set()

    def append_output(message: str) -> None:
        output_text.configure(state="normal")
        output_text.insert("end", f"{message}\n")
        output_text.configure(state="disabled")
        output_text.see("end")

    def submit_message(_event=None) -> None:
        pending_messages.append(message_entry.get())
        message_entry.delete(0, "end")

    def close_window() -> None:
        is_open[0] = False

    def process_message(msg: str) -> bool:
        if msg == "1":
            raise ImportError("error")
        elif msg == "2":
            raise SyntaxError("error")
        elif msg == "3":
            raise KeyboardInterrupt("error")
        elif msg == "4":
            sys.exit(1)
        elif msg == "5":
            import definitely_missing_package_abc123  # noqa # type: ignore
        elif msg == "6":
            try:
                raise ValueError("inner")
            except ValueError as error:
                raise RuntimeError("outer") from error
        elif msg == "7":
            1 / 0  # noqa # type: ignore
        elif msg == "8":
            sys.exit("exit with message")
        elif msg == "9":
            sys.exit(0xC0000005)
        elif msg == "10":
            sys.exit(-1073741819)
        elif msg == "11":
            os._exit(0xC0000005)
        elif msg == "12":
            print("this is stderr", file=sys.stderr)
        elif msg == "13":
            append_output("unicode test: äöü ß €")
        elif msg == "14":
            os._exit(1)
        elif msg == "15":
            os.abort()
        elif msg == "16":
            import ctypes

            ctypes.string_at(0)
        elif msg == "17":
            allocated = []
            while True:
                allocated.append(b"x" * 10_000_000)
        elif msg == "exit":
            return False
        elif msg == "sleep":
            time.sleep(4)
            append_output(msg)
        elif msg in ["np", "numpy"]:
            import numpy  # noqa

            append_output("imported numpy")
        else:
            append_output(msg)
        return True

    submit_button = ttk.Button(input_frame, text="Send", command=submit_message)
    submit_button.pack(side="left", padx=(6, 0))
    message_entry.bind("<Return>", submit_message)
    root.protocol("WM_DELETE_WINDOW", close_window)

    append_output("Ready")
    while is_open[0]:
        root.update()
        if pending_messages and not process_message(pending_messages.pop(0)):
            break
        time.sleep(0.01)
    root.destroy()
    
    
else:
    print("Ready")
    while True:
        msg = input()
        if msg == "1":
            raise ImportError("error")
        elif msg == "2":
            raise SyntaxError("error")
        elif msg == "3":
            raise KeyboardInterrupt("error")
        elif msg == "4":
            sys.exit(1)
        elif msg == "5":
            import definitely_missing_package_abc123  # noqa #type:ignore
        elif msg == "6":
            try:
                raise ValueError("inner")
            except ValueError as e:
                raise RuntimeError("outer") from e
        elif msg == "7":
            1 / 0  # noqa # type:ignore
        elif msg == "8":
            sys.exit("exit with message")

        elif msg == "9":
            sys.exit(0xC0000005)

        elif msg == "10":
            sys.exit(-1073741819)

        elif msg == "11":
            import os

            os._exit(0xC0000005)

        elif msg == "12":
            print("this is stderr", file=sys.stderr)

        elif msg == "13":
            print("unicode test: äöü ß €")

        elif msg == "14":
            import os

            os._exit(1)
        elif msg == "15":
            import os

            os.abort()
        elif msg == "16":
            import ctypes

            ctypes.string_at(0)
        elif msg == "17":
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

        else:
            print(msg)

    # sys.exit()

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
