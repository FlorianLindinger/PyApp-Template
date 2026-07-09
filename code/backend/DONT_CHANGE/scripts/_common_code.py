"""Shared code in scripts that are run in Python backend of this PyApp-Template

Code here should raise an error instead of handling terminal closing or press-enter-to-exit logic.
Imports are mostly lazy because it is not clear what will be needed
"""

# =========================

import os
import sys

# =========================
# add root dir for debug cases where this script is called on its own:
root_dir = os.path.dirname(__file__) + "\\..\\..\\.."
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)
# =========================

from backend.developer_settings import (
    install_tests,
    install_tkinter,
    install_tools,
    program_name,
    python_version,
    terminal_bg_color,
    terminal_text_color,
    use_uv_to_install_packages,
)
from backend.DONT_CHANGE.scripts._common_variables import (
    EMPTY_ARG_INDICATOR,
    backend_python_exe,
    default_packages_file_path,
    determined_current_packages_file_path_noVersion,
    determined_current_packages_file_path_withVersion,
    determined_needed_packages_output_file_path_noVersion,
    determined_needed_packages_output_file_path_withVersion,
    dev_tools_referal_note_path,
    excluded_folders_for_package_search,
    frontend_launcher_for_pip_install_terminal,
    frontend_packages_are_installed_marker_path,
    frontend_packages_dir,
    frontend_python_dir,
    frontend_python_exe,
    icon_path,
    python_scripts_dir,
    python_version_indicator_file_path,
    variable_in_default_packages_path_that_triggers_search_if_true,
)

# =========================
# global variables

_TERMINAL_APPEARANCE_WAS_SET = False

_ANSI_WARN = "\x1b[1;37;41m"  # white text, red bg, bold
_ANSI_SUCCESS = "\x1b[1;37;42m"  # white text, green bg, bold
_ANSI_RESET = "\033[0m"


TERMINAL_COLORS = ""
if terminal_bg_color:
    TERMINAL_COLORS += terminal_bg_color
if terminal_text_color:
    TERMINAL_COLORS += terminal_text_color

# =========================
# general helper functions


def make_empty_args_safe(args: list[str | None]) -> list[str]:
    """Needed because passing empty args as "" in Windows can be flimsy -> replace "" with EMPTY_ARG_INDICATOR and decode in child.

    None get conveted to EMPTY_ARG_INDICATOR as well."""
    return [a if a not in ("", None) else EMPTY_ARG_INDICATOR for a in args]


# =========================
# colored print and input and general print related


def print_success(msg, sep: str | None = " ", end: str | None = "\n"):
    """Print a success-styled console message."""
    print(f"{_ANSI_SUCCESS}{msg}{_ANSI_RESET}", sep=sep, end=end)


def print_warn(msg, sep: str | None = " ", end: str | None = "\n"):
    """Print a warning-styled console message."""
    print(f"{_ANSI_WARN}{msg}{_ANSI_RESET}", sep=sep, end=end)


def input_warn(msg):
    """Prompt for input using warning console styling."""
    return input(f"{_ANSI_WARN}{msg}{_ANSI_RESET}")


def input_success(msg):
    """Prompt for input using success console styling."""
    return input(f"{_ANSI_SUCCESS}{msg}{_ANSI_RESET}")


def print_traceback(message: str = "") -> None:
    """colored traceback via "rich" package. Does not print newlines after traceback but 2 before."""

    from rich.console import Console
    from rich.traceback import Traceback

    console = Console()

    exc_type, exc_value, traceback_ = sys.exc_info()

    print()
    print()
    print_warn("=" * 30)

    if message:
        print_warn(message)
        print("-" * 30)

    console.print(Traceback.from_exception(exc_type, exc_value, traceback_, show_locals=False))  # type:ignore

    print_warn("=" * 30)


# =========================
# folder deletion function


def delete_folder_safe(
    folder_abs_path: str | os.PathLike[str],
    *,
    prompt_message="Delete this folder? (confirm that it is not an important one) [y/n]: ",
    allowed_base_abs_path: str | os.PathLike[str] | None = None,
    expected_folder_name: str | None = None,
    required_included_files: list[str] | tuple[str, ...] | None = (),
    required_included_dirs: list[str] | tuple[str, ...] | None = (),
    allow_empty_without_markers=True,
    require_direct_child_of_allowed_base=False,
    allow_filesystem_root_base=False,
    min_path_depth: int | None = 4,
    max_size_GB_before_prompt: float | None = 1.0,
    max_size_check_seconds: float | None = 5.0,
    prompt_instead_of_requirement_failure=True,
    always_prompt_for_confirmation=False,
    print_on_deletion=False,
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

    def _format_bytes(num_bytes) -> str:
        """Format bytes to for example kB and GB."""
        units = ["B", "KB", "MB", "GB", "TB"]
        size = float(num_bytes)
        for unit in units:
            if size < 1024 or unit == units[-1]:
                if unit == "B":
                    return f"{int(size)} {unit}"
                else:
                    return f"{size:.2f} {unit}"
            size /= 1024
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

    folder_size: int | None = None
    folder_size_is_partial = False
    is_above_max_size = False
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
        if not sys.stdin.isatty():
            raise ValueError(
                f"Refusing to delete folder larger than {_format_bytes(max_size_bytes)} without interactive confirmation. "  # type:ignore
                f"Folder: {target_path}. Folder size: {_format_bytes(folder_size)}"
            )

        print()
        print("Folder deletion size warning:")
        print(f"Folder: {target_path}")
        size_label = "Measured at least" if folder_size_is_partial else "Folder size"
        print(f"{size_label}: {_format_bytes(folder_size)}")
        print(f"Configured limit: {_format_bytes(max_size_bytes)}")  # type:ignore
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


def setup_unminimize_and_foreground_on_first_print():
    # this will unminimize and foreground on first print/error
    sys.stdout = unminimize_plus_foreground_terminal_on_first_output(sys.stdout)  # type:ignore
    sys.stderr = unminimize_plus_foreground_terminal_on_first_output(sys.stderr)  # type:ignore


def set_terminal_colors():
    """set terminal text and bg colors to TERMINAL_COLORS"""
    if TERMINAL_COLORS:
        try:
            import subprocess

            subprocess.run(["cmd.exe", "/c", "color", TERMINAL_COLORS], check=False)  # noqa:S603
        except Exception:
            pass


def get_candidate_hwnds() -> list[int]:
    """Return the candidate hwnds (handle to a Window in the Windows API).
    Needed to modify the current terminal."""
    import ctypes

    kernel32_DLL = ctypes.WinDLL("kernel32", use_last_error=True)  # type:ignore
    user32_DLL = ctypes.WinDLL("user32", use_last_error=True)

    candidate_hwnds: list[int] = []
    console_hwnd = int(kernel32_DLL.GetConsoleWindow() or 0)

    # get console title
    buffer = ctypes.create_unicode_buffer(1024)
    title_length = kernel32_DLL.GetConsoleTitleW(buffer, len(buffer))
    if title_length == 0:
        console_title = ""
    else:
        console_title = buffer.value

    def _add(hwnd: int) -> None:
        if hwnd == 0 or not user32_DLL.IsWindow(hwnd) or hwnd in candidate_hwnds:
            return
        candidate_hwnds.append(hwnd)

    def _get_root_owner(hwnd: int) -> int:
        GA_ROOTOWNER = 3
        if hwnd == 0:
            return 0
        return int(user32_DLL.GetAncestor(hwnd, GA_ROOTOWNER) or 0)

    _add(console_hwnd)
    _add(_get_root_owner(console_hwnd))

    if console_title:
        hwnd_by_console_class = int(user32_DLL.FindWindowW("ConsoleWindowClass", console_title) or 0)
        _add(hwnd_by_console_class)
        _add(_get_root_owner(hwnd_by_console_class))

        hwnd_by_title = int(user32_DLL.FindWindowW(None, console_title) or 0)
        _add(hwnd_by_title)
        _add(_get_root_owner(hwnd_by_title))

    return candidate_hwnds


class unminimize_plus_foreground_terminal_on_first_output:
    """Unminimize a minimized terminal and set to foreground when output is written for the first time."""

    def __init__(self, stream):
        self.stream = stream
        self._restored = False

    def _restore_if_needed(self, data: object) -> None:
        if self._restored or data in ("", b""):
            return
        self._restored = True
        unminimize_and_foreground_terminal()

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


def unminimize_and_foreground_terminal(candidate_hwnds: list[int] | None = None):
    if candidate_hwnds is None:
        candidate_hwnds = get_candidate_hwnds()

    unminimize_window(candidate_hwnds)
    foreground_window(candidate_hwnds)


def foreground_window(candidate_hwnds: list[int] | None = None):
    if candidate_hwnds is None:
        candidate_hwnds = get_candidate_hwnds()

    if candidate_hwnds:
        import ctypes

        for hwnd in candidate_hwnds:
            try:
                ctypes.windll.user32.SetForegroundWindow(hwnd)
            except Exception:
                pass


def unminimize_window(candidate_hwnds: list[int] | None = None):
    if candidate_hwnds is None:
        candidate_hwnds = get_candidate_hwnds()

    if candidate_hwnds:
        import ctypes

        for hwnd in candidate_hwnds:
            try:
                ctypes.windll.user32.ShowWindow(hwnd, 9)  # 9 means unminimized
            except Exception:
                pass


def set_terminal_app_id(app_id: str, candidate_hwnds: list[int]) -> None:
    """Try to set System.AppUserModel.ID on the terminal window itself."""

    if app_id == "":
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
        for hwnd in candidate_hwnds:
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
            except Exception as error:
                print(f"[Info] AppID update skipped for hwnd 0x{hwnd:016X}: {error}")
    finally:
        if should_uninitialize:
            ole32.CoUninitialize()


def set_terminal_icon(icon_path: str, candidate_hwnds=list[int]) -> None:
    """Best-effort icon update of the current Windows terminal icon"""
    if icon_path == "":
        return
    else:
        icon_path = os.path.normpath(icon_path)

    try:
        import ctypes
        from ctypes import wintypes

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

        for hwnd in candidate_hwnds:
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


def set_terminal_title(title: str) -> None:
    try:
        import ctypes

        clean_name = title.replace("\r\n", "").replace("\r", "")
        ctypes.windll.kernel32.SetConsoleTitleW(clean_name)
    except Exception:
        pass


def get_terminal_title() -> str:
    """Returns "" if it fails to get the title."""

    import ctypes

    try:
        buffer = ctypes.create_unicode_buffer(1024)
        ctypes.windll.kernel32.GetConsoleTitleW(buffer, len(buffer))
        return str(buffer.value)
    except Exception:
        return ""


def set_terminal_appearance_once(app_id: str):
    """Apply terminal title, AppID, and icon once per process."""
    global _TERMINAL_APPEARANCE_WAS_SET

    if not _TERMINAL_APPEARANCE_WAS_SET:
        candidate_hwnds = get_candidate_hwnds()

        set_terminal_title(program_name)
        set_terminal_icon(icon_path, candidate_hwnds)

        if app_id:
            set_terminal_app_id(app_id, candidate_hwnds)

        _TERMINAL_APPEARANCE_WAS_SET = True


def close_terminal(exit_code=None) -> bool:
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


# =========================
# path related/file name related


def make_abs_path_relative_to_file(path, file):
    """makes a path absolute if relative with respect to the file (as if the file defined it)"""
    if not os.path.isabs(path):
        return os.path.normpath(os.path.dirname(file) + "\\" + path)
    else:
        return path


def sanitize_filename(filename, replacement="_"):
    """Sanitize a string so it can be used as a Windows filename."""
    import re

    # 1. Characters illegal in Windows: < > : " / \ | ? *
    # Also handles control characters (0-31)
    illegal_chars = r'[<>:"/\\|?*\x00-\x1f]'
    filename = re.sub(illegal_chars, replacement, filename)
    # 2. Windows reserved filenames (CON, PRN, AUX, NUL, COM1-9, LPT1-9)
    # These cannot be filenames even with an extension (e.g., CON.txt is bad)
    reserved_names = {
        "CON",
        "PRN",
        "AUX",
        "NUL",
        "COM1",
        "COM2",
        "COM3",
        "COM4",
        "COM5",
        "COM6",
        "COM7",
        "COM8",
        "COM9",
        "LPT1",
        "LPT2",
        "LPT3",
        "LPT4",
        "LPT5",
        "LPT6",
        "LPT7",
        "LPT8",
        "LPT9",
    }
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


def write_lines(path: str, lines: list[str], override=True):
    """lines are a list of strings without the endline symbol ("\n") added.
    If override==False it will append instead of recreating the file (default:  override=True)."""

    os.makedirs(os.path.dirname(path), exist_ok=True)

    lines_str = "\n".join(lines) + "\n"

    with open(path, "w" if override else "a", encoding="utf-8") as f:
        f.write(lines_str)


def read_lines(path: str):
    """returns a list of strings from path without the endline symbol ("\n" or "\r\n")"""

    with open(path, encoding="utf-8") as f:
        lines = f.readlines()  # readlines converts \r\n into \n

    return [l.rstrip("\n") for l in lines]


# =========================
# pid/process related


def get_running_processes_from_pid_file(pid_path: str) -> tuple[list[int], int]:
    """returns (running_process_ids, stale_count)"""

    if pid_path == "" or not os.path.exists(pid_path):
        return [], 0

    process_id_entries = _read_process_id_entries(pid_path)
    if not process_id_entries:
        os.remove(pid_path)
        return [], 0

    running_process_ids = []
    stale_count = 0
    seen_process_ids: set[int] = set()
    for process_id, _line in process_id_entries:
        if process_id in seen_process_ids:
            continue
        seen_process_ids.add(process_id)

        if _process_is_running(process_id):
            running_process_ids.append(process_id)
        else:
            stale_count += 1

    non_empty_lines = [str(pid) for pid in running_process_ids if str(pid).strip()]
    if non_empty_lines:
        write_lines(pid_path, non_empty_lines)
    elif os.path.exists(pid_path):
        os.remove(pid_path)

    return running_process_ids, stale_count


def stop_processes_from_pid_file(pid_path: str) -> tuple[int, int, list[str]]:
    """returns (stopped_count, stale_count, failed_messages)"""
    import subprocess

    def _wait_until_process_stops(pid: int, timeout_seconds: float) -> bool:
        import time

        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            if not _process_is_running(pid):
                return True
            time.sleep(0.1)
        return not _process_is_running(pid)

    def _stop_process_tree(pid: int) -> str:
        """WIP"""
        if not _process_is_running(pid):
            return ""
        cmd = ["taskkill", "/PID", str(pid), "/T"]
        try:
            graceful_result = subprocess.run(  # noqa:S603
                cmd,
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="oem",
                errors="replace",
            )

        except FileNotFoundError:
            import signal

            os.kill(pid, signal.SIGTERM)
            return ""

        graceful_output = (graceful_result.stdout or "").strip()
        if graceful_result.returncode == 0 and _wait_until_process_stops(pid, 2.0):
            return graceful_output

        if not _process_is_running(pid):
            return graceful_output
        forced_result = subprocess.run(  # noqa:S603
            cmd + ["/F"],  # force
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="oem",
            errors="replace",
        )
        forced_output = (forced_result.stdout or "").strip()
        if forced_result.returncode == 0 or _wait_until_process_stops(pid, 2.0):
            return "\n".join(output for output in [graceful_output, forced_output] if output)

        detail = forced_output or graceful_output
        if detail:
            raise RuntimeError(detail)
        raise RuntimeError(f"taskkill failed with exit code {forced_result.returncode}")

    if pid_path == "" or not os.path.exists(pid_path):
        return 0, 0, []

    process_id_entries = _read_process_id_entries(pid_path)
    if not process_id_entries:
        os.remove(pid_path)
        return 0, 0, []

    lines_by_process_id: dict[int, list[str]] = {}
    for process_id, line in process_id_entries:
        lines_by_process_id.setdefault(process_id, []).append(line)

    failed_lines = []
    failed_messages = []
    stopped_count = 0
    stale_count = 0
    for process_id, lines in lines_by_process_id.items():
        if not _process_is_running(process_id):
            stale_count += 1
            continue

        try:
            _stop_process_tree(process_id)
            stopped_count += 1
        except Exception as process_error:
            failed_lines.extend(lines)
            failed_messages.append(f"{process_id}: {process_error}")

    non_empty_lines = [l for l in failed_lines if l.strip()]
    if non_empty_lines:
        write_lines(pid_path, non_empty_lines)
    elif os.path.exists(pid_path):
        os.remove(pid_path)

    return stopped_count, stale_count, failed_messages


def _process_is_running(pid: int) -> bool:
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


def _read_process_id_entries(path: str) -> list[tuple[int, str]]:
    lines = read_lines(path)

    out = []
    for line in lines:
        line = line.strip()
        if line != "":
            process_id_text = line.split(maxsplit=1)[0]
            try:
                out.append((int(process_id_text), line))
            except ValueError:
                pass
    return out


# =========================
# python version related


def get_python_version():
    import subprocess

    return subprocess.check_output(  # noqa:S603
        [
            frontend_python_exe,
            "-c",
            "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')",
        ],
        stderr=subprocess.STDOUT,
        text=True,
    ).strip()


def is_python_version_compatible(actual_version, required_version):
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


def read_python_version_from_file():
    if not os.path.exists(python_version_indicator_file_path):
        print_warn(f'[Warning] missing file "{python_version_indicator_file_path}". Using Fallback determination.')
        return get_python_version()

    try:
        return read_lines(python_version_indicator_file_path)[0].strip()
    except Exception:
        print_warn("[Error] Failed to determine python version from file. Using Fallback determination.")
        return get_python_version()


def is_python_version_correct(target_version: str | float | int) -> tuple[bool, str | None]:
    """
    Returns whether the Python executable at ``exe_path`` matches ``target_version`` and the actual version:
        if target_version in [None, False, ""]:
            return [True,None]
        else:
            returns: [match,current_verison]

    Matching is prefix-based on proven version components:
    - If ``target_version`` is ``"3"``, any Python 3.x matches.
    - If ``target_version`` is ``"3.13"``, any Python 3.13.x matches.
    - If ``target_version`` is ``"3.13.2"``, only Python 3.13.2 matches.
    """
    if target_version in [None, False, ""]:
        return (True, None)

    if isinstance(target_version, (float, int)):
        target_version = str(target_version)

    found_version = read_python_version_from_file()

    return (is_python_version_compatible(found_version, target_version), found_version)


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

                # return found download links and pyhton version
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

            result = subprocess.run(  # noqa:S603
                [python_exe, "-m", "ensurepip", "--upgrade"],
                check=False,
                env=env,
            )
            if result.returncode != 0:
                raise RuntimeError("Python installation failed: ensurepip failed.")

            upgrade_args = ["-m", "pip", "install", "--upgrade", "pip", "--ignore-installed"]

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
                    [python_exe, *upgrade_args, "--progress-bar", "off"], check=False, stderr=subprocess.DEVNULL
                )
                # retry pip installation if failed without progress bar (for example if that flag is not there yet in the old pip version)
                if result.returncode != 0:
                    result = subprocess.run([python_exe, *upgrade_args], check=False)  # noqa
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

            result = subprocess.run([python_exe, get_pip_path], check=False)  # noqa

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
            "no-warn-script-location = false",
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
# python distribution related


def delete_python_distro():
    delete_folder_safe(
        frontend_python_dir,
        always_prompt_for_confirmation=False,
        allowed_base_abs_path=python_scripts_dir,
        expected_folder_name=None,
        required_included_files=None,
        required_included_dirs=None,
        require_direct_child_of_allowed_base=False,
        max_size_GB_before_prompt=1.2,
        min_path_depth=6,
    )
    os.makedirs(frontend_python_dir, exist_ok=True)


def recreate_python_distro() -> None:
    delete_python_distro()

    rel_path_dist_to_packages = os.path.relpath(path=frontend_packages_dir, start=frontend_python_dir)

    install_full_python(
        python_version=python_version,
        python_dir_abs_path=frontend_python_dir,
        install_tkinter=install_tkinter,
        install_tests=install_tests,
        install_tools=install_tools,
        install_docs=False,
        rel_path_to_packages=rel_path_dist_to_packages,
    )

    if not os.path.exists(frontend_python_exe):
        raise RuntimeError(f'Python installation did not produce expected file at "{frontend_python_exe}"')
    else:
        # save python verion to file
        with open(python_version_indicator_file_path, "w", encoding="utf-8") as f:
            f.write(get_python_version())
        # Create a batch file that launches a terminal that has python and pip install target set:
        batch_content = r"""
:: turn off command print and make variables local
@echo off & setlocal

:: settings (%~dp0 is file dir with "\" at end)
set "PYTHON_DIR=%~dp0.."
set "PACKAGES_TARGET=%~dp0..\..\packages"

:: local variables + resolve paths
for %%I in ("%PYTHON_DIR%") do set "PYTHON_DIR=%%~fI"
for %%I in ("%PACKAGES_TARGET%") do set "PACKAGES_TARGET=%%~fI"
set "PYTHON_EXE=%PYTHON_DIR%\python.exe"

:: create folder
if not exist "%PACKAGES_TARGET%" mkdir "%PACKAGES_TARGET%"

:: set global variables withing terminal to tell set python and package target and disable pip version check
set "PATH=%PYTHON_DIR%;%PYTHON_DIR%\Scripts;%PATH%"
set "PIP_TARGET=%PACKAGES_TARGET%"
set "PIP_DISABLE_PIP_VERSION_CHECK=1"
if defined PYTHONPATH (
    set "PYTHONPATH=%PACKAGES_TARGET%;%PYTHONPATH%"
) else (
    set "PYTHONPATH=%PACKAGES_TARGET%"
)

:: prints
echo Python exe:
echo "%PYTHON_EXE%"
echo Package install target:
echo "%PACKAGES_TARGET%"
echo.
echo Note: pip install commands in this terminal use the local package target. Install packages via "pip install {package-name}"
echo.

:: don't close terminal
cmd /k
"""
        os.makedirs(os.path.dirname(frontend_launcher_for_pip_install_terminal), exist_ok=True)
        with open(frontend_launcher_for_pip_install_terminal, "w", encoding="utf-8") as f:
            f.write(batch_content)


def prompt_for_distro_reinstall(msg="Reinstall distro / recreate virtual environment?"):
    """
    Return int in prints below for cases in print:
        print("0: Leave current Python version and packages")
        print("1: Change Python version + Reset packages + Reinstall default packages")
        print("2: Change Python version + Reset packages + Don't install packages")
        print("3: Change Python version + Reset packages + Reinstall current packages")
        print("4: Change Python version + Reset packages + Reinstall current packages + set them default")
        print("5: Change Python version + Reset packages + Install auto-determined needed packages")
        print("6: Change Python version + Reset packages + Install auto-determined needed packages + set them default")
    """
    print_warn(msg)
    print()
    print_warn("0: Leave current Python version and packages")
    print_warn("1: Change Python version + Reset packages + Reinstall default packages")
    print_warn("2: Change Python version + Reset packages + Don't install packages")
    print_warn("3: Change Python version + Reset packages + Reinstall current packages")
    print_warn("4: Change Python version + Reset packages + Reinstall current packages + set them default")
    print_warn("5: Change Python version + Reset packages + Install auto-determined needed packages")
    print_warn("6: Change Python version + Reset packages + Install auto-determined needed packages + set them default")

    while True:
        choice = input_warn("Choose an option [0-6]: ").strip()

        if choice in {"0", "1", "2", "3", "4", "5", "6"}:
            return int(choice)

        print_warn("Invalid choice. Please enter 0, 1, 2, 3, 4, 5, or 6.")


def ensure_python_distro(
    check_auto_determine_flag_for_default_package_install: bool = True, used_appid_if_slow: str = ""
):
    """returns if python version is correct"""

    if not os.path.exists(frontend_python_exe):  # no python distro existing case:
        set_terminal_appearance_once(used_appid_if_slow)
        print("\n" * 5)
        print("[Info] Python distribution not found. Installing Python:")
        recreate_python_distro()

        if are_frontend_packages_installed() == True:
            print("Deleting packages because are not connected to a Python exe.")
            delete_frontend_packages()
        return

    else:  # alread existing python distro case:
        if python_version:
            matching, actual_version = is_python_version_correct(python_version)
        else:
            matching = True

        if matching == True:  # right python version case:
            return

        else:  # wrong python version case:
            if not are_frontend_packages_installed():
                recreate_python_distro()
                return

            else:
                answer = prompt_for_distro_reinstall(
                    f"[Warning] Python version in settings ({python_version}) is not matching the current one ({actual_version}). Please enter how to proceed:"  # type:ignore
                )

                if answer == 0:
                    return
                elif answer in [1, 2, 3, 4, 5]:
                    set_terminal_appearance_once(used_appid_if_slow)
                    recreate_python_distro()
                    if answer == 1:
                        delete_frontend_packages()
                        install_default_packages(
                            check_auto_determine_flag=check_auto_determine_flag_for_default_package_install
                        )
                    elif answer == 2:
                        delete_frontend_packages()
                    elif answer in [3, 4]:
                        p = save_current_packages(with_version=False)
                        delete_frontend_packages()
                        install_packages_from_file(p)
                        if answer == 4:
                            save_current_packages_as_default()
                    elif answer in [5, 6]:
                        delete_frontend_packages()
                        success, p = save_requirements_of_root_folder_noVersion()
                        if success == True:
                            install_packages_from_file(p)
                            if answer == 6:
                                save_current_packages_as_default()
                        else:
                            print(
                                "[Warning] Failed to auto determine needed packages (see above). Installing default packages instead:"
                            )
                            install_default_packages(check_auto_determine_flag=False)
                else:
                    raise ValueError(f"Invalid answer: {answer}")


# ========================
# package related


def can_reach_pip_url(url: str = "https://pypi.org/simple/pip/", timeout_s: float = 5.0) -> bool:
    """Return True if the given URL can be reached."""
    import urllib.request

    try:
        request = urllib.request.Request(  # noqa
            url,
            headers={"User-Agent": "python-installer-check/1.0"},
        )

        with urllib.request.urlopen(request, timeout=timeout_s):  # noqa
            return True

    except OSError:
        return False


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


def delete_frontend_packages():
    """Delete the packages."""
    delete_folder_safe(
        frontend_packages_dir,
        always_prompt_for_confirmation=False,
        allowed_base_abs_path=python_scripts_dir,
        expected_folder_name=None,
        require_direct_child_of_allowed_base=False,
        max_size_GB_before_prompt=5.0,
        required_included_files=None,
        required_included_dirs=None,
        min_path_depth=6,
    )
    os.makedirs(frontend_packages_dir, exist_ok=True)


def are_frontend_packages_installed() -> bool:
    """returns True if frontend packages are installed"""

    if not os.path.exists(frontend_packages_dir):
        return False
    else:
        num_elems = len(os.listdir(frontend_packages_dir))

        if num_elems == 0:
            return False
        elif num_elems == 1:
            if os.path.exists(frontend_packages_are_installed_marker_path):
                return True
            else:
                return False
        else:
            return True


def ensure_frontend_packages(used_appid_if_slow: str = ""):
    ensure_python_distro(used_appid_if_slow=used_appid_if_slow)

    if not os.path.exists(frontend_packages_dir):  # packages folder not existing - case
        install_default_packages(check_auto_determine_flag=True, app_id_for_slow=used_appid_if_slow)

    else:  # packages folder existing - case
        if os.path.exists(frontend_packages_are_installed_marker_path):
            return
        else:
            print("[Info] Resetting Python packages:")
            delete_frontend_packages()  # resetting packages
            install_default_packages(check_auto_determine_flag=True, app_id_for_slow=used_appid_if_slow)

    # create file to note where to change packages if missing
    if not os.path.exists(dev_tools_referal_note_path):
        open(dev_tools_referal_note_path, "w", encoding="utf-8").close()


def install_packages_from_file(path: str, no_cache: bool = True, app_id_for_slow: str = "", print_=True) -> None:
    """raises if failur"""

    os.makedirs(frontend_packages_dir, exist_ok=True)

    if not os.path.exists(path):
        raise FileNotFoundError(f'Package list not found: "{path}"')

    packages = read_lines(path)
    actual_packgages = [l for l in packages if (not l.strip().startswith("#") and l.strip() != "")]

    if print_:
        print()
        print(f'[Info] Package list file: "{path}"')
        if len(actual_packgages) > 0:
            print("-" * 20)
            print(*actual_packgages, sep="\n")
            print("-" * 20)
            print()
        else:
            print("[Info] No packages to install.")
            print("-" * 20)
            print()

    # create file to indicate frontend packages as installed. (Needed to differentiate 0 packages from not yet installed)
    open(frontend_packages_are_installed_marker_path, "w", encoding="utf-8").close()

    if len(actual_packgages) == 0:
        return

    if app_id_for_slow:
        set_terminal_appearance_once(app_id_for_slow)

    try:
        install_packages(
            python_exe=frontend_python_exe,
            requirements_file=path,
            target=frontend_packages_dir,
            upgrade=True,
            no_cache=no_cache,
            use_uv=use_uv_to_install_packages,
            local_uv_python_exe=backend_python_exe,
        )
    except Exception as e:
        if not can_reach_pip_url():
            raise RuntimeError(
                f"Failed to install packages because cannot reach PyPI. Check internet, firewall, proxy, or DNS.: {e}"
            ) from e
        else:
            raise RuntimeError(f"Failed to install packages: {e}") from e


def install_default_packages(check_auto_determine_flag: bool, app_id_for_slow: str = ""):
    if check_auto_determine_flag == True:
        if get_auto_find_pckgs_phrase_state() == True:
            set_terminal_appearance_once(app_id_for_slow)
            print(
                f'[Info] Found flag "{variable_in_default_packages_path_that_triggers_search_if_true} = True" in default packages file "{default_packages_file_path}"'
            )
            print(
                "--> Auto determine needed packages & reset installed packages to them & set them as new defaults if success."
            )

            success, p = save_requirements_of_root_folder_noVersion()

            if success:
                install_packages_from_file(p)
                save_current_packages_as_default(auto_search_phrase_state=False)
                return
            else:
                raise RuntimeError("[Error] Failed to auto determine required Python packages.")
        else:
            install_packages_from_file(default_packages_file_path, app_id_for_slow=app_id_for_slow)
    else:
        install_packages_from_file(default_packages_file_path, app_id_for_slow=app_id_for_slow)


def get_auto_find_pckgs_phrase_state() -> bool | None:
    """WIP"""
    if not os.path.exists(default_packages_file_path):
        return None

    lines = read_lines(default_packages_file_path)

    for line in lines:
        if variable_in_default_packages_path_that_triggers_search_if_true not in line:
            continue
        value = (
            line.replace(variable_in_default_packages_path_that_triggers_search_if_true, "")
            .replace("=", "")
            .replace("#", "")
            .strip()
            .lower()
        )
        if value == "true":
            return True
        if value == "false":
            return False
        return None
    return None


def save_current_packages_as_default(auto_search_phrase_state=None, with_version=True):
    if auto_search_phrase_state is None:
        auto_search_phrase_state = get_auto_find_pckgs_phrase_state()

    packages = get_current_packages(with_version=with_version)

    write_lines(
        default_packages_file_path,
        [
            f"{variable_in_default_packages_path_that_triggers_search_if_true} = {auto_search_phrase_state}",
            "",
            *packages,
        ],
    )


def get_installed_packages(exe_path, with_version=True):
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


def get_current_packages(with_version=True):
    return get_installed_packages(exe_path=frontend_python_exe, with_version=with_version)


def save_installed_packages(exe_path, output_path=None, with_version=True):
    if output_path is None:
        if with_version == True:
            output_path = determined_current_packages_file_path_withVersion
        else:
            output_path = determined_current_packages_file_path_noVersion
    else:
        output_path = os.path.abspath(output_path)

    packages = get_installed_packages(with_version=with_version, exe_path=exe_path)

    write_lines(output_path, packages)

    return output_path


def save_current_packages(output_path=None, with_version=True):
    return save_installed_packages(output_path=output_path, with_version=with_version, exe_path=frontend_python_exe)


def save_requirements_of_root_folder_noVersion(
    output_path=determined_needed_packages_output_file_path_noVersion,
) -> tuple[bool, str]:
    """reuturns success,output_path"""

    import subprocess

    output_path = os.path.abspath(output_path)

    if os.path.exists(output_path):
        os.remove(output_path)

    try:
        cmd = [
            sys.executable,
            "-m",
            "pipreqs.pipreqs",
            python_scripts_dir,  # searched_folder,
            "--force",
            "--savepath",
            output_path,
            "--ignore",
            ",".join(excluded_folders_for_package_search),  # excluded_folders
            "--encoding",
            "utf-8",
            "--mode",
            "no-pin",
            "--no-follow-links",
        ]

        print()
        print("=" * 20)
        print("Start of finding required python packages")
        print("-" * 20)
        subprocess.run(cmd, check=True)  # noqa

        if os.path.exists(output_path):
            print("-" * 20)
            print(f'End of finding required python packages. Result: "{output_path}":\n')
            packages = read_lines(output_path)
            print(*packages, sep="\n")
            print("=" * 20)
            print()

            success = True

        else:
            success = False
            print()
            print_warn("[Error] Failed to auto determine needed packages (see above)")
    except Exception as e:
        print()
        print_warn(f"[Error] Failed to auto determine packages (do you have internet?): {e}")
        success = False

    return success, output_path


def save_requirements_of_root_folder_withVersion(
    output_path: str = determined_needed_packages_output_file_path_withVersion,
) -> bool:
    """returns success bool. Installation into a fresh temp venv needed to determine package versions. Pipreqs only can determine what packages are needed."""

    # lazy imports
    import subprocess
    import tempfile

    output_path = os.path.normpath(os.path.abspath(output_path))

    success, output_path_noVersion = save_requirements_of_root_folder_noVersion()

    if success == False:
        return False

    ensure_python_distro()

    try:
        with tempfile.TemporaryDirectory(prefix="tmp_venv_to_get_package_version") as tmp:
            temp_python = tmp + "\\Scripts\\python.exe"

            subprocess.run([frontend_python_exe, "-m", "venv", tmp], check=True)  # noqa
            if not os.path.exists(temp_python):
                raise RuntimeError(f'Temporary environment did not create "{temp_python}"')

            subprocess.run(  # noqa
                [temp_python, "-m", "pip", "install", "-r", output_path_noVersion, "--disable-pip-version-check"],
                check=True,
            )

            save_installed_packages(exe_path=temp_python, output_path=output_path, with_version=True)

            return True

    except Exception as e:
        print()
        print_warn(f"[Error] Failed to auto determine packages: {e}")
        return False


# ========================
# debug test area
# ========================

# if __name__ == "__main__":
#     install_full_python(
#         python_version="3.3",
#         python_dir_abs_path=r"C:\Users\Flo\Documents\Repositories\PyApp Template\code\test",
#         install_tkinter=False,
#         install_tests=False,
#         install_tools=False,
#         install_docs=False,
#         rel_path_to_packages="test",
#     )


# ========================
