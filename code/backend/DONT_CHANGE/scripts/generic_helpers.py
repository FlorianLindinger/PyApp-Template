"""WIP"""

# =========================
# imports

import os
import sys
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any, override

# =========================
# constants

ANSI_WARN: str = "\x1b[1;37;41m"  # white text, red bg, bold
ANSI_SUCCESS: str = "\x1b[1;37;42m"  # white text, green bg, bold
ANSI_RESET: str = "\033[0m"

# =========================
# miscellaneous


def can_reach_url(url: str, timeout_s: float = 5.0) -> bool:
    """Return True if the given URL can be reached."""
    import urllib.request

    try:
        request = urllib.request.Request(  # noqa
            url,
            headers={"User-Agent": "url-reachable-check/1.0"},
        )

        with urllib.request.urlopen(request, timeout=timeout_s):  # noqa
            return True

    except OSError:
        return False


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
# git related


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


def close_terminal(exit_code: Any = None) -> bool:
    """Close the current terminal window when the launcher can safely exit."""
    parent_pid = os.getppid()
    try:
        import ctypes
        from ctypes import wintypes

        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel32.OpenProcess.restype = wintypes.HANDLE
        kernel32.QueryFullProcessImageNameW.argtypes = [
            wintypes.HANDLE,
            wintypes.DWORD,
            wintypes.LPWSTR,
            ctypes.POINTER(wintypes.DWORD),
        ]
        kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel32.CloseHandle.restype = wintypes.BOOL

        process_handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, parent_pid)
        if not process_handle:
            parent_image_path = ""
        try:
            buffer_length = wintypes.DWORD(32768)
            buffer = ctypes.create_unicode_buffer(buffer_length.value)
            if not kernel32.QueryFullProcessImageNameW(process_handle, 0, buffer, ctypes.byref(buffer_length)):
                parent_image_path = ""
            parent_image_path = buffer.value
        finally:
            kernel32.CloseHandle(process_handle)
    except Exception:
        parent_image_path = ""
    parent_name = os.path.basename(parent_image_path).lower()
    if parent_name not in ("cmd.exe", "powershell.exe", "pwsh.exe"):
        return False

    import signal

    os.kill(parent_pid, signal.SIGTERM)

    import sys

    sys.exit(exit_code)


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


def set_terminal_colors(colors: str | None) -> None:
    """colors is in format of windows terminal colors"""
    if colors:
        try:
            import subprocess

            subprocess.run(["cmd.exe", "/c", "color", colors], check=False)  # noqa:S603
        except Exception:
            pass


# =========================
# path related/file name related


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
            attributes = getattr(path.stat(follow_symlinks=False), "st_file_attributes", 0)
        except OSError:
            return True
        return path.is_symlink() or bool(attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))

    if top_path_count < 1:
        raise ValueError("top_path_count must be at least 1.")

    root_path = Path(root_dir).resolve()
    if not root_path.is_dir():
        raise NotADirectoryError(f"Path is not a directory: {root_path}")

    excluded_names = frozenset(excluded_dir_names)
    paths = [root_path]
    scanned_files = 0
    scanned_directories = 0

    for current_directory, directory_names, file_names in os.walk(root_path, topdown=True, followlinks=False):
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

    paths.sort(key=lambda path: len(str(path)), reverse=True)
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


# =========================
# file read/write


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

    return [l.rstrip("\n") for l in lines]


# =========================
# process id related


def is_process_running(pid: int) -> bool:
    if pid <= 0:
        return False

    try:
        import ctypes
        from ctypes import wintypes

        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        STILL_ACTIVE = 259

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel32.OpenProcess.restype = wintypes.HANDLE
        kernel32.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
        kernel32.GetExitCodeProcess.restype = wintypes.BOOL
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel32.CloseHandle.restype = wintypes.BOOL

        process_handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if not process_handle:
            return ctypes.get_last_error() == 5  # ERROR_ACCESS_DENIED means the process still exists.
        try:
            exit_code = wintypes.DWORD()
            if not kernel32.GetExitCodeProcess(process_handle, ctypes.byref(exit_code)):
                return False
            return exit_code.value == STILL_ACTIVE
        finally:
            kernel32.CloseHandle(process_handle)
    except Exception:
        return False


# =========================
# python related


def get_python_version(python_exe: str) -> str:
    import subprocess

    return subprocess.check_output(  # noqa:S603
        [
            python_exe,
            "-c",
            "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')",
        ],
        stderr=subprocess.STDOUT,
        text=True,
    ).strip()


def is_python_version_compatible(actual_version: str, required_version: str) -> bool:
    actual_parts = actual_version.split(".")
    required_parts = required_version.strip().split(".")

    if (len(actual_parts) != 3) or (any(not part.isdigit() for part in actual_parts)):
        raise ValueError(
            f"Could not determine Python version from output: {actual_version}. Expected format like '3.13.2'."
        )

    if not required_parts or any(not part.isdigit() for part in required_parts):
        raise ValueError(
            f"Invalid target_version format: {required_version}. Must be a string like '3', '3.13', or '3.13.2'."
        )

    return actual_parts[: len(required_parts)] == required_parts


# =========================
# Python installer


def install_full_python(
    python_dir_abs_path: str,
    python_version: str = "",
    rel_path_to_packages: str = "",
    install_tkinter: bool = True,
    install_tests: bool = True,
    install_tools: bool = True,
    install_docs: bool = False,
    print_: bool = True,
) -> None:
    r"""
    Create a local full Windows Python installation from python.org MSI files.

    The function finds the newest matching Python version in the form of:

        https://www.python.org/ftp/python/{version}/amd64/<some-file>.msi or
        https://www.python.org/ftp/python/<version>/<some-file>.amd64.msi

    It downloads the selected amd64 MSI packages, extracts them into
    ``python_dir_abs_path``, bootstraps pip through ensurepip or get-pip.py,
    and optionally writes a ``.pth`` file that adds another relative package
    directory to Python's import path if parameter rel_path_to_packages is given.

    Args:
        python_dir_abs_path: Target directory. Existing contents are deleted after a
            valid MSI set is found. Must be absolute path and raises Error otherwise.
        python_version (optional, default ""): Python version filter. Examples: ``""``, ``"3"``,
            ``"3.12"``, ``"3.12.4"``.
        rel_path_to_packages: Optional path relative to being inside ``python_dir_abs_path`` that is
            written into ``Lib/site-packages/path_to_packages.pth``. Default "" -> No path written.
        install_tkinter (optional, default True): Include Tcl/Tk support.
        install_tests (optional, default True): Include the standard library test package.
        install_tools (optional, default True): Include Python tools.
        install_docs (optional, default False): Include documentation.
        print_ (default True): Whether to print info messages

    For lower python versions (3.4-), there is no option to for example not install tkinter. It will ignore the parameter

    Raises:
        RuntimeError: If version discovery, download, extraction, or pip setup
        fails.
    """

    # ---------------------------
    # lazy imports

    import fnmatch
    import html.parser
    import re
    import shutil
    import subprocess
    import tempfile
    import urllib.error
    import urllib.parse
    import urllib.request

    # ---------------------------
    # local variables

    python_file_download_url_patterns = [  # lower index preferred
        "https://www.python.org/ftp/python/{version}/amd64/*.msi",  # python 3.5+ 64bit
        "https://www.python.org/ftp/python/{version}/*.amd64.msi",  # python 3.4- 64bit
    ]
    blacklisted_file_patterns = [
        "appendpath.msi",  # PATH modification helper, skipped because this install uses a local target directory.
        "launcher.msi",  # Global Python launcher component, skipped for this local extracted install.
        "path.msi",  # PATH modification helper, skipped because this install uses a local target directory.
        "pip.msi",  # Pip is installed later through ensurepip or get-pip.py.
        "*_d.msi",  # Debug build MSI, not the normal runtime package.
        "*_pdb.msi",  # Debug symbols MSI, not needed for normal runtime use.
        "*arm64*",  # ARM64 package, skipped because this installer uses the amd64 package directory.
        "*[0-9]rc[0-9]*",  # Release candidate, not a final release.
        "*win32*",  # 32-bit package, skipped because this installer uses the amd64 package directory.
    ]
    if not install_tkinter:
        blacklisted_file_patterns.append("tcltk.msi")  # Tkinter component disabled.
    if not install_tests:
        blacklisted_file_patterns.append("test.msi")  # Test suite component disabled.
    if not install_tools:
        blacklisted_file_patterns.append("tools.msi")  # Tools component disabled.
    if not install_docs:
        blacklisted_file_patterns.append("doc.msi")  # Documentation component disabled.
    python_exe = python_dir_abs_path + "\\python.exe"
    site_packages_dir = python_dir_abs_path + "\\Lib\\site-packages"
    path_to_packages_file = site_packages_dir + "\\_PATH_TO_PACKAGES_.pth"
    ruff_config = python_dir_abs_path + "\\Lib\\test\\.ruff.toml"
    python_download_timeout_s = 120
    user_agent = "install-full-python/1.0"

    # ---------------------------
    # define helper functions

    def _find_python_version_and_download_links() -> tuple[str, str, list[str]]:
        def _get_download_links_from_url(url: str) -> list[str]:
            request = urllib.request.Request(url, headers={"User-Agent": user_agent})  # noqa

            with urllib.request.urlopen(request, timeout=python_download_timeout_s) as response:  # noqa
                html_text = response.read().decode("utf-8", errors="replace")

            class _LinkParser(html.parser.HTMLParser):
                """Extract href values from a simple HTML directory listing."""

                def __init__(self) -> None:
                    super().__init__()
                    self.links: list[str] = []

                @override
                def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
                    """WIP"""
                    if tag.lower() == "a":
                        self.links.extend(value for name, value in attrs if name.lower() == "href" and value)

            parser = _LinkParser()
            parser.feed(html_text)
            return parser.links

        # define key to sort download links: prefer newest version that matches pattern
        def _version_key(version: str) -> tuple[int, int, int]:
            major, minor, patch = version.split(".")
            return int(major), int(minor), int(patch)

        def _find_matching_versions() -> list[str]:
            """Find all matching version folders from the configured download URL patterns."""
            versions = set()
            errors = []
            for url_pattern in python_file_download_url_patterns:
                version_list_url = url_pattern.split("{version}", 1)[0]
                try:
                    versions.update(
                        link.strip("/")
                        for link in _get_download_links_from_url(version_list_url)
                        if target_version_pattern.match(link)
                    )
                except (OSError, urllib.error.URLError) as error:
                    errors.append(error)

            if versions:
                return sorted(versions, key=_version_key, reverse=True)
            if errors:
                raise RuntimeError(
                    f'[Error] Could not find a matching Python MSI set for parameter python_version: "{python_version}".'
                ) from errors[0]
            raise RuntimeError(
                f'[Error] No Python download URL patterns configured for parameter python_version: "{python_version}".'
            )

        def _is_wanted_file(link: str) -> bool:
            """Return whether wanted msi."""
            if link.endswith("/"):  # reject folders
                return False

            filename = os.path.basename(urllib.parse.urlparse(link).path).lower()

            # return False if filename matches any blacklisted pattern
            if any(fnmatch.fnmatchcase(filename.lower(), pattern) for pattern in blacklisted_file_patterns):
                return False

            _base, extension = os.path.splitext(filename)
            if extension == ".msi":
                return True
            else:
                return False

        def _find_msi_urls_from_pattern(url_pattern: str, version: str) -> tuple[str, list[str]]:
            """Find matching MSI URLs from a URL pattern such as .../{version}/amd64/*.msi."""
            resolved_pattern = url_pattern.format(version=version)
            folder_url, filename_pattern = resolved_pattern.rsplit("/", 1)
            folder_url += "/"
            links = _get_download_links_from_url(folder_url)
            msi_urls = []
            for link in links:
                filename = os.path.basename(urllib.parse.urlparse(link).path).lower()
                if fnmatch.fnmatchcase(filename, filename_pattern.lower()) and _is_wanted_file(link):
                    msi_urls.append(urllib.parse.urljoin(folder_url, link))
            return folder_url, sorted(msi_urls)

        if python_version == "":
            target_version_pattern = re.compile(r"^\d+\.\d+\.\d+/$")
        elif re.fullmatch(r"\d+", python_version):
            target_version_pattern = re.compile(rf"^{re.escape(python_version)}\.\d+\.\d+/$")
        elif re.fullmatch(r"\d+\.\d+", python_version):
            target_version_pattern = re.compile(rf"^{re.escape(python_version)}\.\d+/$")
        elif re.fullmatch(r"\d+\.\d+\.\d+", python_version):
            target_version_pattern = re.compile(rf"^{re.escape(python_version)}/$")
        else:
            raise RuntimeError(
                f'[Error] Could not find a matching Python version pattern for parameter python_version: "{python_version}".'
            )

        # sort download links and take first working
        for version in _find_matching_versions():
            for url_pattern in python_file_download_url_patterns:
                try:
                    url, msi_urls = _find_msi_urls_from_pattern(url_pattern, version)
                except (OSError, urllib.error.URLError):
                    continue

                # return found download links and python version
                if msi_urls:
                    return version, url, msi_urls
        else:
            raise RuntimeError(
                f'[Error] Could not find msi-downloadable Python for python_version: "{python_version}".'
            )

    def _download_file_from_url(url: str, folder: str) -> str:
        filename = os.path.basename(urllib.parse.urlparse(url).path)
        output_path = os.path.join(folder, filename)

        if print_:
            print(f"Downloading {filename}")

        request = urllib.request.Request(url, headers={"User-Agent": user_agent})  # noqa

        with urllib.request.urlopen(request, timeout=python_download_timeout_s) as response:  # noqa
            with open(output_path, "wb") as file:
                shutil.copyfileobj(response, file)

        if not os.path.isfile(output_path) or os.path.getsize(output_path) == 0:
            raise RuntimeError(f'Download produced an empty file: "{output_path}"')

        return output_path

    def _install_msi_file(msi_path: str) -> None:
        msi_name = os.path.basename(msi_path)
        log_path = os.path.splitext(msi_path)[0] + ".msi.log"

        if print_:
            print(f"Installing {msi_name}")

        # install msi files in python_dir_abs_path
        command = f'msiexec /a "{msi_path}" TARGETDIR="{python_dir_abs_path}" /qn /L*V "{log_path}"'
        result = subprocess.run(  # noqa
            command,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(f"msiexec failed for {msi_name} with exit code {result.returncode}. Log: {log_path}")

        if msi_name.lower() == "test.msi":
            # needed to prevent Ruff from complaining/failing for ".ruff.toml" files in Pythons "test" package/folder because this local python installation does not follow the global python source-tree layout.-> it comments out lines starting with "extend" in "Lib\test\.ruff.toml", e.g., "extend = "../.ruff.toml"."""
            if os.path.exists(ruff_config):
                lines = read_lines(ruff_config)
                lines = ["# " + line if re.match(r"^\s*extend\s*=", line) else line for line in lines]
                write_lines(ruff_config, lines)

        # Remove any MSI copy that install left in TARGETDIR.
        copied_msi = os.path.join(python_dir_abs_path, msi_name)
        if os.path.exists(copied_msi):
            os.remove(copied_msi)

    def _install_pip(target_version: str) -> None:
        """Bootstrap pip using the best method for the installed Python version."""
        version_match = re.fullmatch(r"(\d+)\.(\d+)(?:\.(\d+))?", target_version)
        if not version_match:
            raise RuntimeError(f'Could not parse Python version "{target_version}".')

        major = int(version_match.group(1))
        minor = int(version_match.group(2))
        patch = int(version_match.group(3) or 0)

        # Python includes ensurepip starting with 3.4 and 2.7.9.
        supports_ensurepip = (
            major > 3 or (major == 3 and minor >= 4) or (major == 2 and (minor > 7 or (minor == 7 and patch >= 9)))
        )
        if supports_ensurepip:
            env = os.environ.copy()
            env["PIP_NO_WARN_SCRIPT_LOCATION"] = "1"  # supress warning that pip is not global
            env["PATH"] = os.pathsep.join(
                [
                    python_dir_abs_path,
                    os.path.join(python_dir_abs_path, "Scripts"),
                    env.get("PATH", ""),
                ]
            )

            result = subprocess.run(  # noqa:S603
                [python_exe, "-m", "ensurepip", "--upgrade"],
                check=False,
                env=env,
            )
            if result.returncode != 0:
                raise RuntimeError("Python installation failed: ensurepip failed.")

            upgrade_args = [
                "-m",
                "pip",
                "install",
                "--upgrade",
                "pip",
                "--ignore-installed",
                "--no-warn-script-location",
            ]

            # One upgrade is normally enough. Repeat a few times only if each upgrade
            # actually changes the installed pip version.
            for _pip_upgrade_attempt in range(5):
                result = subprocess.run(  # noqa
                    [python_exe, "-m", "pip", "--version"],
                    check=False,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                )
                if result.returncode != 0:
                    raise RuntimeError("Python installation failed: pip is not available after ensurepip.")
                pip_version_output = result.stdout.split()
                if len(pip_version_output) < 2 or pip_version_output[0].lower() != "pip":
                    raise RuntimeError(f"Python installation failed: could not parse pip version: {result.stdout}")
                pip_version_before = pip_version_output[1]

                # Try quiet/log-friendly pip upgrade first, then retry without the progress-bar flag.
                result = subprocess.run(  # noqa
                    [python_exe, *upgrade_args, "--progress-bar", "off"],
                    check=False,
                    stderr=subprocess.DEVNULL,
                    env=env,
                )
                # retry pip installation if failed without progress bar (for example if that flag is not there yet in the old pip version)
                if result.returncode != 0:
                    result = subprocess.run([python_exe, *upgrade_args], check=False, env=env)  # noqa
                # raise if failed pip installation
                if result.returncode != 0:
                    raise RuntimeError("Python installation failed: pip upgrade failed.")

                result = subprocess.run(  # noqa
                    [python_exe, "-m", "pip", "--version"],
                    check=False,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                )
                if result.returncode != 0:
                    raise RuntimeError("Python installation failed: pip is not available after upgrade.")
                pip_version_output = result.stdout.split()
                if len(pip_version_output) < 2 or pip_version_output[0].lower() != "pip":
                    raise RuntimeError(f"Python installation failed: could not parse pip version: {result.stdout}")
                pip_version_after = pip_version_output[1]

                if pip_version_after == pip_version_before:
                    break
            else:
                raise RuntimeError("Python installation failed: pip upgrade did not stabilize.")

            return

        # Python 3.3 and older do not have ensurepip. Use PyPA's versioned
        # legacy get-pip.py bootstrapper so pip itself still supports the interpreter.
        if print_:
            print(f"Bootstrapping pip with get-pip.py for Python {target_version}")

        get_pip_urls = [
            f"https://bootstrap.pypa.io/pip/{major}.{minor}/get-pip.py",
            f"https://bootstrap.pypa.io/{major}.{minor}/get-pip.py",
        ]
        errors = []
        env = os.environ.copy()
        env["PIP_NO_WARN_SCRIPT_LOCATION"] = "1"
        env["PATH"] = os.pathsep.join(
            [
                python_dir_abs_path,
                os.path.join(python_dir_abs_path, "Scripts"),
                env.get("PATH", ""),
            ]
        )
        with tempfile.TemporaryDirectory(prefix="tmp_get_pip_") as tmp:
            for get_pip_url in get_pip_urls:
                try:
                    get_pip_path = _download_file_from_url(get_pip_url, tmp)
                    break
                except (OSError, RuntimeError, urllib.error.URLError) as error:
                    errors.append(f"{get_pip_url}: {error}")
            else:
                raise RuntimeError(
                    f"Python installation failed: could not download get-pip.py for Python {target_version}. "
                    f"Tried: {'; '.join(errors)}"
                )

            result = subprocess.run([python_exe, get_pip_path, "--no-warn-script-location"], check=False, env=env)  # noqa

        if result.returncode != 0:
            raise RuntimeError("Python installation failed: get-pip.py failed.")

        # Verify that pip can be imported and run by the installed Python:
        result = subprocess.run([python_exe, "-m", "pip", "--version"], check=False)  # noqa
        if result.returncode != 0:
            raise RuntimeError("Python installation failed: pip is not available after bootstrap.")

    # ----------------------------
    # execute code of function

    if not os.path.isabs(python_dir_abs_path):
        raise RuntimeError(f'Paramter "python_dir_abs_path" must be an absolute path. Got "{python_dir_abs_path}"')

    # find compatible python version and download links
    compatible_full_py_vers, download_url, msi_urls = _find_python_version_and_download_links()

    if print_:
        print(f"Found Python {compatible_full_py_vers} (Target: {python_version}).")
        print(f"Download URL: {download_url}")
        print(f"Found {len(msi_urls)} MSI package(s).")

    # Only delete the target after a valid MSI set has been found.
    try:
        delete_folder_safe(python_dir_abs_path, max_size_GB_before_prompt=1.2)
    except Exception as error:
        raise RuntimeError(f'[Error] Refusing to delete "{python_dir_abs_path}". {error}') from error

    # create folder
    os.makedirs(python_dir_abs_path, exist_ok=True)

    # add gitignore file
    write_lines(
        python_dir_abs_path + "\\.gitignore",
        [
            "# Prevent committing the local Python distribution.",
            "*",
        ],
    )

    # download and install msi files
    try:
        with tempfile.TemporaryDirectory(prefix="tmp_python_installation_files_") as tmp:
            # downlaod into temp folder
            msi_paths = [_download_file_from_url(url, tmp) for url in msi_urls]
            # install
            for msi_path in sorted(msi_paths, key=lambda path: os.path.basename(path).lower()):
                _install_msi_file(msi_path)
    except Exception as error:
        raise RuntimeError(f"Local Python installation failed: {error}") from error

    # check if installation looks successful
    if not os.path.exists(python_exe):
        raise RuntimeError("Python installation failed: python.exe was not created.")

    # create a pip config file to stop it from complaining about not being a globally installed python
    write_lines(
        python_dir_abs_path + "\\pip.ini",
        [
            "[global]",
            "no-warn-script-location = true",
        ],
    )

    # install pip
    _install_pip(compatible_full_py_vers)

    # tell python where to look for third party packages
    if rel_path_to_packages:
        # .pth files work best with forward slashes:
        write_lines(path_to_packages_file, ["../../" + rel_path_to_packages.replace("\\", "/")])

    if print_:
        print()
        print(f'Successfully created local Python {compatible_full_py_vers} at "{python_dir_abs_path}".')
        print()


# =========================
# package related


def install_packages(
    python_exe: str,
    packages: str | list[str] | tuple[str, ...] | None = None,
    requirements_file: str | None = None,
    target: str | None = None,
    upgrade: bool = False,
    no_deps: bool = False,
    no_cache: bool = False,
    use_uv: bool = False,
    install_uv_locally_if_global_not_available: bool = True,
    local_uv_python_exe: str | None = None,
    extra_args: str | list[str] | tuple[str, ...] | None = None,
    disable_pip_version_check: bool = True,
    no_warn_script_location: bool = True,
    uninstall: bool = False,
):
    """Install or uninstall packages with pip, optionally trying uv first.

    ``python_exe`` is the interpreter whose package environment should be
    changed. For normal backend runtime packages this is still the backend
    Python executable, while ``target`` points pip/uv at the separate
    ``backend_packages`` runtime folder. Build/install tools should usually be
    installed without ``target`` so they land in the interpreter environment and
    can be removed again after the targeted runtime install is finished.

    ``packages`` may be one package string or a sequence of package strings.
    ``requirements_file`` may be one requirements file path. At least one of
    those inputs is required. The requirements file is passed to pip/uv with
    ``-r``, so pip/uv handle normal requirement parsing instead of this helper
    trying to parse the file.

    Set ``uninstall=True`` to run uninstall instead of install. Uninstalls are
    confirmed automatically with ``-y`` because these scripts run unattended.
    Install-only options are ignored for uninstall: ``target``, ``upgrade``,
    ``no_deps``, ``no_cache``, ``disable_pip_version_check``, and
    ``no_warn_script_location``.

    pip is the default and final fallback. If ``use_uv`` is true, a globally
    available ``uv`` executable is tried first. If no global uv is found and
    ``install_uv_locally_if_global_not_available`` is true (default), uv is
    installed into ``local_uv_python_exe`` and run as
    ``local_uv_python_exe -m uv``. If ``local_uv_python_exe`` is not given,
    ``python_exe`` is used for local uv as well. The local uv install is kept
    after the package operation; this helper does not uninstall it.

    ``local_uv_python_exe`` is useful when the Python that runs uv should be
    different from the Python being modified. For example, backend Python can
    run ``uv`` while uv installs frontend packages with ``--python`` pointing at
    frontend Python.

    If local uv cannot be installed or the uv command fails, this helper prints
    a warning and retries the same package operation with pip.

    ``extra_args`` are appended last to the selected pip/uv command. Use them
    for uncommon flags only; prefer the named options above for behavior that
    this repo relies on.
    """
    import shutil
    import subprocess

    def _as_list(value: str | list[str] | tuple[str, ...] | None) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            return [value]
        return list(value)

    package_args = _as_list(packages)
    extra_args_list = _as_list(extra_args)
    if not package_args and requirements_file is None:
        raise ValueError("No packages or requirements file was given.")

    local_uv_python_exe = local_uv_python_exe or python_exe

    pip_args = [python_exe, "-m", "pip", "uninstall" if uninstall else "install"]
    if requirements_file is not None:
        pip_args.extend(["-r", requirements_file])
    pip_args.extend(package_args)

    if not uninstall:
        if target is not None:
            pip_args.extend(["--target", target])
        if upgrade:
            pip_args.append("--upgrade")
        if no_deps:
            pip_args.append("--no-deps")
        if no_cache:
            pip_args.append("--no-cache-dir")
        if disable_pip_version_check:
            pip_args.append("--disable-pip-version-check")
        if no_warn_script_location:
            pip_args.append("--no-warn-script-location")
    else:
        pip_args.append("-y")
    pip_args.extend(extra_args_list)

    uv_command: list[str] | None = None
    if use_uv:
        global_uv = shutil.which("uv")
        if global_uv:
            uv_command = [global_uv, "pip", "uninstall" if uninstall else "install", "--python", python_exe]

    if uv_command is None and use_uv and install_uv_locally_if_global_not_available:
        local_uv_command = [
            local_uv_python_exe,
            "-m",
            "uv",
            "pip",
            "uninstall" if uninstall else "install",
            "--python",
            python_exe,
        ]
        try:
            local_uv_probe = subprocess.run(  # noqa:S603
                [local_uv_python_exe, "-m", "uv", "--version"],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            if local_uv_probe.returncode == 0:
                uv_command = local_uv_command
            else:
                uv_install_args = [
                    local_uv_python_exe,
                    "-m",
                    "pip",
                    "install",
                    "uv",
                    "--upgrade",
                    "--disable-pip-version-check",
                    "--no-warn-script-location",
                ]
                if no_cache:
                    uv_install_args.append("--no-cache-dir")
                subprocess.run(uv_install_args, check=True)  # noqa:S603
                uv_command = local_uv_command
        except Exception as error:
            print(f"[Warning] local uv installation failed. Falling back to pip. Error: {error}")

    if uv_command is not None:
        uv_args = [*uv_command]
        if requirements_file is not None:
            uv_args.extend(["-r", requirements_file])
        uv_args.extend(package_args)

        if not uninstall:
            if target is not None:
                uv_args.extend(["--target", target])
            if upgrade:
                uv_args.append("--upgrade")
            if no_deps:
                uv_args.append("--no-deps")
            if no_cache:
                uv_args.append("--no-cache")
            uv_args.extend(["--link-mode", "copy"])
        else:
            uv_args.append("-y")
        uv_args.extend(extra_args_list)

        uv_result = subprocess.run(uv_args, check=False)  # noqa:S603
        if uv_result.returncode == 0:
            return uv_result

        print(f"[Warning] uv package {'uninstall' if uninstall else 'install'} failed. Falling back to pip.")

    return subprocess.run(pip_args, check=True)  # noqa:S603


def get_installed_packages(exe_path: str, with_version: bool = True):
    import subprocess

    result = subprocess.run(  # noqa
        [exe_path, "-m", "pip", "--disable-pip-version-check", "freeze"],
        capture_output=True,
        text=True,
        check=True,
    )
    packages_with_version = result.stdout.strip().splitlines()

    if with_version == True:
        return packages_with_version
    else:
        packages_without_version = []

        for line in packages_with_version:
            line = line.strip()

            if line == "" or line.startswith("#"):
                continue

            for operator in ("===", "==", "~=", ">=", "<=", "!=", ">", "<"):
                if operator in line:
                    packages_without_version.append(line.split(operator, 1)[0].strip())
                    break
            else:
                packages_without_version.append(line)

        return packages_without_version


def save_installed_packages(exe_path: str, output_path: str = "requirements.txt", with_version: bool = True):
    output_path = os.path.abspath(output_path)

    packages = get_installed_packages(with_version=with_version, exe_path=exe_path)

    write_lines(output_path, packages)

    return output_path


def save_requirements_of_folder_noVersion(
    target_folder: str,
    output_path: str,
    excluded_folders: Sequence[str] = (
        "__pycache__",
        ".git",
        ".hg",
        ".svn",
    ),
    print_: bool = True,
) -> bool:
    """Save the pipreqs determined python package requirement without a package version. See save_requirements_of_folder_withVersion for with version.

    Returns success bool"""

    import subprocess

    output_path = os.path.abspath(output_path)

    if os.path.exists(output_path):
        os.remove(output_path)

    try:
        cmd = [
            sys.executable,
            "-m",
            "pipreqs.pipreqs",
            target_folder,  # searched_folder,
            "--force",
            "--savepath",
            output_path,
            "--ignore",
            ",".join(excluded_folders),  # excluded_folders
            "--encoding",
            "utf-8",
            "--mode",
            "no-pin",
            "--no-follow-links",
        ]

        if print_:
            print()
            print("=" * 20)
            print("Start of finding required python packages")
            print("-" * 20)
        subprocess.run(cmd, check=True)  # noqa

        if os.path.exists(output_path):
            if print_:
                print("-" * 20)
                print(f'End of finding required python packages. Result: "{output_path}":\n')
                packages = read_lines(output_path)
                print(*packages, sep="\n")
                print("=" * 20)
                print()

            success = True

        else:
            success = False
            if print_:
                print()
                print_warn("[Error] Failed to auto determine needed packages (see above)")
    except Exception as e:
        if print_:
            print()
            print_warn(f"[Error] Failed to auto determine packages (do you have internet?): {e}")
        success = False

    return success


def save_requirements_of_folder_withVersion(
    target_folder: str,
    output_path: str,
    python_exe: str,
    print_: bool = True,
) -> bool:
    """Save the pipreqs determined python package requirement with a package version. See save_requirements_of_folder_noVersion for wihtout version.

    Returns success bool

    Installation into a fresh temp venv needed to determine package versions. Pipreqs only can determine what packages are needed.

    lazy imports subprocess and tempfile."""

    # lazy imports
    import subprocess
    import tempfile

    output_path = os.path.normpath(os.path.abspath(output_path))

    try:
        with tempfile.TemporaryDirectory(prefix="tmp_venv_to_get_package_version") as tmp:
            temp_requirements = tmp + "\\tmp_package_requirements"
            success = save_requirements_of_folder_noVersion(
                print_=print_, target_folder=target_folder, output_path=temp_requirements
            )
            if success == False:
                return False

            temp_python = tmp + "\\Scripts\\python.exe"

            subprocess.run([python_exe, "-m", "venv", tmp], check=True)  # noqa
            if not os.path.exists(temp_python):
                raise RuntimeError(f'Temporary environment did not create "{temp_python}"')

            subprocess.run(  # noqa
                [
                    temp_python,
                    "-m",
                    "pip",
                    "install",
                    "-r",
                    temp_requirements,
                    "--disable-pip-version-check",
                    "--no-warn-script-location",
                ],
                check=True,
            )

            save_installed_packages(exe_path=temp_python, output_path=output_path, with_version=True)

            return True

    except Exception as e:
        if print_:
            print()
            print_warn(f"[Error] Failed to auto determine packages: {e}")
        return False


# ========================

# =========================
# icon generation


def generate_ico_from_png(
    output_path: str,
    base_png_path: str,
    sub_png_path: str | None = None,
    sub_icon_area_scale_factor: float = 0.35,
    sub_icon_alignment: str = "bottom right",
    override: bool = True,
    icon_sizes: Iterable[int] = (256, 128, 64, 48, 32, 16),
) -> str:
    """Create one multi-resolution ``.ico`` file from a base PNG and optional sub-icon.

    ``sub_icon_alignment`` accepts the nine compass-style positions: ``top
    left``, ``top center``, ``top right``, ``center left``, ``center``,
    ``center right``, ``bottom left``, ``bottom center``, and ``bottom right``.
    Word order is flexible (for example, ``left top``), and ``up``/``down``
    (including the common typo ``donw``) are accepted for ``top``/``bottom``.
    When ``override`` is false, an existing output file is kept unchanged.

    Returns the absolute output path.
    """
    import base64
    import json
    import os
    import struct
    import subprocess
    import zlib
    from urllib.parse import quote

    output_path = os.path.abspath(output_path)
    base_png_path = os.path.abspath(base_png_path)
    sub_png_path = os.path.abspath(sub_png_path) if sub_png_path else None
    if not os.path.isfile(base_png_path):
        raise FileNotFoundError(f'Base PNG does not exist: "{base_png_path}"')
    if sub_png_path is not None and not os.path.isfile(sub_png_path):
        raise FileNotFoundError(f'Sub PNG does not exist: "{sub_png_path}"')
    if not 0 < sub_icon_area_scale_factor <= 1:
        raise ValueError("sub_icon_area_scale_factor must be greater than 0 and at most 1.")
    if not icon_sizes or any(size <= 0 for size in icon_sizes):
        raise ValueError("icon_sizes must contain one or more positive sizes.")

    def _normalize_sub_icon_alignment(value: str) -> str:
        normalized = value.lower().replace("_", " ").replace("-", " ")
        tokens = normalized.split()
        aliases = {
            "up": "top",
            "upper": "top",
            "north": "top",
            "down": "bottom",
            "donw": "bottom",
            "lower": "bottom",
            "south": "bottom",
            "middle": "center",
            "centre": "center",
            "west": "left",
            "east": "right",
        }
        tokens = [aliases.get(token, token) for token in tokens]
        allowed = {"top", "bottom", "left", "right", "center"}
        if not tokens or any(token not in allowed for token in tokens):
            raise ValueError(f"Unsupported sub_icon_alignment: {value!r}")
        horizontal = next((token for token in tokens if token in {"left", "right"}), "center")
        vertical = next((token for token in tokens if token in {"top", "bottom"}), "center")
        if tokens.count("center") > 2 or len(set(tokens)) != len(tokens):
            raise ValueError(f"Unsupported sub_icon_alignment: {value!r}")
        return f"{vertical} {horizontal}"

    sub_icon_alignment = _normalize_sub_icon_alignment(sub_icon_alignment)
    output_folder = os.path.dirname(output_path)
    if output_folder:
        os.makedirs(output_folder, exist_ok=True)
    if os.path.exists(output_path) and not override:
        return output_path

    _POWERSHELL_SCRIPT = r"""
    $ErrorActionPreference = 'Stop'
    Add-Type -AssemblyName PresentationCore
    Add-Type -AssemblyName WindowsBase

    function Get-BgraBitmap([string]$uriText) {
        $bitmap = [System.Windows.Media.Imaging.BitmapImage]::new()
        $bitmap.BeginInit()
        $bitmap.UriSource = [System.Uri]::new($uriText)
        $bitmap.CacheOption = [System.Windows.Media.Imaging.BitmapCacheOption]::OnLoad
        $bitmap.CreateOptions = [System.Windows.Media.Imaging.BitmapCreateOptions]::PreservePixelFormat
        $bitmap.EndInit()

        return [System.Windows.Media.Imaging.FormatConvertedBitmap]::new(
            $bitmap,
            [System.Windows.Media.PixelFormats]::Bgra32,
            $null,
            0
        )
    }

    function Copy-BgraBytes([System.Windows.Media.Imaging.BitmapSource]$bitmap) {
        $stride = $bitmap.PixelWidth * 4
        $bytes = New-Object byte[] ($stride * $bitmap.PixelHeight)
        $bitmap.CopyPixels($bytes, $stride, 0)
        return $bytes
    }

    function Encode-PngBase64([System.Windows.Media.Imaging.BitmapSource]$bitmap) {
        $encoder = [System.Windows.Media.Imaging.PngBitmapEncoder]::new()
        $encoder.Frames.Add([System.Windows.Media.Imaging.BitmapFrame]::Create($bitmap))
        $stream = [System.IO.MemoryStream]::new()
        try {
            $encoder.Save($stream)
            return [Convert]::ToBase64String($stream.ToArray())
        }
        finally {
            $stream.Dispose()
        }
    }

    function Render-SquareIcon([System.Windows.Media.Imaging.BitmapSource]$bitmap, [int]$size) {
        $scale = $size / [double][Math]::Max($bitmap.PixelWidth, $bitmap.PixelHeight)
        $newWidth = [Math]::Max(1, [int][Math]::Round($bitmap.PixelWidth * $scale))
        $newHeight = [Math]::Max(1, [int][Math]::Round($bitmap.PixelHeight * $scale))
        $offsetX = [int](($size - $newWidth) / 2)
        $offsetY = [int](($size - $newHeight) / 2)

        $visual = [System.Windows.Media.DrawingVisual]::new()
        [System.Windows.Media.RenderOptions]::SetBitmapScalingMode(
            $visual,
            [System.Windows.Media.BitmapScalingMode]::HighQuality
        )

        $context = $visual.RenderOpen()
        $context.DrawImage(
            $bitmap,
            [System.Windows.Rect]::new($offsetX, $offsetY, $newWidth, $newHeight)
        )
        $context.Close()

        $rendered = [System.Windows.Media.Imaging.RenderTargetBitmap]::new(
            $size,
            $size,
            96,
            96,
            [System.Windows.Media.PixelFormats]::Pbgra32
        )
        $rendered.Render($visual)

        return [System.Windows.Media.Imaging.FormatConvertedBitmap]::new(
            $rendered,
            [System.Windows.Media.PixelFormats]::Bgra32,
            $null,
            0
        )
    }

    function Compose-Overlay(
        [System.Windows.Media.Imaging.BitmapSource]$baseBitmap,
        [System.Windows.Media.Imaging.BitmapSource]$overlayBitmap,
        [double]$overlayScaleFactor,
        [string]$alignment
    ) {
        # Make the sub-icon occupy the requested fraction of the base icon's area.
        # Scaling each dimension requires the square root of that area ratio.
        $baseArea = [double]$baseBitmap.PixelWidth * $baseBitmap.PixelHeight
        $overlayArea = [double]$overlayBitmap.PixelWidth * $overlayBitmap.PixelHeight
        $scale = [Math]::Sqrt(($baseArea / $overlayArea) * $overlayScaleFactor)
        $overlayWidth = [Math]::Max(1, [int][Math]::Round($overlayBitmap.PixelWidth * $scale))
        $overlayHeight = [Math]::Max(1, [int][Math]::Round($overlayBitmap.PixelHeight * $scale))
        $position = $alignment -split ' '
        $vertical = $position[0]
        $horizontal = $position[1]
        $posX = switch ($horizontal) {
            'left' { 0 }
            'right' { $baseBitmap.PixelWidth - $overlayWidth }
            default { [int](($baseBitmap.PixelWidth - $overlayWidth) / 2) }
        }
        $posY = switch ($vertical) {
            'top' { 0 }
            'bottom' { $baseBitmap.PixelHeight - $overlayHeight }
            default { [int](($baseBitmap.PixelHeight - $overlayHeight) / 2) }
        }

        $visual = [System.Windows.Media.DrawingVisual]::new()
        [System.Windows.Media.RenderOptions]::SetBitmapScalingMode(
            $visual,
            [System.Windows.Media.BitmapScalingMode]::HighQuality
        )

        $context = $visual.RenderOpen()
        $context.DrawImage(
            $baseBitmap,
            [System.Windows.Rect]::new(0, 0, $baseBitmap.PixelWidth, $baseBitmap.PixelHeight)
        )
        $context.DrawImage(
            $overlayBitmap,
            [System.Windows.Rect]::new($posX, $posY, $overlayWidth, $overlayHeight)
        )
        $context.Close()

        $rendered = [System.Windows.Media.Imaging.RenderTargetBitmap]::new(
            $baseBitmap.PixelWidth,
            $baseBitmap.PixelHeight,
            96,
            96,
            [System.Windows.Media.PixelFormats]::Pbgra32
        )
        $rendered.Render($visual)

        return [System.Windows.Media.Imaging.FormatConvertedBitmap]::new(
            $rendered,
            [System.Windows.Media.PixelFormats]::Bgra32,
            $null,
            0
        )
    }

    $operation = $env:ICON_OPERATION
    switch ($operation) {
        'image-id' {
            $bitmap = Get-BgraBitmap $env:ICON_BASE_URI
            [pscustomobject]@{
                width = $bitmap.PixelWidth
                height = $bitmap.PixelHeight
                bgra_base64 = [Convert]::ToBase64String((Copy-BgraBytes $bitmap))
            } | ConvertTo-Json -Compress
            break
        }
        'image-ids' {
            $requests = $env:ICON_IMAGE_ID_REQUESTS | ConvertFrom-Json
            $entries = foreach ($request in $requests) {
                $bitmap = Get-BgraBitmap $request.uri
                [pscustomobject]@{
                    path = $request.path
                    width = $bitmap.PixelWidth
                    height = $bitmap.PixelHeight
                    bgra_base64 = [Convert]::ToBase64String((Copy-BgraBytes $bitmap))
                }
            }

            @($entries) | ConvertTo-Json -Compress
            break
        }    'render-icon' {
            $bitmap = Get-BgraBitmap $env:ICON_BASE_URI
            if ($env:ICON_OVERLAY_URI) {
                $overlayBitmap = Get-BgraBitmap $env:ICON_OVERLAY_URI
                $bitmap = Compose-Overlay $bitmap $overlayBitmap ([double]$env:ICON_SUB_ICON_AREA_SCALE_FACTOR) $env:ICON_SUB_ICON_ALIGNMENT
            }

            $sizes = $env:ICON_SIZES -split ',' | ForEach-Object { [int]$_ }
            $entries = foreach ($size in $sizes) {
                $iconBitmap = Render-SquareIcon $bitmap $size
                [pscustomobject]@{
                    size = $size
                    png_base64 = Encode-PngBase64 $iconBitmap
                }
            }

            @($entries) | ConvertTo-Json -Compress
            break
        }
        'render-icons' {
            $jobs = $env:ICON_RENDER_JOBS | ConvertFrom-Json
            $sizes = $env:ICON_SIZES -split ',' | ForEach-Object { [int]$_ }
            $results = foreach ($job in $jobs) {
                $bitmap = Get-BgraBitmap $job.base_uri
                if ($job.overlay_uri) {
                    $overlayBitmap = Get-BgraBitmap $job.overlay_uri
                    $bitmap = Compose-Overlay $bitmap $overlayBitmap ([double]$job.sub_icon_area_scale_factor) $job.sub_icon_alignment
                }

                $entries = foreach ($size in $sizes) {
                    $iconBitmap = Render-SquareIcon $bitmap $size
                    [pscustomobject]@{
                        size = $size
                        png_base64 = Encode-PngBase64 $iconBitmap
                    }
                }

                [pscustomobject]@{
                    name = $job.name
                    entries = @($entries)
                }
            }

            @($results) | ConvertTo-Json -Compress -Depth 4
            break
        }    default {
            throw "Unsupported ICON_OPERATION: $operation"
        }
    }
    """

    def _run_powershell(**extra_env: str) -> str:
        env = os.environ.copy()
        env.update(extra_env)

        try:
            completed = subprocess.run(  # noqa:S603
                [
                    "powershell.exe",
                    "-NoProfile",
                    "-NonInteractive",
                    "-STA",
                    "-Command",
                    _POWERSHELL_SCRIPT,
                ],
                capture_output=True,
                text=True,
                check=False,
                env=env,
            )
        except FileNotFoundError as exc:
            raise RuntimeError("powershell.exe was not found. This script requires Windows PowerShell.") from exc

        if completed.returncode != 0:
            stderr = completed.stderr.strip() or completed.stdout.strip() or "Unknown PowerShell error."
            raise RuntimeError(stderr)

        return completed.stdout.strip()

    def _path_to_uri(path: str) -> str:
        absolute_path = os.path.abspath(path)
        uri_path = quote(absolute_path.replace("\\", "/"), safe="/:")
        if absolute_path.startswith("\\\\"):
            return f"file:{uri_path}"
        return f"file:///{uri_path}"

    def _bgra_to_rgba(bgra_bytes: bytes) -> bytes:
        rgba = bytearray(len(bgra_bytes))
        rgba[0::4] = bgra_bytes[2::4]
        rgba[1::4] = bgra_bytes[1::4]
        rgba[2::4] = bgra_bytes[0::4]
        rgba[3::4] = bgra_bytes[3::4]
        return bytes(rgba)

    def _load_image_data(path: str) -> tuple[int, int, bytes]:
        payload = json.loads(
            _run_powershell(
                ICON_OPERATION="image-id",
                ICON_BASE_URI=_path_to_uri(path),
            )
        )

        return (
            int(payload["width"]),
            int(payload["height"]),
            base64.b64decode(payload["bgra_base64"]),
        )

    def _load_image_data_batch(paths: list[str]) -> dict[str, tuple[int, int, bytes]]:
        """Load decoded pixels for multiple images in one PowerShell/WPF process."""
        if not paths:
            return {}

        requests = [{"path": path, "uri": _path_to_uri(path)} for path in paths]
        payload = json.loads(
            _run_powershell(
                ICON_OPERATION="image-ids",
                ICON_IMAGE_ID_REQUESTS=json.dumps(requests),
            )
        )
        if isinstance(payload, dict):
            payload = [payload]

        return {
            entry["path"]: (
                int(entry["width"]),
                int(entry["height"]),
                base64.b64decode(entry["bgra_base64"]),
            )
            for entry in payload
        }

    def _image_ids(paths: list[str]) -> dict[str, str]:
        """Return stable image identifiers for multiple paths in one process."""
        image_data = _load_image_data_batch(paths)
        return {
            path: f"{width}x{height}:{zlib.crc32(_bgra_to_rgba(bgra_bytes)) & 0xFFFFFFFF:08x}"
            for path, (width, height, bgra_bytes) in image_data.items()
        }

    def _render_png_layers(
        base_path: str,
        icon_sizes: Iterable[int],
        overlay_path: str | None = None,
        sub_icon_area_scale_factor: float = 0.35,
        sub_icon_alignment: str = "bottom right",
    ) -> list[tuple[int, bytes]]:
        raw_payload = _run_powershell(
            ICON_OPERATION="render-icon",
            ICON_BASE_URI=_path_to_uri(base_path),
            ICON_OVERLAY_URI=_path_to_uri(overlay_path) if overlay_path else "",
            ICON_SUB_ICON_AREA_SCALE_FACTOR=str(sub_icon_area_scale_factor),
            ICON_SUB_ICON_ALIGNMENT=sub_icon_alignment,
            ICON_SIZES=",".join(str(size) for size in icon_sizes),
        )

        payload = json.loads(raw_payload)
        if isinstance(payload, dict):
            payload = [payload]

        return [(int(entry["size"]), base64.b64decode(entry["png_base64"])) for entry in payload]

    def _render_png_layers_batch(
        jobs: list[tuple[str, str, str | None, float]],
        icon_sizes: tuple[int, ...],
    ) -> dict[str, list[tuple[int, bytes]]]:
        """Render multiple icons in one PowerShell/WPF process."""
        if not jobs:
            return {}

        requests = [
            {
                "name": name,
                "base_uri": _path_to_uri(base_path),
                "overlay_uri": _path_to_uri(overlay_path) if overlay_path else "",
                "overlay_scale_factor": overlay_scale_factor,
            }
            for name, base_path, overlay_path, overlay_scale_factor in jobs
        ]
        payload = json.loads(
            _run_powershell(
                ICON_OPERATION="render-icons",
                ICON_RENDER_JOBS=json.dumps(requests),
                ICON_SIZES=",".join(str(size) for size in icon_sizes),
            )
        )
        if isinstance(payload, dict):
            payload = [payload]

        return {
            result["name"]: [(int(entry["size"]), base64.b64decode(entry["png_base64"])) for entry in result["entries"]]
            for result in payload
        }

    def _build_ico(layers: list[tuple[int, bytes]]) -> bytes:
        icon_dir = struct.pack("<HHH", 0, 1, len(layers))
        directory_entries = []
        image_data = bytearray()
        offset = 6 + (16 * len(layers))

        for size, png_bytes in layers:
            directory_entries.append(
                struct.pack(
                    "<BBBBHHII",
                    0 if size >= 256 else size,
                    0 if size >= 256 else size,
                    0,
                    0,
                    1,
                    32,
                    len(png_bytes),
                    offset,
                )
            )
            image_data.extend(png_bytes)
            offset += len(png_bytes)

        return icon_dir + b"".join(directory_entries) + bytes(image_data)

    def create_icon(
        image_path,
        output_path,
        icon_sizes=(256, 128, 64, 48, 32, 16),
        background_color=(0, 0, 0, 0),  # transparent
    ):
        """
        Convert an image into a multi-resolution .ico file with padding
        to preserve aspect ratio (no distortion).

        background_color=(0, 0, 0, 0) means transparent background.
        The parameter is kept for API compatibility with generate_icons.py.
        """

        _ = background_color
        layers = _render_png_layers(image_path, tuple(icon_sizes))
        with open(output_path, "wb") as output_file:
            output_file.write(_build_ico(layers))

    def create_composite_icon(
        base_path,
        overlay_path,
        output_path,
        overlay_scale_factor=0.35,
        icon_sizes=(256, 128, 64, 48, 32, 16),
        background_color=(0, 0, 0, 0),  # transparent padding
    ):
        """
        Create a composite icon:
        - Place overlay on the bottom-right of base.
        - Preserve aspect ratio.
        - Pad to square for each icon size (no distortion).

        background_color=(0, 0, 0, 0) means transparent background.
        The parameter is kept for API compatibility with generate_icons.py.
        """

        _ = background_color
        layers = _render_png_layers(
            base_path,
            tuple(icon_sizes),
            overlay_path=overlay_path,
            sub_icon_area_scale_factor=overlay_scale_factor,
        )
        with open(output_path, "wb") as output_file:
            output_file.write(_build_ico(layers))

    def image_id(path: str) -> str:
        """Return a stable image identifier from dimensions and pixels."""
        width, height, bgra_bytes = _load_image_data(path)
        rgba_bytes = _bgra_to_rgba(bgra_bytes)
        crc = zlib.crc32(rgba_bytes) & 0xFFFFFFFF
        return f"{width}x{height}:{crc:08x}"

    def _pick_icon_path(
        user_path: str,
        fallback_path: str,
        fallback_image_id: str,
        label: str,
        user_image_id: str | None = None,
    ) -> str:
        """Choose the user icon path when available, otherwise the fallback path."""
        if os.path.exists(user_path):
            if (user_image_id if user_image_id is not None else image_id(user_path)) == fallback_image_id:
                print(f"Using fallback {label} icon.")
                return fallback_path
            return user_path

        print(f"Using fallback {label} icon because {os.path.basename(user_path)} is missing.")
        return fallback_path

    def _pause_before_exit() -> None:
        """Pause before exit so console users can read the result."""
        if not sys.stdin.isatty() or not sys.stdout.isatty():
            return

        print()
        input("Press enter to exit.")
        close_terminal()

    layers = _render_png_layers(
        base_png_path,
        icon_sizes,
        overlay_path=sub_png_path,
        sub_icon_area_scale_factor=sub_icon_area_scale_factor,
        sub_icon_alignment=sub_icon_alignment,
    )
    with open(output_path, "wb") as output_file:
        output_file.write(_build_ico(layers))
    return output_path
