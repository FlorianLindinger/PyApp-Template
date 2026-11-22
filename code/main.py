"""Example app: a small window that shows what the launcher and "import pyapp_api" can do.

Replace this file with your application. Start it with the shortcut Setup created; it also runs
with plain "python main.py", where the launcher features simply do nothing.
"""

import os
import threading
import time
import tkinter as tk
from tkinter import ttk

import pyapp_api  # helpers from the launcher; overview: help(pyapp_api)

# Set by the buttons; acted on after the window has closed (see the end of main()).
after_close = {"crash": False, "restart": False}


def main():
    root = tk.Tk()
    root.title(os.environ.get("PROGRAM_NAME", "Example app"))  # the launcher passes the app's name ...
    if os.environ.get("ICON_PATH"):
        root.iconbitmap(os.environ["ICON_PATH"])  # ... and its icon
    started = "Started by the launcher." if pyapp_api.launched() else "Started without the launcher."
    status = tk.StringVar(value=started)

    def show(text):
        """Show a message in the window and print it (prints also go to the log)."""
        status.set(text)
        print(text)

    # --- Things the launcher reports to the app -----------------------------------------------

    # Runs when the app is ended from outside (Stop shortcut, Ctrl+C, the window's X): save here.
    pyapp_api.on_stop(lambda: print("Saving before the app is stopped ..."))

    # With instance_policy = "focus" or "prevent", starting the app again lands here instead of
    # starting a second copy. The callback runs on a background thread, so root.after hands the
    # work to Tkinter's own thread.
    def started_again(arguments, folder):
        root.after(0, show, f"Started again with {arguments or 'no arguments'}.")

    pyapp_api.on_new_start(started_again)

    # --- The buttons --------------------------------------------------------------------------

    def notify():
        sent = pyapp_api.notify("Hello", "A notification from the example app.")
        show("Notification sent." if sent else "No notification (needs the launcher and Start Menu shortcuts).")

    def long_task():
        def work():
            with pyapp_api.keep_awake():  # the PC does not go to sleep while this runs
                for step in range(1, 21):
                    time.sleep(0.15)
                    pyapp_api.set_progress(step / 20)  # progress on the taskbar button
                    root.after(0, show, f"Working ... {step * 5} %")
            pyapp_api.set_progress(None)
            pyapp_api.flash()  # draws attention if the user switched to another window meanwhile
            root.after(0, show, "Long task done.")

        threading.Thread(target=work, daemon=True).start()  # keeps the window responsive

    def minimize_and_flash():
        show("Minimized: the taskbar button flashes until you return to the app.")
        root.iconify()
        root.after(500, pyapp_api.flash)  # let Windows finish minimizing before flashing

    def ask():
        answer = pyapp_api.ask_yes_no("Do you like this example?")
        pyapp_api.message_box("Thank you!" if answer else "Then replace main.py with your own app.")

    def handled_error():
        try:
            int("not a number")  # a deliberate error
        except ValueError:
            path = pyapp_api.report_error(note="from the example's button")
            show(f"Error caught, crash log written: {path}" if path else "Error caught (no crash log without the launcher).")

    def crash():
        after_close["crash"] = True
        root.destroy()

    def restart():
        if not pyapp_api.launched():
            show("Restart needs the launcher: start the app with its shortcut.")
            return
        after_close["restart"] = True
        root.destroy()

    frame = ttk.Frame(root, padding=16)
    frame.pack(fill="both", expand=True)
    for text, command in (
        ("Send a notification", notify),
        ("Long task with taskbar progress", long_task),
        ("Minimize and flash", minimize_and_flash),
        ("Ask a question", ask),
        ("Handle an error (crash log, keeps running)", handled_error),
        ("Crash (see the crash report)", crash),
        ("Restart the app", restart),
    ):
        ttk.Button(frame, text=text, command=command).pack(fill="x", pady=2)
    ttk.Label(frame, textvariable=status, wraplength=320).pack(fill="x", pady=(12, 0))

    root.mainloop()

    # In the main thread, after the window has closed: a real crash and restart() both end the app.
    if after_close["crash"]:
        raise RuntimeError("A deliberate crash from the example's button")
    if after_close["restart"]:
        pyapp_api.restart()


if __name__ == "__main__":
    main()
