"""A minimal example GUI. Replace this file with your application."""

import tkinter as tk
from tkinter import ttk


def main():
    root = tk.Tk()
    root.title("Example GUI")
    root.geometry("360x180")
    ttk.Label(root, text="Example GUI", padding=40).pack(expand=True)

    root.mainloop()


if __name__ == "__main__":
    main()
