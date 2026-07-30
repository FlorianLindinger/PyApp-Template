"""WIP"""

# =========================

import os
import sys
from pathlib import Path
from typing import Any, override

# =========================

ANSI_WARN: str = "\x1b[1;37;41m"  # white text, red bg, bold
ANSI_SUCCESS: str = "\x1b[1;37;42m"  # white text, green bg, bold
ANSI_RESET: str = "\033[0m"

# =========================
# Git helper functions


def git_repository_root() -> Path:
    """Return the Git work tree containing this project."""
    import subprocess

    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=Path(__file__).parent,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "Could not find a Git work tree.")
    return Path(result.stdout.strip())


def run_git(arguments: list[str]) -> int:
    """Run Git in the project repository and return its exit code."""
    import subprocess

    try:
        root = git_repository_root()
    except (FileNotFoundError, RuntimeError) as error:
        print(f"[Error] {error}")
        return 2
    return subprocess.run(["git", *arguments], cwd=root, check=False).returncode  # noqa: S603


def show_git_results(arguments: list[str], *, heading: str, no_results_message: str) -> int:
    """Run a Git listing command and make an empty result explicit."""
    import subprocess

    try:
        root = git_repository_root()
    except (FileNotFoundError, RuntimeError) as error:
        print(f"[Error] {error}")
        return 2

    print(f"[Info] {heading}")
    result = subprocess.run(  # noqa:S603
        ["git", *arguments],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.stdout:
        print(result.stdout, end="" if result.stdout.endswith("\n") else "\n")
    elif result.returncode == 0:
        print(f"[Info] {no_results_message}")
    if result.stderr:
        print(result.stderr, end="" if result.stderr.endswith("\n") else "\n")
    return result.returncode


# =========================


def open_in_editor(path: str) -> None:
    """Open a file preferably in vscode with fallback in Windows notepad. Lazily imports shutil and subprocess."""

    import shutil
    import subprocess

    if not os.path.exists(path):
        print(f"[Error] Could not find file at path: {path}")
        input("Press enter to exit.")
        sys.exit(0)
    vscode_exe_path = shutil.which("code")
    if vscode_exe_path is not None:
        subprocess.Popen([vscode_exe_path, path])  # noqa:S603
    else:
        # Fallback
        subprocess.Popen(["notepad.exe", path])  # noqa:S603


# =========================
# colored print and input and prompt and general print related


def print_warn(msg: Any, sep: str | None = " ", end: str | None = "\n") -> None:
    """Print a warning-styled console message."""
    if msg is not None:
        print(f"{ANSI_WARN}{msg}{ANSI_RESET}", sep=sep, end=end)


def input_warn(msg: str) -> str:
    """Prompt for input using warning console styling."""
    return input(f"{ANSI_WARN}{msg}{ANSI_RESET}")


def input_success(msg: str) -> str:
    """Prompt for input using success console styling."""
    return input(f"{ANSI_SUCCESS}{msg}{ANSI_RESET}")


def print_success(msg: Any, sep: str | None = " ", end: str | None = "\n") -> None:
    """Print a success-styled console message."""
    if msg is not None:
        print(f"{ANSI_SUCCESS}{msg}{ANSI_RESET}", sep=sep, end=end)


# =========================
# folder deletion function


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

    def _validate_required_child_names(names: list[str] | tuple[str, ...], label: str) -> tuple[str, ...]:
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
                raise ValueError(f'Required {label} marker must be a direct child name: "{name_text}"')
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

    def _get_folder_size(folder: str | os.PathLike[str], timeout_seconds: float | None = None) -> tuple[int, bool]:
        total = 0
        deadline = None
        get_time = None
        if timeout_seconds is not None:
            if timeout_seconds <= 0:
                raise ValueError(f"Folder scan timeout must be greater than zero: {timeout_seconds}")
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
            raise ValueError(f'Allowed base path must be absolute: "{allowed_base_text}"')
    elif require_direct_child_of_allowed_base:
        raise ValueError("Cannot require direct child of allowed base when no allowed base path is configured.")

    if required_included_files is None:
        required_included_files = ()
    if required_included_dirs is None:
        required_included_dirs = ()
    required_included_files = _validate_required_child_names(required_included_files, "file")
    required_included_dirs = _validate_required_child_names(required_included_dirs, "directory")

    if max_size_GB_before_prompt is not None and max_size_GB_before_prompt < 0:
        raise ValueError(f"Maximum folder size must be zero or greater: {max_size_GB_before_prompt}")
    if max_size_check_seconds is not None and max_size_check_seconds <= 0:
        raise ValueError(f"Folder scan timeout must be greater than zero: {max_size_check_seconds}")

    if _is_symlink_or_junction(folder_path_text):
        raise ValueError(f'Refusing to delete symlink or junction path: "{folder_path_text}"')
    if allowed_base_text is not None and _is_symlink_or_junction(allowed_base_text):
        raise ValueError(f'Allowed base path may not be a symlink or junction: "{allowed_base_text}"')

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
            raise ValueError(f"Refusing to delete the allowed base directory itself: {target_path}")

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

        if require_direct_child_of_allowed_base and os.path.normcase(os.path.dirname(target_path)) != os.path.normcase(
            base_path
        ):
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
            raise ValueError(f"Minimum path depth must be zero or greater: {min_path_depth}")
        _drive, path_without_drive = os.path.splitdrive(os.path.normpath(target_path))
        path_without_root = path_without_drive.strip("\\/")
        path_depth = len([part for part in path_without_root.replace("\\", "/").split("/") if part])
        is_below_min_path_depth = path_depth < min_path_depth

    if expected_folder_name is not None and os.path.basename(target_path).lower() != expected_folder_name.lower():
        raise RuntimeError(
            f'Refusing to delete "{target_path}" because its folder name is not "{expected_folder_name}".'
        )

    if not os.path.isdir(target_path):
        raise NotADirectoryError(f"Target is not a directory: {target_path}")

    if always_prompt_for_confirmation and not sys.stdin.isatty():
        raise ValueError(f'Refusing to delete "{target_path}" without interactive confirmation.')

    folder_size: float | None = None
    folder_size_is_partial = False
    is_above_max_size = False
    max_size_bytes: int | None = None
    if max_size_GB_before_prompt is not None:
        try:
            folder_size, folder_size_is_partial = _get_folder_size(target_path, timeout_seconds=max_size_check_seconds)
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
                raise RuntimeError(f'Could not determine a partial folder size for "{target_path}".')
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
            print(f"Empty-folder check timed out after {max_size_check_seconds:g} seconds.")
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
            print(f"Could not determine whether the folder only contains empty files/folders: {error}")
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
                    if not prompt_instead_of_requirement_failure or not sys.stdin.isatty():
                        raise ValueError(f'Refusing to delete "{target_path}" because {message}')
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
                    if not prompt_instead_of_requirement_failure or not sys.stdin.isatty():
                        raise ValueError(f'Refusing to delete "{target_path}" because {message}')
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
        answer = input("Folder path is shallower than expected. Delete anyway? [y/n]: ").strip().lower()
        if answer not in {"y", "yes"}:
            print("Cancelled folder deletion.")
            return False

    if is_above_max_size:
        if folder_size is None or max_size_bytes is None:
            raise RuntimeError(f'Could not determine the size limit for "{target_path}".')
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
        answer = input("Folder is larger than expected. Delete anyway? [y/n]: ").strip().lower()
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
                answer = input("Continue to deletion confirmation? [y/n]: ").strip().lower()
                if answer not in {"y", "yes"}:
                    print("Cancelled folder deletion.")
                    return False
            if folder_size_is_partial:
                if folder_size is None:
                    raise RuntimeError(f'Could not determine a partial folder size for "{target_path}".')
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
                answer = input("Continue to deletion confirmation? [y/n]: ").strip().lower()
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


# =========================
# terminal related

def get_terminal_title() -> str:
    """Returns "" if it fails to get the title."""

    import ctypes

    try:
        buffer = ctypes.create_unicode_buffer(1024)
        ctypes.windll.kernel32.GetConsoleTitleW(buffer, len(buffer))
        return str(buffer.value)
    except Exception:
        return ""

def set_terminal_title(title: str | None) -> None:
    if title is None:
        return

    try:
        import ctypes

        clean_name = title.replace("\r\n", "").replace("\r", "")
        ctypes.windll.kernel32.SetConsoleTitleW(clean_name)
    except Exception:
        pass

def set_terminal_icon(icon_path: str | None) -> None:
    """Best-effort icon update of the current Windows terminal icon"""
    if icon_path in ("", None):
        return
    else:
        icon_path = os.path.normpath(icon_path)

    import ctypes
    from ctypes import wintypes

    try:
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)  # type:ignore
        hwnd = int(kernel32.GetConsoleWindow() or 0)
        if not hwnd:
            return

        user32 = ctypes.WinDLL("user32", use_last_error=True)

        user32.GetSystemMetrics.argtypes = [ctypes.c_int]
        user32.GetSystemMetrics.restype = ctypes.c_int
        user32.LoadImageW.argtypes = [
            wintypes.HINSTANCE,
            wintypes.LPCWSTR,
            ctypes.c_uint,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_uint,
        ]
        user32.LoadImageW.restype = wintypes.HANDLE
        user32.SendMessageW.argtypes = [wintypes.HWND, ctypes.c_uint, ctypes.c_size_t, ctypes.c_size_t]
        user32.SendMessageW.restype = ctypes.c_size_t
        user32.SetWindowPos.argtypes = [
            wintypes.HWND,
            wintypes.HWND,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_uint,
        ]
        user32.SetWindowPos.restype = wintypes.BOOL

        WM_SETICON = 0x0080
        ICON_SMALL = 0
        ICON_BIG = 1
        IMAGE_ICON = 1
        LR_LOADFROMFILE = 0x0010
        LR_DEFAULTSIZE = 0x0040
        SM_CXSMICON = 49
        SM_CYSMICON = 50
        SM_CXICON = 11
        SM_CYICON = 12
        SWP_NOMOVE = 0x0002
        SWP_NOSIZE = 0x0001
        SWP_NOZORDER = 0x0004
        SWP_NOACTIVATE = 0x0010
        SWP_FRAMECHANGED = 0x0020

        def _load_icon(width: int, height: int) -> int:
            icon = user32.LoadImageW(None, icon_path, IMAGE_ICON, width, height, LR_LOADFROMFILE)
            if not icon:
                icon = user32.LoadImageW(None, icon_path, IMAGE_ICON, 0, 0, LR_LOADFROMFILE | LR_DEFAULTSIZE)
            return int(icon or 0)

        small_icon = _load_icon(
            user32.GetSystemMetrics(SM_CXSMICON),
            user32.GetSystemMetrics(SM_CYSMICON),
        )
        large_icon = _load_icon(
            user32.GetSystemMetrics(SM_CXICON),
            user32.GetSystemMetrics(SM_CYICON),
        )
        if small_icon == 0 and large_icon == 0:
            return

        if small_icon:
            user32.SendMessageW(hwnd, WM_SETICON, ICON_SMALL, small_icon)
        if large_icon:
            user32.SendMessageW(hwnd, WM_SETICON, ICON_BIG, large_icon)
        user32.SetWindowPos(
            hwnd,
            None,
            0,
            0,
            0,
            0,
            SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_NOACTIVATE | SWP_FRAMECHANGED,
        )

    except Exception:
        pass


def set_terminal_app_id(app_id: str) -> None:
    """Try to set System.AppUserModel.ID on the terminal window itself."""

    if not app_id:
        return

    import ctypes
    import uuid
    from ctypes import wintypes

    HRESULT = ctypes.c_long
    VT_LPWSTR = 31
    S_OK = 0
    S_FALSE = 1
    RPC_E_CHANGED_MODE = 0x80010106

    def _helper_refresh_nonclient_area(hwnd: int) -> None:
        """Run the helper refresh nonclient area step."""
        user32_DLL = ctypes.WinDLL("user32", use_last_error=True)

        SWP_NOMOVE = 0x0002
        SWP_NOSIZE = 0x0001
        SWP_NOZORDER = 0x0004
        SWP_NOACTIVATE = 0x0010
        SWP_FRAMECHANGED = 0x0020

        user32_DLL.SetWindowPos(
            hwnd,
            None,
            0,
            0,
            0,
            0,
            SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_NOACTIVATE | SWP_FRAMECHANGED,
        )

    class _GUID(ctypes.Structure):
        """Represent a Windows GUID/UUID structure used by COM APIs."""

        _fields_ = (
            ("Data1", ctypes.c_ulong),
            ("Data2", ctypes.c_ushort),
            ("Data3", ctypes.c_ushort),
            ("Data4", ctypes.c_ubyte * 8),
        )

    class _PROPERTYKEY(ctypes.Structure):
        """WIP"""

        _fields_ = (("fmtid", _GUID), ("pid", wintypes.DWORD))

    class _PROPVARIANT(ctypes.Structure):
        """WIP"""

        _fields_ = (
            ("vt", ctypes.c_ushort),
            ("wReserved1", ctypes.c_ushort),
            ("wReserved2", ctypes.c_ushort),
            ("wReserved3", ctypes.c_ushort),
            ("pwszVal", ctypes.c_wchar_p),
        )

    class _IPropertyStore(ctypes.Structure):
        """WIP"""

    IPropertyStorePtr = ctypes.POINTER(_IPropertyStore)

    class _IPropertyStoreVtbl(ctypes.Structure):
        """WIP"""

        _fields_ = (
            (
                "QueryInterface",
                ctypes.WINFUNCTYPE(
                    HRESULT,
                    IPropertyStorePtr,
                    ctypes.POINTER(_GUID),
                    ctypes.POINTER(ctypes.c_void_p),
                ),
            ),
            ("AddRef", ctypes.WINFUNCTYPE(ctypes.c_ulong, IPropertyStorePtr)),
            ("Release", ctypes.WINFUNCTYPE(ctypes.c_ulong, IPropertyStorePtr)),
            ("GetCount", ctypes.WINFUNCTYPE(HRESULT, IPropertyStorePtr, ctypes.POINTER(wintypes.DWORD))),
            (
                "GetAt",
                ctypes.WINFUNCTYPE(
                    HRESULT,
                    IPropertyStorePtr,
                    wintypes.DWORD,
                    ctypes.POINTER(_PROPERTYKEY),
                ),
            ),
            (
                "GetValue",
                ctypes.WINFUNCTYPE(
                    HRESULT,
                    IPropertyStorePtr,
                    ctypes.POINTER(_PROPERTYKEY),
                    ctypes.POINTER(_PROPVARIANT),
                ),
            ),
            (
                "SetValue",
                ctypes.WINFUNCTYPE(
                    HRESULT,
                    IPropertyStorePtr,
                    ctypes.POINTER(_PROPERTYKEY),
                    ctypes.POINTER(_PROPVARIANT),
                ),
            ),
            ("Commit", ctypes.WINFUNCTYPE(HRESULT, IPropertyStorePtr)),
        )

    _IPropertyStore._fields_ = [("lpVtbl", ctypes.POINTER(_IPropertyStoreVtbl))]

    def _make_guid(value: str) -> _GUID:
        """Build and return the guid."""
        parsed = uuid.UUID(value)
        return _GUID(
            parsed.time_low,
            parsed.time_mid,
            parsed.time_hi_version,
            (ctypes.c_ubyte * 8)(*parsed.bytes[8:]),
        )

    def _format_hresult(hr: int) -> str:
        code = hr & 0xFFFFFFFF
        try:
            message = ctypes.FormatError(code).strip()
        except Exception:
            message = "unknown error"
        return f"0x{code:08X}: {message}"

    def _check_hresult(hr: int, action: str) -> None:
        if hr < 0:
            raise OSError(f"{action} failed with HRESULT {_format_hresult(hr)}")

    try:
        hwnd = int(ctypes.windll.kernel32.GetConsoleWindow() or 0)
        if not hwnd:
            return

        shell32 = ctypes.WinDLL("shell32", use_last_error=True)
        ole32 = ctypes.WinDLL("ole32", use_last_error=True)

        shell32.SHGetPropertyStoreForWindow.argtypes = [
            wintypes.HWND,
            ctypes.POINTER(_GUID),
            ctypes.POINTER(IPropertyStorePtr),
        ]
        shell32.SHGetPropertyStoreForWindow.restype = HRESULT

        ole32.CoInitialize.argtypes = [ctypes.c_void_p]
        ole32.CoInitialize.restype = HRESULT
        ole32.CoUninitialize.argtypes = []
        ole32.CoUninitialize.restype = None

        iid_property_store = _make_guid("886D8EEB-8CF2-4446-8D02-CDBA1DBDCF99")
        pkey_app_user_model_id = _PROPERTYKEY(
            _make_guid("9F4C2855-9F79-4B39-A8D0-E1D42DE1D5F3"),
            5,
        )
        prop_var = _PROPVARIANT()
        prop_var.vt = VT_LPWSTR
        prop_var.pwszVal = app_id

        coinitialize_result = ole32.CoInitialize(None)
        should_uninitialize = coinitialize_result in {S_OK, S_FALSE}
        if coinitialize_result < 0 and (coinitialize_result & 0xFFFFFFFF) != RPC_E_CHANGED_MODE:
            raise OSError(f"CoInitialize failed with HRESULT {_format_hresult(coinitialize_result)}")

        try:
            property_store = IPropertyStorePtr()
            hr = shell32.SHGetPropertyStoreForWindow(
                wintypes.HWND(hwnd),
                ctypes.byref(iid_property_store),
                ctypes.byref(property_store),
            )
            _check_hresult(hr, f"SHGetPropertyStoreForWindow for hwnd 0x{hwnd:016X}")

            try:
                hr = property_store.contents.lpVtbl.contents.SetValue(
                    property_store,
                    ctypes.byref(pkey_app_user_model_id),
                    ctypes.byref(prop_var),
                )
                _check_hresult(hr, f"SetValue System.AppUserModel.ID for hwnd 0x{hwnd:016X}")

                hr = property_store.contents.lpVtbl.contents.Commit(property_store)
                _check_hresult(hr, f"Commit System.AppUserModel.ID for hwnd 0x{hwnd:016X}")

                _helper_refresh_nonclient_area(hwnd)
            finally:
                if property_store:
                    property_store.contents.lpVtbl.contents.Release(property_store)
        finally:
            if should_uninitialize:
                ole32.CoUninitialize()
    except Exception:
        pass


def unminimize_terminal() -> None:
    try:
        import ctypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        hwnd = int(kernel32.GetConsoleWindow() or 0)
        if not hwnd:
            return
        ctypes.windll.user32.ShowWindow(hwnd, 9)  # 9 means unminimized
    except Exception:
        pass

def foreground_terminal() -> None:
    try:
        import ctypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        hwnd = int(kernel32.GetConsoleWindow() or 0)
        if not hwnd:
            return
        ctypes.windll.user32.SetForegroundWindow(hwnd)
    except Exception:
        pass

def enable_unminimize_and_foreground_terminal_on_first_print() -> None:
    
    class unminimize_plus_foreground_terminal_on_first_output:
        """Unminimize a minimized terminal and set to foreground when output is written for the first time."""

        def __init__(self, stream):
            self.stream = stream
            self._restored = False

        def _restore_if_needed(self, data: object) -> None:
            if self._restored or data in ("", b""):
                return
            self._restored = True
            unminimize_terminal()
            foreground_terminal()

        def write(self, data):
            """Write text to the wrapped stream or terminal target."""
            self._restore_if_needed(data)
            return self.stream.write(data)

        def flush(self) -> None:
            """Flush the wrapped stream when supported."""
            if hasattr(self.stream, "flush"):
                self.stream.flush()

        def isatty(self) -> bool:
            """Return whether the wrapped stream behaves like a terminal."""
            return bool(getattr(self.stream, "isatty", lambda: False)())

        def writable(self) -> bool:
            """Return whether the wrapped stream accepts writes."""
            return True

        def fileno(self) -> int:
            """Return the wrapped stream file descriptor."""
            if hasattr(self.stream, "fileno"):
                return self.stream.fileno()
            raise OSError("Underlying stream does not support fileno()")

        def __getattr__(self, name: str):
            """Forward unknown attribute lookups to the wrapped stream."""
            return getattr(self.stream, name)

    # this will unminimize and foreground on first print/error
    sys.stdout = unminimize_plus_foreground_terminal_on_first_output(sys.stdout)  # type:ignore
    sys.stderr = unminimize_plus_foreground_terminal_on_first_output(sys.stderr)  # type:ignore


def set_terminal_colors(colors: str | None = TERMINAL_COLORS) -> None:
    """colors is in format of windows terminal colors"""
    if colors:
        try:
            import subprocess

            subprocess.run(["cmd.exe", "/c", "color", colors], check=False)  # noqa:S603
        except Exception:
            pass
