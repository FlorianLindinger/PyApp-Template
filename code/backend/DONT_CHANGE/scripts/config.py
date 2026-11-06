"""Load and validate developer_settings.py with messages that point at the setting to fix."""

from __future__ import annotations

import ast
import importlib
import os
import re
import sys

from backend.DONT_CHANGE.backend_settings import DEV_SETTINGS_PATH
from backend.DONT_CHANGE.scripts.errors import SettingsError

# Read by bootstrap/resolve_runtime.ps1 before Python exists; must stay one-line literals.
BOOTSTRAP_SETTINGS = (
    "python_version",
    "python_source",
    "package_environment",
    "uv_prefer",
    "uv_install_if_missing",
    "uv_version",
    "uv_user_python_visible_globally",
    "uv_cache",
    "allow_downloads_at_launch",
    "use_system_certificates",
)

# Fonts of the app name banner (scripts/banner.py; files in data/fonts).
BANNER_FONTS = ("future", "future_smooth", "standard", "coder_mini")

CHOICES = {
    "python_source": (
        "local",
        "uv_user",
        "system_if_matching_else_local",
        "system_default_any_version",
    ),
    "package_environment": ("project_venv", "interpreter_site_packages"),
    "uv_prefer": ("global", "local"),
    "uv_install_if_missing": ("global", "local", "never"),
    "uv_cache": ("global", "local"),
    "instance_policy": ("allow", "focus", "prevent", "replace", "ask"),
}
SHORTCUT_KINDS = (
    "terminal",
    "no_terminal",
    "stop",
    "settings",
    "logs",
    "crash_logs",
    "main_py",
)
BOOLEANS = (
    "uv_user_python_visible_globally",
    "allow_downloads_at_launch",
    "use_system_certificates",
    "allow_installing_into_global_python",
    "install_environment_when_generating_shortcuts",
    "start_menu_shortcuts",
    "start_in_shortcut_folder",
    "start_minimized",
    "use_classic_terminal",
    "traceback_colors",
    "enable_log_for_terminal_start",
    "enable_log_for_no_terminal_start",
    "overwrite_log",
    "overwrite_crash_log",
    "log_path_is_relative_to_start_folder_if_relative",
    "crash_log_path_is_relative_to_start_folder_if_relative",
)


OUTCOMES = ("success", "failure", "crash", "keyboard_interrupt")
SHORTCUT_NAME_SETTINGS = (
    "terminal_shortcut_name",
    "no_terminal_shortcut_name",
    "open_settings_shortcut_name",
    "stop_running_shortcut_name",
    "open_log_folder_shortcut_name",
    "open_crash_log_folder_shortcut_name",
    "open_main_py_shortcut_name",
)
SUB_ICON_KINDS = (
    "settings",
    "stop",
    "log",
    "success",
    "failure",
    "crash",
    "crash_log",
    "open_main_py",
    "keyboard_interrupt",
)
_ALIGNMENT_WORDS = {"top", "bottom", "left", "right", "center", "up", "down", "middle", "centre"}


def _number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _alignment_ok(value) -> bool:
    """Same rules as image_tools.generate_ico_from_png."""
    if not isinstance(value, str):
        return False
    words = value.lower().replace("_", " ").replace("-", " ").split()
    return bool(words) and all(word in _ALIGNMENT_WORDS for word in words)


def _sound_path(value: str) -> str:
    """Same rules as process_exit.play_sound: relative names are in C:\\Windows\\Media, ".wav" is optional."""
    from backend.DONT_CHANGE.backend_settings import WINDOWS_DIR

    path = value if os.path.isabs(value) else os.path.join(WINDOWS_DIR, "Media", value)
    return path if path.lower().endswith(".wav") else path + ".wav"


def _strftime_problem(value: str) -> str | None:
    """Explain a date format Windows' strftime rejects (e.g. "%Q" or a trailing "%")."""
    from datetime import datetime

    try:
        datetime.now().astimezone().strftime(value)
    except ValueError as error:
        return f"invalid date format ({error}); see the strftime codes, e.g. %Y-%m-%d %H:%M:%S"
    return None


# A requirement starts with a distribution name (PEP 508); uv checks the rest (versions, extras, markers).
REQUIREMENT_START = re.compile(r"\s*[A-Za-z0-9][A-Za-z0-9._-]*\s*($|[\[(<>=!~;@ ])")


def settings():
    """Import developer_settings, turning any error in the file into a short actionable message."""
    from backend.DONT_CHANGE.scripts.entrypoint import settings_file_problem

    try:
        return importlib.import_module("backend.developer_settings")
    except Exception as error:
        problem = settings_file_problem(error)
        if problem is None:
            raise
        raise SettingsError(problem) from None


def _assigned_names(node) -> list[str]:
    """Names a plain `name = ...` or `name: type = ...` statement assigns."""
    if isinstance(node, ast.Assign):
        return [t.id for t in node.targets if isinstance(t, ast.Name)]
    if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.value is not None:
        return [node.target.id]
    return []


def _bootstrap_literal_problems() -> list[str]:
    """The batch bootstrap reads some settings with a line-based parser; keep them simple and unique.

    It reads only unindented lines and takes the last definition, like Python; a setting that is
    defined twice, indented (e.g. inside an "if") or not a one-line literal could differ between the two.
    """
    problems = []
    with open(DEV_SETTINGS_PATH, encoding="utf-8") as stream:
        tree = ast.parse(stream.read(), DEV_SETTINGS_PATH)
    top_level = {id(node) for node in tree.body}
    definitions: dict[str, list[ast.Assign | ast.AnnAssign]] = {}
    for node in ast.walk(tree):
        for name in _assigned_names(node):
            if name in BOOTSTRAP_SETTINGS and isinstance(node, (ast.Assign, ast.AnnAssign)):
                definitions.setdefault(name, []).append(node)
    for name in BOOTSTRAP_SETTINGS:
        nodes = sorted(definitions.get(name, []), key=lambda n: n.lineno)
        if len(nodes) > 1:
            lines = ", ".join(str(n.lineno) for n in nodes)
            problems.append(
                f"{name} is set {len(nodes)} times (lines {lines}); keep only one, because the Windows bootstrap reads it."
            )
        for node in nodes:
            value = node.value
            plain = isinstance(value, ast.Constant) and (value.value is None or isinstance(value.value, (str, bool)))
            if id(node) not in top_level or node.col_offset != 0:
                problems.append(
                    f"{name} (line {node.lineno}) must be set unindented at the top of the file because the Windows bootstrap reads it."
                )
            elif not plain or node.lineno != getattr(node, "end_lineno", node.lineno):
                problems.append(
                    f'{name} must be a plain one-line value ("text", True, False or None) because the Windows bootstrap reads it.'
                )
    return problems


def python_version_problem(value: str) -> str | None:
    """Explain an obviously unsupported python_version; uv validates exotic request strings itself."""
    if not value:
        return None
    match = re.fullmatch(r"(\d+)(?:\.(\d+))?(?:\.(\d+))?(t)?", value)
    if not match:
        return None  # e.g. "pypy@3.11" or ">=3.11" is passed to uv unchanged
    major = int(match.group(1))
    minor = None if match.group(2) is None else int(match.group(2))
    if major != 3:
        return f'python_version "{value}" is not supported: only Python 3 versions exist on uv (3.8.2 and newer on Windows x64).'
    if minor is not None and minor < 8:
        return f'python_version "{value}" is not supported: the launcher needs Python 3.8 or newer (uv offers 3.8.2 and newer on Windows x64).'
    return None


def validate(module=None) -> None:
    """Raise SettingsError listing every unusable setting."""
    s = module or settings()
    problems = list(_bootstrap_literal_problems())

    def get(name, default=None):
        return getattr(s, name, default)

    def need(name, ok, message):
        if not hasattr(s, name):
            problems.append(f"{name} is missing. Add it again (see the template's developer_settings.py).")
        elif not ok(getattr(s, name)):
            problems.append(f"{name} = {getattr(s, name)!r}: {message}")

    for name, choices in CHOICES.items():
        need(name, lambda v, c=choices: v in c, "use one of " + ", ".join(repr(c) for c in choices))
    for name in BOOLEANS:
        need(name, lambda v: isinstance(v, bool), "use True or False")
    need("program_name", lambda v: isinstance(v, str) and v.strip(), "use a non-empty text")
    need(
        "app_name_banner_font",
        lambda v: v is None or v in BANNER_FONTS,
        "use one of " + ", ".join(repr(font) for font in BANNER_FONTS) + " or None",
    )
    need("python_version", lambda v: isinstance(v, str), 'use text such as "3.14" or "" for the newest')
    python_version = get("python_version")
    version_problem = python_version_problem(python_version if isinstance(python_version, str) else "")
    if version_problem:
        problems.append(version_problem)
    need(
        "uv_version",
        lambda v: isinstance(v, str) and re.fullmatch(r"[0-9.,<>=!~ ]*", v),
        'use "" or a version like "0.11.32" or ">=0.9,<1"',
    )
    need(
        "desktop_shortcuts",
        lambda v: isinstance(v, (list, tuple)) and all(k in SHORTCUT_KINDS for k in v),
        "use a list of " + ", ".join(repr(k) for k in SHORTCUT_KINDS),
    )
    need(
        "args_for_main_py",
        lambda v: isinstance(v, (list, tuple)) and all(isinstance(a, str) for a in v),
        "use a list of strings",
    )
    need(
        "packages",
        lambda v: isinstance(v, (list, tuple)) and all(isinstance(p, str) and REQUIREMENT_START.match(p) for p in v),
        'use a list of package requirements such as ["requests", "numpy>=2"]',
    )
    for name in ("max_log_files", "max_run_folder_age_days"):
        need(
            name,
            lambda v: v is None or (isinstance(v, int) and not isinstance(v, bool) and v > 0),
            "use a positive whole number or None",
        )
    need(
        "traceback_extra_lines",
        lambda v: isinstance(v, int) and not isinstance(v, bool) and v >= 0,
        "use 0 or a positive whole number",
    )
    for name in ("log_path", "crash_log_path", "user_settings_path"):
        need(name, lambda v: v is None or isinstance(v, str), "use a path text or None")
    for name in ("terminal_bg_color", "terminal_text_color"):
        need(
            name,
            lambda v: v in (None, "") or (isinstance(v, str) and re.fullmatch(r"[0-9A-Fa-f]", v)),
            "use one hex digit 0-9/A-F or None",
        )
    for outcome in OUTCOMES:
        need(
            "terminal_colors_after_" + outcome,
            lambda v: v in (None, "") or (isinstance(v, str) and re.fullmatch(r"[0-9A-Fa-f]{2}", v)),
            'use two hex digits like "4F" or None',
        )
    need(
        "tab_bar_color",
        lambda v: v is None or (isinstance(v, str) and re.fullmatch(r"#[0-9A-Fa-f]{6}", v)),
        'use a color like "#3B78FF" or None',
    )
    need("stop_timeout_seconds", lambda v: _number(v) and v >= 0, "use 0 (stop immediately) or a number of seconds")

    for name in SHORTCUT_NAME_SETTINGS:
        need(name, lambda v: v is None or (isinstance(v, str) and v.strip()), "use a non-empty text or None")
    for outcome in OUTCOMES:
        for prefix in ("close_after_", "open_log_file_after_", "open_main_py_after_"):
            need(prefix + outcome, lambda v: isinstance(v, bool), "use True or False")
        need("title_after_" + outcome, lambda v: v is None or isinstance(v, str), "use a text or None")
        name = "play_sound_after_" + outcome
        need(name, lambda v: isinstance(v, (bool, str)), 'use True, False or a .wav name such as "Windows Ding.wav"')
        sound = get(name)
        if isinstance(sound, str) and sound and not os.path.isfile(_sound_path(sound)):
            problems.append(
                f'{name} = {sound!r}: "{_sound_path(sound)}" does not exist (use True, False or an existing .wav file).'
            )
    for name in (
        "print_prepend",
        "input_prepend",
        "log_print_prepend",
        "log_input_prepend",
        "error_date_format",
        "log_path",
        "crash_log_path",
    ):
        value = get(name)
        if isinstance(value, str) and "%" in value:
            problem = _strftime_problem(value)
            if problem:
                problems.append(f"{name} = {value!r}: {problem}")
    for name in ("print_prepend", "input_prepend", "log_print_prepend", "log_input_prepend"):
        need(name, lambda v: v is None or isinstance(v, str), 'use a text such as "%H:%M:%S | " or None')
    need("error_date_format", lambda v: isinstance(v, str), 'use a date format such as "%Y-%m-%d %H:%M:%S"')
    for kind in SUB_ICON_KINDS:
        need(
            kind + "_sub_icon_scale",
            lambda v: v is None or (_number(v) and 0 < v <= 1),
            "use a number greater than 0 and at most 1, or None",
        )
        need(
            kind + "_sub_icon_alignment",
            lambda v: v is None or _alignment_ok(v),
            'use a position such as "bottom right", "top", "center left", or None',
        )

    if get("package_environment") == "interpreter_site_packages" and get("python_source") in ("local", "uv_user"):
        problems.append(
            'package_environment = "interpreter_site_packages" only works with python_source = "system_if_matching_else_local" '
            'or "system_default_any_version" (a uv-managed Python must not be modified directly). Use "project_venv".'
        )
    if problems:
        raise SettingsError(
            "Please fix developer_settings.py:\n  " + "\n  ".join(problems) + f'\n  File: "{DEV_SETTINGS_PATH}"'
        )


def edit_settings(changes: dict) -> list[str]:
    """Set top-level settings in developer_settings.py to new values; return a readable diff.

    Only the value is replaced: annotations, trailing comments and line endings are kept.
    """
    diff = []
    for name, value in changes.items():
        literal = _literal(value)
        diff += _replace_setting_value(name, lambda newline, literal=literal: literal)
    return diff


def set_list_setting(name: str, values) -> list[str]:
    """Rewrite the top-level list setting `name` (it may span several lines); return a readable diff."""
    values = list(values)

    def body(newline: str) -> str:
        if not values:
            return "[]"
        return "[" + newline + "".join("    " + _quoted(v) + "," + newline for v in values) + "]"

    return _replace_setting_value(name, body)


def _replace_setting_value(name: str, make_value) -> list[str]:
    """Replace the value of the last top-level assignment to `name` (the one Python uses).

    make_value(newline) returns the new value's source text. The file's line endings are kept.
    """
    with open(DEV_SETTINGS_PATH, encoding="utf-8", newline="") as stream:
        source = stream.read()
    newline = "\r\n" if "\r\n" in source else "\n"
    # Split exactly where ast counts lines (str.splitlines also splits at e.g. U+2028).
    lines = re.findall(r"[^\r\n]*(?:\r\n|\r|\n)|[^\r\n]+$", source)
    node = None
    for item in ast.parse(source, DEV_SETTINGS_PATH).body:
        if name in _assigned_names(item):
            node = item
    if node is None:
        raise SettingsError(f"Could not find the setting {name} in developer_settings.py to edit.")
    first, last = node.lineno - 1, (node.end_lineno or node.lineno) - 1
    # ast offsets count UTF-8 bytes
    head = lines[first].encode("utf-8")[: node.value.col_offset].decode("utf-8")  # e.g. "packages: list[str] = "
    tail = lines[last].encode("utf-8")[node.value.end_col_offset :].decode("utf-8").rstrip("\r\n")  # e.g. a comment
    replacement = (head + make_value(newline) + tail).rstrip() + newline
    old = "".join(lines[first : last + 1])
    if replacement == old:
        return []
    lines[first : last + 1] = [replacement]
    with open(DEV_SETTINGS_PATH, "w", encoding="utf-8", newline="") as stream:
        stream.write("".join(lines))
    sys.modules.pop("backend.developer_settings", None)
    return [f"- {line}" for line in old.rstrip().splitlines()] + [
        f"+ {line}" for line in replacement.rstrip().splitlines()
    ]


def _literal(value) -> str:
    """Python source text for a setting value."""
    if isinstance(value, str):
        return _quoted(value)
    if value is None or isinstance(value, (bool, int, float)):
        return repr(value)
    raise SettingsError(f"Cannot write the value {value!r} into developer_settings.py.")


def _quoted(value: str) -> str:
    """Double-quoted Python string literal (the style used in developer_settings.py)."""
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def describe_python_request(value: str) -> str:
    """Human-readable form of the python_version setting."""
    return f'"{value}"' if value else '"" (newest stable, chosen once)'


def display_path(path: str) -> str:
    """Shorten a path below the repository root for messages."""
    from backend.DONT_CHANGE.backend_settings import SHORTCUT_OUTPUT_DIR

    try:
        relative = os.path.relpath(path, SHORTCUT_OUTPUT_DIR)
    except ValueError:
        return path
    return path if relative.startswith("..") else relative
