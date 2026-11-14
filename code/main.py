"""A minimal example GUI. Replace this file with your application."""

import os
import sys
import tkinter as tk
from importlib import import_module
from tkinter import ttk

# while True:
#     m = input()
#     if m != "q":
#         print(m)
#     else:
#         break


def main():
    """Show the example Tkinter window using the launcher-provided app name and icon."""
    root = tk.Tk()
    root.title(os.environ.get("PROGRAM_NAME", "Example GUI"))
    if os.environ.get("ICON_PATH"):
        root.iconbitmap(os.environ["ICON_PATH"])
    root.geometry("360x180")
    ttk.Label(root, text="Example GUI", padding=40).pack(expand=True)
    root.mainloop()


def main_qt(binding: str = "PySide6") -> int:
    """Show the Qt alternative using PyQt5, PyQt6, PySide2, or PySide6.

    Install the selected binding in the application environment first.
    PySide2 is the Qt 5 binding; there is no PySide5 package.
    PySide2 requires Python older than 3.11.
    """
    if binding not in ("PyQt5", "PyQt6", "PySide2", "PySide6"):
        raise ValueError(f"Unsupported Qt binding: {binding}")

    # Import only the selected binding so the Tkinter example needs no Qt dependency.
    QtWidgets = import_module(f"{binding}.QtWidgets")
    QtGui = import_module(f"{binding}.QtGui")
    app = QtWidgets.QApplication(sys.argv)
    window = QtWidgets.QWidget()
    window.setWindowTitle(os.environ.get("PROGRAM_NAME", "Example GUI"))
    if os.environ.get("ICON_PATH"):
        window.setWindowIcon(QtGui.QIcon(os.environ["ICON_PATH"]))
    window.resize(360, 180)
    layout = QtWidgets.QVBoxLayout(window)
    layout.setContentsMargins(40, 40, 40, 40)
    layout.addWidget(QtWidgets.QLabel("Example GUI"))
    window.show()

    # Qt 5 bindings use exec_(); Qt 6 uses exec().
    if binding in ("PyQt5", "PySide2"):
        return app.exec_()
    return app.exec()


if __name__ == "__main__":
    main()
    # To use Qt instead, replace main() above with:
    # sys.exit(main_qt("PySide6"))  # Or "PyQt5", "PyQt6", "PySide2".
