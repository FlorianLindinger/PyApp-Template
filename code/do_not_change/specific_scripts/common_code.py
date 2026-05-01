# colored print and input

ANSI_WARN = "\x1b[1;37;41m"  # white text, red bg, bold
ANSI_SUCCESS = "\x1b[1;37;42m"  # white text, green bg, bold
ANSI_RESET = "\033[0m"


def print_warn(msg, sep: str | None = " ", end: str | None = "\n"):
    print(f"{ANSI_WARN}{msg}{ANSI_RESET}", sep=sep, end=end)


def input_warn(msg):
    input(f"{ANSI_WARN}{msg}{ANSI_RESET}")


def input_success(msg):
    input(f"{ANSI_SUCCESS}{msg}{ANSI_RESET}")

# colored traceback related
try:
    import rich.box
    import rich.console
    import rich.panel
    import rich.text
    import rich.traceback

    # enable colored traceback (needed especially before python 3.13)
    rich.traceback.install(show_locals=False)

    def print_traceback(message="Error", add_press_enter_to_exit=False) -> None:
        import sys  # noqa

        exc_type, exc_value, tb = sys.exc_info()
        if exc_type is None or exc_value is None:
            rich.console.Console().print(
                "[yellow][Warning] Running print_traceback function without active exception.[/yellow]"
            )
            if add_press_enter_to_exit:
                rich.console.Console().print("[red]Press enter to exit[/red]")
        else:
            panel = rich.panel.Panel(
                rich.traceback.Traceback.from_exception(
                    exc_type,
                    exc_value,
                    tb,
                    show_locals=False,
                ),
                title=rich.text.Text(message, style="bold red on white"),
                title_align="left",
                subtitle=rich.text.Text("Press Enter to exit", style="bold red on white")
                if add_press_enter_to_exit
                else None,
                subtitle_align="left",
                box=rich.box.HEAVY,
                border_style="bold red",
                padding=(1, 2),
                expand=False,
            )
            rich.console.Console().print(panel)

        if add_press_enter_to_exit:
            input()
            import signal  # noqa

            os.kill(
                os.getppid(), signal.SIGTERM
            )  # kills even terminal launched by cmd and terminal from script calling this script

except Exception:
    import os

    print(
        r'Failed during setup of rich traceback. Is "rich" package installed in the code\do_not_change\python_packages folder?'
    )
    print("Press enter to exit")
    input()
    os._exit(1)


