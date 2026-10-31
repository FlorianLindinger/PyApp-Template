"""Portable Tkinter task list. Replace this file with your own application.

Example: Start.cmd --title "My tasks" --data-file "C:\\Data\\tasks.json"
Uses the standard library and the template's optional shutdown API.
"""

import argparse
import json
import os
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk

from backend.shutdown import shutdown_requested


class TaskList:
    def __init__(self, root, data_file):
        self.root = root
        self.data_file = Path(data_file)
        self.tasks = []
        self.closing = False
        self.status = tk.StringVar(value="Ready")
        self.new_task = tk.StringVar()
        root.minsize(620, 440)
        root.geometry("720x500")
        root.protocol("WM_DELETE_WINDOW", self.close)
        style = ttk.Style(root)
        if "vista" in style.theme_names():
            style.theme_use("vista")
        style.configure("Title.TLabel", font=("Segoe UI", 20, "bold"))
        style.configure("Treeview", rowheight=30)
        style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"))
        content = ttk.Frame(root, padding=24)
        content.pack(fill="both", expand=True)
        content.columnconfigure(0, weight=1)
        content.rowconfigure(3, weight=1)
        ttk.Label(
            content, text="Make room for what matters.", style="Title.TLabel"
        ).grid(row=0, column=0, sticky="w")
        ttk.Label(
            content, text="A small task list. Your changes are saved automatically."
        ).grid(row=1, column=0, sticky="w", pady=(4, 20))
        add_row = ttk.Frame(content)
        add_row.grid(row=2, column=0, sticky="ew", pady=(0, 14))
        add_row.columnconfigure(0, weight=1)
        entry = ttk.Entry(add_row, textvariable=self.new_task)
        entry.grid(row=0, column=0, sticky="ew", ipady=5, padx=(0, 8))
        entry.bind("<Return>", lambda _event: self.add_task())
        ttk.Button(add_row, text="Add task", command=self.add_task).grid(
            row=0, column=1, ipady=3
        )
        list_frame = ttk.Frame(content)
        list_frame.grid(row=3, column=0, sticky="nsew")
        list_frame.rowconfigure(0, weight=1)
        list_frame.columnconfigure(0, weight=1)
        self.tree = ttk.Treeview(
            list_frame,
            columns=("state", "task"),
            show="headings",
            selectmode="extended",
        )
        self.tree.heading("state", text="Status")
        self.tree.heading("task", text="Task")
        self.tree.column("state", width=90, stretch=False)
        self.tree.column("task", width=420)
        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(
            list_frame, orient="vertical", command=self.tree.yview
        )
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.bind("<Double-1>", lambda _event: self.toggle_selected())
        self.tree.bind("<Delete>", lambda _event: self.remove_selected())
        self.tree.tag_configure("done", foreground="#6b7280")
        actions = ttk.Frame(content)
        actions.grid(row=4, column=0, sticky="ew", pady=(14, 14))
        ttk.Button(actions, text="Done / to do", command=self.toggle_selected).pack(
            side="left"
        )
        ttk.Button(actions, text="Remove selected", command=self.remove_selected).pack(
            side="left", padx=8
        )
        ttk.Button(actions, text="Close", command=self.close).pack(side="right")
        ttk.Label(content, textvariable=self.status).grid(row=5, column=0, sticky="w")
        self.load()
        self.refresh()
        entry.focus_set()
        root.after(150, self.poll_shutdown)

    def load(self):
        try:
            payload = json.loads(self.data_file.read_text(encoding="utf-8"))
            if not isinstance(payload, list) or not all(
                isinstance(item, dict)
                and isinstance(item.get("text"), str)
                and isinstance(item.get("done"), bool)
                for item in payload
            ):
                raise ValueError("Expected tasks with text and done values")
            self.tasks = payload
        except FileNotFoundError:
            pass
        except (OSError, ValueError) as error:
            print("[Error] Could not load tasks: {}".format(error))
            messagebox.showerror(
                "Could not open tasks",
                "{}\n\nThe existing file has not been changed.".format(error),
                parent=self.root,
            )
            self.data_file = self.data_file.with_name(
                self.data_file.stem + "-recovered.json"
            )

    def save(self):
        temporary = self.data_file.with_name(
            self.data_file.name + ".{}.tmp".format(os.getpid())
        )
        try:
            self.data_file.parent.mkdir(parents=True, exist_ok=True)
            temporary.write_text(
                json.dumps(self.tasks, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            os.replace(str(temporary), str(self.data_file))
            self.status.set("{} task(s) - Saved".format(len(self.tasks)))
            print("[Info] Saved {} task(s).".format(len(self.tasks)))
            return True
        except OSError as error:
            self.status.set("Changes could not be saved")
            print("[Error] Could not save tasks: {}".format(error))
            messagebox.showerror("Could not save tasks", str(error), parent=self.root)
            return False

    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        for index, task in enumerate(self.tasks):
            self.tree.insert(
                "",
                "end",
                iid=str(index),
                values=("Done" if task["done"] else "To do", task["text"]),
                tags=("done",) if task["done"] else (),
            )
        self.status.set(
            "{} task(s) - {} complete".format(
                len(self.tasks), sum(task["done"] for task in self.tasks)
            )
        )

    def add_task(self):
        text = self.new_task.get().strip()
        if not text:
            self.status.set("Write a task first")
            return
        self.tasks.append({"text": text, "done": False})
        self.new_task.set("")
        self.refresh()
        self.save()

    def toggle_selected(self):
        selection = self.tree.selection()
        for item in selection:
            task = self.tasks[int(item)]
            task["done"] = not task["done"]
        self.refresh()
        if selection:
            self.tree.selection_set(selection)
            self.save()

    def remove_selected(self):
        selection = {int(item) for item in self.tree.selection()}
        self.tasks = [
            task for index, task in enumerate(self.tasks) if index not in selection
        ]
        self.refresh()
        if selection:
            self.save()

    def poll_shutdown(self):
        if self.closing:
            return
        if shutdown_requested():
            print("[Info] Shutdown requested; saving tasks.")
            self.close()
        else:
            self.root.after(150, self.poll_shutdown)

    def close(self):
        if self.closing:
            return
        if not self.save() and not messagebox.askyesno(
            "Close without saving?",
            "Your latest changes could not be saved. Close anyway?",
            parent=self.root,
        ):
            return
        self.closing = True
        self.root.destroy()


def main():
    parser = argparse.ArgumentParser(description="A portable Tkinter task list")
    parser.add_argument("--title", default="Portable Task List")
    parser.add_argument(
        "--data-file",
        type=Path,
        default=Path(__file__).resolve().parent / "data" / "tasks.json",
    )
    args = parser.parse_args()
    root = tk.Tk()
    root.title(args.title)
    icon = Path(__file__).resolve().parent / "backend" / "icons" / "icon.ico"
    if icon.is_file():
        try:
            root.iconbitmap(str(icon))
        except tk.TclError:
            pass
    TaskList(root, args.data_file)
    root.mainloop()


if __name__ == "__main__":
    main()
