"""Validated filesystem operations and path utilities."""

import os
import sys
from collections.abc import Sequence
from pathlib import Path


def delete_folder_safe(
    folder_abs_path: str | os.PathLike[str],
    *,
    prompt_message: str = "Delete this folder? (confirm that it is not an important one) [y/n]: ",
    allowed_base_abs_path: str | os.PathLike[str] | None = None,
    expected_folder_name: str | None = None,
    required_included_files: list[str] | tuple[str, ...] | None = (),
    required_included_dirs: list[str] | tuple[str, ...] | None = (),
    allow_empty_without_markers: bool = True,
    require_direct_child_of_allowed_base: bool = False,
    allow_filesystem_root_base: bool = False,
    min_path_depth: int | None = 4,
    max_size_GB_before_prompt: float | None = 1.0,
    max_size_check_seconds: float | None = 5.0,
    prompt_instead_of_requirement_failure: bool = True,
    always_prompt_for_confirmation: bool = False,
    print_on_deletion: bool = False,
) -> bool:
    """Delete a directory only after path, identity, and size checks pass.

    ``folder_abs_path`` must be an absolute path. If ``allowed_base_abs_path``
    is not ``None``, it must also be an absolute path. The target path and any
    allowed-base path themselves must not be symlinks, junctions, or Windows
    reparse points. After resolving both paths, the target must be inside the
    allowed base, must not be the allowed base, and must not be a filesystem
    root. The allowed base may not be a filesystem root unless
    ``allow_filesystem_root_base`` is true. Pass ``allowed_base_abs_path=None``
    to skip the base existence and containment checks. If the target is absent,
    this returns ``True`` only after the relevant path-safety checks pass.

    ``require_direct_child_of_allowed_base`` requires the target to be an
    immediate child of the allowed base. ``expected_folder_name`` requires the
    target's final folder name to match.

    ``required_included_files`` and ``required_included_dirs`` require exact
    file or directory names directly inside the target. Marker names may not be
    absolute paths, drive-qualified paths, ``.``, ``..``, or contain path
    separators. Pass ``None`` or an empty sequence for no marker requirements.
    Set ``allow_empty_without_markers`` to skip marker checks only when the
    target contains nothing except empty folders and 0-byte files.

    ``min_path_depth`` warns for shallow paths. ``max_size_GB_before_prompt``
    warns for large folders. Interactive warnings ask for confirmation;
    non-interactive warnings raise. Set either value to ``None`` to disable
    that check. ``max_size_check_seconds`` limits folder-size and empty-folder
    scans; if the size scan times out, the measured size is a lower bound. Set
    it to ``None`` to disable scan timeouts.

    With ``prompt_instead_of_requirement_failure=True`` and interactive stdin,
    size/empty scan failures and missing markers prompt instead of raising.
    Hard path-safety failures always raise. If
    ``always_prompt_for_confirmation`` is true, a final confirmation prompt is
    shown after all safety checks; in non-interactive mode it raises instead.

    Returns ``True`` if the folder was absent or deleted, and ``False`` only
    when the user cancels an interactive prompt.
    """

    def _raise_walk_error(error: OSError) -> None:
        raise error

    def _format_bytes(num_bytes: float) -> str:
        """Format bytes to for example kB and GB."""
        units = ["B", "KB", "MB", "GB", "TB"]

        for unit in units:
            if num_bytes < 1024 or unit == units[-1]:
                if unit == "B":
                    return f"{int(num_bytes)} {unit}"
                else:
                    return f"{num_bytes:.2f} {unit}"
            num_bytes /= 1024
        return f"{num_bytes} B"

    def _is_filesystem_root_path(path: str | os.PathLike[str]) -> bool:
        path_text = os.path.abspath(os.fspath(path))
        return path_text == os.path.abspath(os.path.join(path_text, os.pardir))

    def _validate_required_child_names(
        names: list[str] | tuple[str, ...], label: str
    ) -> tuple[str, ...]:
        """WIP"""
        validated_names = []
        for name in names:
            name_text = os.fspath(name)
            drive, _tail = os.path.splitdrive(name_text)
            if (
                name_text in {"", ".", ".."}
                or drive
                or os.path.isabs(name_text)
                or "/" in name_text
                or "\\" in name_text
            ):
                raise ValueError(
                    f'Required {label} marker must be a direct child name: "{name_text}"'
                )
            validated_names.append(name_text)
        return tuple(validated_names)

    def _is_symlink_or_junction(path: str | os.PathLike[str]) -> bool:
        """Return whether path is a Windows symlink or junction."""
        path_text = os.fspath(path)
        if os.path.islink(path_text):
            return True

        isjunction = getattr(os.path, "isjunction", None)
        if isjunction is not None and isjunction(path_text):
            return True

        try:
            file_attributes = getattr(os.lstat(path_text), "st_file_attributes", 0)
        except OSError:
            return False
        return bool(file_attributes & 0x400)  # FILE_ATTRIBUTE_REPARSE_POINT

    def _get_folder_size(
        folder: str | os.PathLike[str], timeout_seconds: float | None = None
    ) -> tuple[int, bool]:
        total = 0
        deadline = None
        get_time = None
        if timeout_seconds is not None:
            if timeout_seconds <= 0:
                raise ValueError(
                    f"Folder scan timeout must be greater than zero: {timeout_seconds}"
                )
            import time

            get_time = time.monotonic
            deadline = get_time() + timeout_seconds

        def _scan_timed_out() -> bool:
            if deadline is not None and get_time is not None and get_time() > deadline:
                return True
            return False

        for root, _dirs, files in os.walk(folder, onerror=_raise_walk_error):
            if _scan_timed_out():
                return total, True
            for filename in files:
                if _scan_timed_out():
                    return total, True
                path = os.path.join(root, filename)
                if os.path.isfile(path):
                    total += os.path.getsize(path)
        return total, False

    folder_path_text = os.fspath(folder_abs_path)
    if not os.path.isabs(folder_path_text):
        raise ValueError(f'Folder path must be absolute: "{folder_path_text}"')

    allowed_base_text = None
    if allowed_base_abs_path is not None:
        allowed_base_text = os.fspath(allowed_base_abs_path)
        if not os.path.isabs(allowed_base_text):
            raise ValueError(
                f'Allowed base path must be absolute: "{allowed_base_text}"'
            )
    elif require_direct_child_of_allowed_base:
        raise ValueError(
            "Cannot require direct child of allowed base when no allowed base path is configured."
        )

    if required_included_files is None:
        required_included_files = ()
    if required_included_dirs is None:
        required_included_dirs = ()
    required_included_files = _validate_required_child_names(
        required_included_files, "file"
    )
    required_included_dirs = _validate_required_child_names(
        required_included_dirs, "directory"
    )

    if max_size_GB_before_prompt is not None and max_size_GB_before_prompt < 0:
        raise ValueError(
            f"Maximum folder size must be zero or greater: {max_size_GB_before_prompt}"
        )
    if max_size_check_seconds is not None and max_size_check_seconds <= 0:
        raise ValueError(
            f"Folder scan timeout must be greater than zero: {max_size_check_seconds}"
        )

    if _is_symlink_or_junction(folder_path_text):
        raise ValueError(
            f'Refusing to delete symlink or junction path: "{folder_path_text}"'
        )
    if allowed_base_text is not None and _is_symlink_or_junction(allowed_base_text):
        raise ValueError(
            f'Allowed base path may not be a symlink or junction: "{allowed_base_text}"'
        )

    target_path = os.path.realpath(folder_path_text)

    if _is_filesystem_root_path(target_path):
        raise ValueError(f"Refusing to delete filesystem root: {target_path}")

    if allowed_base_text is not None:
        base_path = os.path.realpath(allowed_base_text)

        if not os.path.exists(base_path):
            raise FileNotFoundError(f"Allowed base does not exist: {base_path}")

        if not os.path.isdir(base_path):
            raise NotADirectoryError(f"Allowed base is not a directory: {base_path}")

        if _is_filesystem_root_path(base_path) and not allow_filesystem_root_base:
            raise ValueError(f"Allowed base may not be a filesystem root: {base_path}")

        if os.path.normcase(target_path) == os.path.normcase(base_path):
            raise ValueError(
                f"Refusing to delete the allowed base directory itself: {target_path}"
            )

        try:
            common_path = os.path.commonpath([base_path, target_path])
        except ValueError as exc:
            raise ValueError(
                f"Refusing to delete directory outside allowed base.\nTarget: {target_path}\nAllowed base: {base_path}"
            ) from exc

        if os.path.normcase(common_path) != os.path.normcase(base_path):
            raise ValueError(
                f"Refusing to delete directory outside allowed base.\nTarget: {target_path}\nAllowed base: {base_path}"
            )

        if require_direct_child_of_allowed_base and os.path.normcase(
            os.path.dirname(target_path)
        ) != os.path.normcase(base_path):
            raise ValueError(
                "Refusing to delete directory because it is not directly inside the allowed base.\n"
                f"Target: {target_path}\nAllowed base: {base_path}"
            )

    if not os.path.exists(target_path):
        return True

    is_below_min_path_depth = False
    path_depth = 0
    if min_path_depth is not None:
        if min_path_depth < 0:
            raise ValueError(
                f"Minimum path depth must be zero or greater: {min_path_depth}"
            )
        _drive, path_without_drive = os.path.splitdrive(os.path.normpath(target_path))
        path_without_root = path_without_drive.strip("\\/")
        path_depth = len(
            [part for part in path_without_root.replace("\\", "/").split("/") if part]
        )
        is_below_min_path_depth = path_depth < min_path_depth

    if (
        expected_folder_name is not None
        and os.path.basename(target_path).lower() != expected_folder_name.lower()
    ):
        raise RuntimeError(
            f'Refusing to delete "{target_path}" because its folder name is not "{expected_folder_name}".'
        )

    if not os.path.isdir(target_path):
        raise NotADirectoryError(f"Target is not a directory: {target_path}")

    if always_prompt_for_confirmation and not sys.stdin.isatty():
        raise ValueError(
            f'Refusing to delete "{target_path}" without interactive confirmation.'
        )

    folder_size: float | None = None
    folder_size_is_partial = False
    is_above_max_size = False
    max_size_bytes: int | None = None
    if max_size_GB_before_prompt is not None:
        try:
            folder_size, folder_size_is_partial = _get_folder_size(
                target_path, timeout_seconds=max_size_check_seconds
            )
        except OSError as error:
            if not prompt_instead_of_requirement_failure or not sys.stdin.isatty():
                raise
            print()
            print("Folder deletion size check warning:")
            print(f"Folder: {target_path}")
            print(f"Could not determine folder size: {error}")
            print()
            answer = input("Delete anyway? [y/n]: ").strip().lower()
            if answer not in {"y", "yes"}:
                print("Cancelled folder deletion.")
                return False
        if folder_size_is_partial:
            if folder_size is None:
                raise RuntimeError(
                    f'Could not determine a partial folder size for "{target_path}".'
                )
            if not prompt_instead_of_requirement_failure or not sys.stdin.isatty():
                raise ValueError(
                    f'Could not finish size check for "{target_path}" within {max_size_check_seconds:g} seconds. '
                    f"Measured at least {_format_bytes(folder_size)}."
                )
            print()
            print("Folder deletion size check warning:")
            print(f"Folder: {target_path}")
            print(f"Size check timed out after {max_size_check_seconds:g} seconds.")
            print(f"Measured at least: {_format_bytes(folder_size)}")
            print()
            answer = input("Delete anyway? [y/n]: ").strip().lower()
            if answer not in {"y", "yes"}:
                print("Cancelled folder deletion.")
                return False
        if folder_size is not None:
            max_size_bytes = int(max_size_GB_before_prompt * 1024 * 1024 * 1024)
            is_above_max_size = folder_size > max_size_bytes

    if required_included_files or required_included_dirs:
        try:
            is_empty = True
            empty_check_deadline = None
            empty_check_get_time = None
            if max_size_check_seconds is not None:
                import time

                empty_check_get_time = time.monotonic
                empty_check_deadline = empty_check_get_time() + max_size_check_seconds

            def _check_empty_scan_timeout() -> None:
                if (
                    empty_check_deadline is not None
                    and empty_check_get_time is not None
                    and empty_check_get_time() > empty_check_deadline
                ):
                    raise TimeoutError

            for root, _dirs, files in os.walk(target_path, onerror=_raise_walk_error):
                _check_empty_scan_timeout()
                for filename in files:
                    _check_empty_scan_timeout()
                    file_path = os.path.join(root, filename)
                    if os.path.isfile(file_path) and os.path.getsize(file_path) > 0:
                        is_empty = False
                        break
                if not is_empty:
                    break
        except TimeoutError as error:
            if not prompt_instead_of_requirement_failure or not sys.stdin.isatty():
                raise ValueError(
                    f'Could not finish empty-folder check for "{target_path}" within {max_size_check_seconds:g} seconds.'
                ) from error
            print()
            print("Folder deletion empty-check warning:")
            print(f"Folder: {target_path}")
            print(
                f"Empty-folder check timed out after {max_size_check_seconds:g} seconds."
            )
            print()
            answer = input("Continue deletion checks anyway? [y/n]: ").strip().lower()
            if answer not in {"y", "yes"}:
                print("Cancelled folder deletion.")
                return False
            is_empty = False
        except OSError as error:
            if not prompt_instead_of_requirement_failure or not sys.stdin.isatty():
                raise
            print()
            print("Folder deletion empty-check warning:")
            print(f"Folder: {target_path}")
            print(
                f"Could not determine whether the folder only contains empty files/folders: {error}"
            )
            print()
            answer = input("Continue deletion checks anyway? [y/n]: ").strip().lower()
            if answer not in {"y", "yes"}:
                print("Cancelled folder deletion.")
                return False
            is_empty = False

        if not is_empty or not allow_empty_without_markers:
            for expected_file in required_included_files:
                expected_path = os.path.join(target_path, expected_file)
                if not os.path.isfile(expected_path):
                    message = f'Required file is missing: "{expected_file}"'
                    if (
                        not prompt_instead_of_requirement_failure
                        or not sys.stdin.isatty()
                    ):
                        raise ValueError(
                            f'Refusing to delete "{target_path}" because {message}'
                        )
                    print()
                    print("Folder deletion requirement warning:")
                    print(f"Folder: {target_path}")
                    print(message)
                    print()
                    answer = input("Delete anyway? [y/n]: ").strip().lower()
                    if answer not in {"y", "yes"}:
                        print("Cancelled folder deletion.")
                        return False

            for expected_dir in required_included_dirs:
                expected_path = os.path.join(target_path, expected_dir)
                if not os.path.isdir(expected_path):
                    message = f'Required directory is missing: "{expected_dir}"'
                    if (
                        not prompt_instead_of_requirement_failure
                        or not sys.stdin.isatty()
                    ):
                        raise ValueError(
                            f'Refusing to delete "{target_path}" because {message}'
                        )
                    print()
                    print("Folder deletion requirement warning:")
                    print(f"Folder: {target_path}")
                    print(message)
                    print()
                    answer = input("Delete anyway? [y/n]: ").strip().lower()
                    if answer not in {"y", "yes"}:
                        print("Cancelled folder deletion.")
                        return False

    if is_below_min_path_depth:
        if not sys.stdin.isatty():
            raise ValueError(
                f'Refusing to delete "{target_path}" with path depth {path_depth} without interactive confirmation. '
                f"Configured minimum depth: {min_path_depth}."
            )

        print()
        print("Folder deletion path depth warning:")
        print(f"Folder: {target_path}")
        print(f"Path depth: {path_depth}")
        print(f"Configured minimum depth: {min_path_depth}")
        print()
        answer = (
            input("Folder path is shallower than expected. Delete anyway? [y/n]: ")
            .strip()
            .lower()
        )
        if answer not in {"y", "yes"}:
            print("Cancelled folder deletion.")
            return False

    if is_above_max_size:
        if folder_size is None or max_size_bytes is None:
            raise RuntimeError(
                f'Could not determine the size limit for "{target_path}".'
            )
        if not sys.stdin.isatty():
            raise ValueError(
                f"Refusing to delete folder larger than {_format_bytes(max_size_bytes)} without interactive confirmation. "
                f"Folder: {target_path}. Folder size: {_format_bytes(folder_size)}"
            )

        print()
        print("Folder deletion size warning:")
        print(f"Folder: {target_path}")
        size_label = "Measured at least" if folder_size_is_partial else "Folder size"
        print(f"{size_label}: {_format_bytes(folder_size)}")
        print(f"Configured limit: {_format_bytes(max_size_bytes)}")
        print()
        answer = (
            input("Folder is larger than expected. Delete anyway? [y/n]: ")
            .strip()
            .lower()
        )
        if answer not in {"y", "yes"}:
            print("Cancelled folder deletion.")
            return False

    if always_prompt_for_confirmation:
        if folder_size is None:
            try:
                folder_size, folder_size_is_partial = _get_folder_size(
                    target_path, timeout_seconds=max_size_check_seconds
                )
            except OSError as error:
                if not prompt_instead_of_requirement_failure or not sys.stdin.isatty():
                    raise
                print()
                print("Folder deletion size check warning:")
                print(f"Folder: {target_path}")
                print(f"Could not determine folder size: {error}")
                print()
                answer = (
                    input("Continue to deletion confirmation? [y/n]: ").strip().lower()
                )
                if answer not in {"y", "yes"}:
                    print("Cancelled folder deletion.")
                    return False
            if folder_size_is_partial:
                if folder_size is None:
                    raise RuntimeError(
                        f'Could not determine a partial folder size for "{target_path}".'
                    )
                if not prompt_instead_of_requirement_failure or not sys.stdin.isatty():
                    raise ValueError(
                        f'Could not finish size check for "{target_path}" within {max_size_check_seconds:g} seconds. '
                        f"Measured at least {_format_bytes(folder_size)}."
                    )
                print()
                print("Folder deletion size check warning:")
                print(f"Folder: {target_path}")
                print(f"Size check timed out after {max_size_check_seconds:g} seconds.")
                print(f"Measured at least: {_format_bytes(folder_size)}")
                print()
                answer = (
                    input("Continue to deletion confirmation? [y/n]: ").strip().lower()
                )
                if answer not in {"y", "yes"}:
                    print("Cancelled folder deletion.")
                    return False
        print()
        print("Folder deletion request:")
        print(f"Folder: {target_path}")
        size_label = "Measured at least" if folder_size_is_partial else "Folder size"
        if folder_size is not None:
            print(f"{size_label}: {_format_bytes(folder_size)}")
        else:
            print("Folder size: unknown")
        print()
        answer = input(prompt_message).strip().lower()
        if answer not in {"y", "yes"}:
            print("Cancelled folder deletion.")
            return False

    if print_on_deletion:
        print(f'[Info] Deleting "{target_path}"')

    import shutil  # lazy import because takes 0.2 s

    shutil.rmtree(target_path)
    if os.path.exists(target_path):
        raise RuntimeError(f'Failed to delete "{target_path}"')
    return True


def set_hidden_in_explorer(paths: list[str], hidden: bool = True):
    """
    Hide or unhide multiple Windows files and folders.

    Args:
        paths: Iterable of file/folder paths.
        hidden: True to hide, False to unhide.

    Returns:
        A dictionary mapping each path to None on success,
        or an exception object on failure.
    """

    import ctypes

    FILE_ATTRIBUTE_HIDDEN = 0x02
    INVALID_FILE_ATTRIBUTES = 0xFFFFFFFF
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.GetFileAttributesW.argtypes = [ctypes.c_wchar_p]
    kernel32.GetFileAttributesW.restype = ctypes.c_uint32
    kernel32.SetFileAttributesW.argtypes = [ctypes.c_wchar_p, ctypes.c_uint32]
    kernel32.SetFileAttributesW.restype = ctypes.c_int

    for path in paths:
        path = os.path.abspath(path)

        attributes = kernel32.GetFileAttributesW(path)

        if attributes == INVALID_FILE_ATTRIBUTES:
            continue

        if hidden:
            new_attributes = attributes | FILE_ATTRIBUTE_HIDDEN
        else:
            new_attributes = attributes & ~FILE_ATTRIBUTE_HIDDEN

        # Avoid an unnecessary filesystem operation.
        if new_attributes == attributes:
            continue

        if not kernel32.SetFileAttributesW(path, new_attributes):
            continue


def get_script_name(with_file_ending: bool = True) -> str:
    """Return the filename of the script that called this helper.

    ``with_file_ending=False`` removes a trailing ``.py`` extension. This is
    intended for standalone-script status and error messages.
    """
    import inspect

    caller_file = inspect.currentframe().f_back.f_globals.get("__file__", "")  # type: ignore[union-attr]
    name = os.path.basename(caller_file) or os.path.basename(sys.argv[0])
    return name if with_file_ending else name.removesuffix(".py")


def find_longest_paths(
    root_dir: str | os.PathLike[str],
    *,
    top_path_count: int = 50,
    excluded_dir_names: Sequence[str] = (),
) -> tuple[list[Path], int, int]:
    """Return the longest paths below *root_dir* and the number of files and directories scanned."""

    import stat

    def _is_reparse_point(path: Path) -> bool:
        """Return whether *path* is a symbolic link or Windows reparse point."""
        try:
            attributes = getattr(
                path.stat(follow_symlinks=False), "st_file_attributes", 0
            )
        except OSError:
            return True
        return path.is_symlink() or bool(
            attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
        )

    if top_path_count < 1:
        raise ValueError("top_path_count must be at least 1.")

    root_path = Path(root_dir).resolve()
    if not root_path.is_dir():
        raise NotADirectoryError(f"Path is not a directory: {root_path}")

    excluded_names = frozenset(excluded_dir_names)
    paths: list[Path] = [root_path]
    scanned_files = 0
    scanned_directories = 0

    for current_directory, directory_names, file_names in os.walk(
        root_path, topdown=True, followlinks=False
    ):
        current_path = Path(current_directory)
        kept_directories: list[str] = []
        for directory_name in directory_names:
            directory_path = current_path / directory_name
            if directory_name in excluded_names or _is_reparse_point(directory_path):
                continue
            kept_directories.append(directory_name)
            scanned_directories += 1
            paths.append(directory_path)
        directory_names[:] = kept_directories

        for file_name in file_names:
            file_path = current_path / file_name
            if _is_reparse_point(file_path):
                continue
            scanned_files += 1
            paths.append(file_path)

    def path_length(path: Path) -> int:
        return len(str(path))

    paths.sort(key=path_length, reverse=True)
    return paths[:top_path_count], scanned_files, scanned_directories


def make_abs_path_relative_to_file(path: str, file: str) -> str:
    """makes a path absolute if relative with respect to the file (as if the file defined it)"""
    if not os.path.isabs(path):
        return os.path.normpath(os.path.dirname(file) + "\\" + path)
    else:
        return path


def sanitize_filename(filename: str, replacement: str = "_") -> str:
    """Sanitize a string so it can be used as a Windows filename."""
    import re

    # 1. Characters illegal in Windows: < > : " / \ | ? *
    # Also handles control characters (0-31)
    illegal_chars = r'[<>:"/\\|?*\x00-\x1f]'
    filename = re.sub(illegal_chars, replacement, filename)
    # 2. Windows reserved filenames (CON, PRN, AUX, NUL, COM1-9, LPT1-9)
    # These cannot be filenames even with an extension (e.g., CON.txt is bad)
    reserved_names = {"CON", "PRN", "AUX", "NUL", "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9", "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9"}  # fmt: skip
    # Check the "stem" (name before the dot)
    base_name = os.path.splitext(filename)[0].upper()
    if base_name in reserved_names:
        filename = f"{replacement}{filename}"
    # 3. Strip trailing dots and spaces (Windows ignores/removes these)
    filename = filename.rstrip(". ")
    # 4. Enforce length limit (255 characters for the filename itself)
    if len(filename) > 255:
        filename = filename[:255]
    # 5. Handle empty strings (if sanitization removed everything)
    return filename if filename else "unnamed_file"


def write_lines(path: str, lines: list[str], override: bool = True) -> None:
    """lines are a list of strings without the endline symbol ("\n") added.
    If override==False it will append instead of recreating the file (default:  override=True)."""

    os.makedirs(os.path.dirname(path), exist_ok=True)

    lines_str = "\n".join(lines) + "\n"

    with open(path, "w" if override else "a", encoding="utf-8") as f:
        f.write(lines_str)


def read_lines(path: str) -> list[str]:
    """returns a list of strings from path without the endline symbol ("\n" or "\r\n")"""

    with open(path, encoding="utf-8") as f:
        lines = f.readlines()  # readlines converts \r\n into \n

    return [line.rstrip("\n") for line in lines]
