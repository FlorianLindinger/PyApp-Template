"""Find the longest project paths and assess their Windows path-length risk."""

# =========================
# settings

fail_message: str = "[Error] Failed to run {script_name}: {error}"  # "{error}" will be replaced with the error, "{script_name}" with script name
close_terminal_on_finish: bool = False
rel_path_to_root_dir: str = (
    "\\..\\..\\..\\.."  # path to pyproject.toml containing folder
)
TOP_PATH_COUNT = 20
ANSI_PATH = "\x1b[96m"

# =========================

try:
    # =========================
    # import Python packages

    import os
    import sys

    # =========================
    # import third-party packages

    # =========================
    # import from files

    # add root dir to resolve file imports for debug cases where this script is called on its own:
    ROOT_DIR = os.path.normpath(os.path.dirname(__file__) + rel_path_to_root_dir)
    if ROOT_DIR not in sys.path:
        sys.path.insert(0, ROOT_DIR)

    from backend.DONT_CHANGE.scripts.common_code import (
        print_traceback,
    )
    from backend.DONT_CHANGE.scripts.generic_helpers import (
        ANSI_RESET,
        close_terminal,
        find_longest_paths,
        get_script_name,
        input_warn,
    )

    # =========================
    # local variables
    # =========================

    LEGACY_WINDOWS_PATH_LIMIT = 260

    # =========================
    # local functions/classes
    # =========================

    def print_guidance(path_length: int) -> None:
        """Explain the current risk level and actions that reduce path length."""
        remaining = LEGACY_WINDOWS_PATH_LIMIT - path_length
        if remaining < 0:
            print(
                f"[Warning] This path exceeds the {LEGACY_WINDOWS_PATH_LIMIT}-character legacy Windows limit by {-remaining} characters."
            )
        elif remaining <= 20:
            print(
                f"[Warning] Only {remaining} characters remain before the legacy Windows path limit."
            )
        else:
            print(
                f"[Info] {remaining} characters remain before the legacy Windows path limit."
            )

        print("\n[Info] If this becomes a problem:")
        print(
            "- Move the repository closer to the drive root, for example C:\\src\\App-Name."
        )
        print("- Shorten deeply nested folder or file names.")
        print(
            "- Keep generated environments and package folders out of deeply nested project paths."
        )
        print(
            "- Enable Windows long paths and Git core.longpaths where appropriate, but do not rely on them for every tool."
        )

    def check_longest_paths() -> None:
        """Print the project's longest paths and their Windows path-risk assessment."""
        print("[Info] Scanning repository:")
        print(f"{ANSI_PATH}{ROOT_DIR}{ANSI_RESET}")
        longest_paths, scanned_files, scanned_directories = find_longest_paths(
            ROOT_DIR,
            top_path_count=TOP_PATH_COUNT,
            excluded_dir_names=(".git",),
        )
        print(
            f"[Info] Scanned {scanned_files} files and {scanned_directories} directories; .git metadata was skipped."
        )
        print(f"[Info] Top {len(longest_paths)} longest paths:")
        for index, path in enumerate(longest_paths, start=1):
            relative_path = path.relative_to(ROOT_DIR)
            print(
                f"{index:>2}. {len(str(path)):>3} characters  {ANSI_PATH}{relative_path}{ANSI_RESET}"
            )
        print_guidance(len(str(longest_paths[0])))

    # =========================
    # main function
    # =========================

    def main() -> None:
        """Repeatedly check paths until the user chooses to exit."""
        while True:
            check_longest_paths()
            try:
                input("\n[Input] Press Enter to recheck: ")
            except EOFError:
                return
            print()

    # =========================
    # execute main function
    # =========================

    if __name__ == "__main__":
        try:
            main()
        except Exception as error:
            print_traceback(
                fail_message.format(error=error, script_name=get_script_name())
            )
            if (
                sys.stdin.isatty() and sys.stdout.isatty()
            ):  # check if interactive terminal
                input_warn("[Error] Press enter to exit")
        if close_terminal_on_finish:
            close_terminal()

    # =========================

except Exception as error:
    import os
    import sys
    import traceback

    print()
    print()
    print("=" * 30)
    print(
        fail_message.format(
            error=error, script_name=__file__.replace("\\", "/").rsplit("/", 1)[-1]
        )
    )
    print("-" * 30)
    print(traceback.format_exc())
    print("=" * 30)
    if sys.stdin.isatty() and sys.stdout.isatty():  # check if interactive terminal
        input("[Error] Press enter to exit")
    if close_terminal_on_finish:
        os._exit(
            1
        )  # instead of sys.exit(1) to prevent exception by script calling this script -> closing terminal
