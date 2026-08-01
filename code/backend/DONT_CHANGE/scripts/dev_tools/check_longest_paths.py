"""Find the longest project path and assess its Windows path-length risk."""

# ==============================
# settings

# ==============================
# import Python packages

import sys
from pathlib import Path

# ==============================
# import third-party packages

# ==============================
# import from files

CODE_DIR = Path(__file__).resolve().parents[4]
if str(CODE_DIR) not in sys.path:
    sys.path.insert(0, str(CODE_DIR))

from backend.DONT_CHANGE.scripts.generic_helpers import find_longest_paths

# ==============================
# local variables

# Many Windows tools still require traditional Win32 paths to stay within this
# conservative limit, even when long-path support is enabled elsewhere.
LEGACY_WINDOWS_PATH_LIMIT = 260
TOP_PATH_COUNT = 50
REPOSITORY_DIR = Path(__file__).resolve().parents[6]
ANSI_PATH = "\x1b[96m"
ANSI_RESET = "\x1b[0m"

# ==============================
# local functions/classes


def print_guidance(path_length: int) -> None:
    """Explain the current risk level and actions that reduce path length."""
    remaining = LEGACY_WINDOWS_PATH_LIMIT - path_length
    if remaining < 0:
        print(
            f"[Warning] This path exceeds the {LEGACY_WINDOWS_PATH_LIMIT}-character legacy Windows limit by {-remaining} characters."
        )
    elif remaining <= 20:
        print(f"[Warning] Only {remaining} characters remain before the legacy Windows path limit.")
    else:
        print(f"[Info] {remaining} characters remain before the legacy Windows path limit.")

    print("\n[Info] If this becomes a problem:")
    print("- Move the repository closer to the drive root, for example C:\\src\\App-Name.")
    print("- Shorten deeply nested folder or file names.")
    print("- Keep generated environments and package folders out of deeply nested project paths.")
    print(
        "- Enable Windows long paths and Git core.longpaths where appropriate, but do not rely on them for every tool."
    )


def check_longest_paths() -> int:
    """Print the project's longest paths and their Windows path-risk assessment."""
    print(f"[Info] Scanning repository: {REPOSITORY_DIR}")
    try:
        longest_paths, scanned_files, scanned_directories = find_longest_paths(
            REPOSITORY_DIR,
            top_path_count=TOP_PATH_COUNT,
            excluded_dir_names=(".git",),
        )
    except OSError as error:
        print(f"[Error] Could not finish scanning paths: {error}")
        return 1

    print(f"[Info] Scanned {scanned_files} files and {scanned_directories} directories; .git metadata was skipped.")
    print(f"[Info] Top {len(longest_paths)} longest paths:")
    for index, path in enumerate(longest_paths, start=1):
        print(f"{index:>2}. {len(str(path)):>3} characters  {ANSI_PATH}{path}{ANSI_RESET}")
    path_length = len(str(longest_paths[0]))
    print_guidance(path_length)
    return 0


# ==============================
# main function


def main() -> int:
    """Repeatedly check paths until the user chooses to exit."""
    while True:
        exit_code = check_longest_paths()
        if exit_code:
            return exit_code
        try:
            input("\n[Input] Press Enter to recheck: ")
        except EOFError:
            return 0
        print()


# ==============================
# execute main function


if __name__ == "__main__":
    raise SystemExit(main())
