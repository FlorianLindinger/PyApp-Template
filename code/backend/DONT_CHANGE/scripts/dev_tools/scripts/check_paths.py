"""Find the longest project path and assess its Windows path-length risk."""

from __future__ import annotations

import os
import stat
from pathlib import Path


# Many Windows tools still require traditional Win32 paths to stay within this
# conservative limit, even when long-path support is enabled elsewhere.
LEGACY_WINDOWS_PATH_LIMIT = 260
TOP_PATH_COUNT = 50
REPOSITORY_DIR = Path(__file__).resolve().parents[6]
ANSI_PATH = "\x1b[96m"
ANSI_RESET = "\x1b[0m"


def is_reparse_point(path: Path) -> bool:
    """Return whether *path* is a Windows reparse point or a symbolic link."""
    try:
        attributes = path.stat(follow_symlinks=False).st_file_attributes
    except OSError:
        return True
    return path.is_symlink() or bool(attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))


def find_longest_paths() -> tuple[list[Path], int, int]:
    """Return the longest file or directory paths below the repository and scan counts."""
    paths = [REPOSITORY_DIR]
    scanned_files = 0
    scanned_directories = 0

    for current_directory, directory_names, file_names in os.walk(REPOSITORY_DIR, topdown=True, followlinks=False):
        current_path = Path(current_directory)
        kept_directories: list[str] = []
        for directory_name in directory_names:
            directory_path = current_path / directory_name
            if directory_name == ".git" or is_reparse_point(directory_path):
                continue
            kept_directories.append(directory_name)
            scanned_directories += 1
            paths.append(directory_path)
        directory_names[:] = kept_directories

        for file_name in file_names:
            file_path = current_path / file_name
            if is_reparse_point(file_path):
                continue
            scanned_files += 1
            paths.append(file_path)

    paths.sort(key=lambda path: len(str(path)), reverse=True)
    return paths[:TOP_PATH_COUNT], scanned_files, scanned_directories


def print_guidance(path_length: int) -> None:
    """Explain the current risk level and actions that reduce path length."""
    remaining = LEGACY_WINDOWS_PATH_LIMIT - path_length
    if remaining < 0:
        print(f"[Warning] This path exceeds the {LEGACY_WINDOWS_PATH_LIMIT}-character legacy Windows limit by {-remaining} characters.")
    elif remaining <= 20:
        print(f"[Warning] Only {remaining} characters remain before the legacy Windows path limit.")
    else:
        print(f"[Info] {remaining} characters remain before the legacy Windows path limit.")

    print("\n[Info] If this becomes a problem:")
    print("- Move the repository closer to the drive root, for example C:\\src\\PyApp-Template.")
    print("- Shorten deeply nested folder or file names.")
    print("- Keep generated environments and package folders out of deeply nested project paths.")
    print("- Enable Windows long paths and Git core.longpaths where appropriate, but do not rely on them for every tool.")


def check_paths() -> int:
    """Print the project's longest paths and their Windows path-risk assessment."""
    print(f"[Info] Scanning repository: {REPOSITORY_DIR}")
    try:
        longest_paths, scanned_files, scanned_directories = find_longest_paths()
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


def main() -> int:
    """Repeatedly check paths until the user chooses to exit."""
    while True:
        exit_code = check_paths()
        if exit_code:
            return exit_code
        try:
            input("\n[Input] Press Enter to recheck: ")
        except EOFError:
            return 0
        print()


if __name__ == "__main__":
    raise SystemExit(main())
