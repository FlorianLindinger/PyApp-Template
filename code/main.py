"""A minimal example GUI. Replace this file with your application."""

import os
import tkinter as tk
from tkinter import ttk


def main():
    root = tk.Tk()
    root.title(os.environ.get("PROGRAM_NAME", "Example GUI"))
    if os.environ.get("ICON_PATH"):
        root.iconbitmap(os.environ["ICON_PATH"])
    root.geometry("360x180")
    ttk.Label(root, text="Example GUI", padding=40).pack(expand=True)

    root.mainloop()


if __name__ == "__main__":
    main()
