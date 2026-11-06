"""Load and validate developer_settings.py with messages that point at the setting to fix."""

from __future__ import annotations

import ast
import importlib
import os
import re
import sys

from backend.DONT_CHANGE.backend_settings import DEV_SETTINGS_PATH

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
    "enable_log_for_Windows_terminal_start",
    "enable_log_for_no_terminal_start",
    "overwrite_log",
    "overwrite_crash_log",
    "log_path_is_relative_to_start_folder_if_relative",
    "crash_log_path_is_relative_to_start_folder_if_relative",
)


# A requirement starts with a distribution name (PEP 508); uv checks the rest (versions, extras, markers).
REQUIREMENT_START = re.compile(r"\s*[A-Za-z0-9][A-Za-z0-9._-]*\s*($|[\[(<>=!~;@ ])")


class SettingsError(Exception):
    """A developer_settings.py value cannot be used."""


def settings():
    """Import developer_settings, turning syntax errors into a short actionable message."""
    try:
        return importlib.import_module("backend.developer_settings")
    except SyntaxError as error:
        raise SettingsError(
            f'developer_settings.py has a syntax error in line {error.lineno}: {error.msg}\n  "{DEV_SETTINGS_PATH}"'
        ) from None


def _bootstrap_literal_problems() -> list[str]:
    """The batch bootstrap parses some settings with a regex; require plain one-line literals."""
    problems = []
    with open(DEV_SETTINGS_PATH, encoding="utf-8") as stream:
        tree = ast.parse(stream.read())
    for node in tree.body:
        targets = []
        if isinstance(node, ast.Assign):
            targets = [t.id for t in node.targets if isinstance(t, ast.Name)]
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            targets = [node.target.id]
        for name in targets:
            if name not in BOOTSTRAP_SETTINGS:
                continue
            value = node.value
            plain = isinstance(value, ast.Constant) and (
                value.value is None or isinstance(value.value, (str, bool))
            )
            if not plain or node.lineno != getattr(node, "end_lineno", node.lineno):
                problems.append(
                    f'{name} must be a plain one-line value ("text", True, False or None) because the Windows bootstrap reads it.'
                )
    return problems


def _version_problem(value: str) -> str | None:
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
    need("python_version", lambda v: isinstance(v, str), 'use text such as "3.14" or "" for the newest')
    version_problem = _version_problem(get("python_version", "") if isinstance(get("python_version"), str) else "")
    if version_problem:
        problems.append(version_problem)
    need("uv_version", lambda v: isinstance(v, str) and re.fullmatch(r"[0-9.,<>=!~ ]*", v), 'use "" or a version like "0.11.32" or ">=0.9,<1"')
    need("desktop_shortcuts", lambda v: isinstance(v, (list, tuple)) and all(k in SHORTCUT_KINDS for k in v), "use a list of " + ", ".join(repr(k) for k in SHORTCUT_KINDS))
    need("args_for_main_py", lambda v: isinstance(v, (list, tuple)) and all(isinstance(a, str) for a in v), "use a list of strings")
    need("packages", lambda v: isinstance(v, (list, tuple)) and all(isinstance(p, str) and REQUIREMENT_START.match(p) for p in v),
         'use a list of package requirements such as ["requests", "numpy>=2"]')
    for name in ("max_log_files", "max_run_folder_age_days"):
        need(name, lambda v: v is None or (isinstance(v, int) and not isinstance(v, bool) and v > 0), "use a positive whole number or None")
    need("traceback_extra_lines", lambda v: isinstance(v, int) and not isinstance(v, bool) and v >= 0, "use 0 or a positive whole number")
    for name in ("log_path", "crash_log_path", "user_settings_path"):
        need(name, lambda v: v is None or v is False or isinstance(v, str), "use a path text or None")
    for name in ("terminal_bg_color", "terminal_text_color"):
        need(name, lambda v: v in (None, "") or (isinstance(v, str) and re.fullmatch(r"[0-9A-Fa-f]", v)), "use one hex digit 0-9/A-F or None")
    for outcome in ("success", "failure", "crash", "KeyboardInterrupt"):
        need("terminal_colors_after_" + outcome, lambda v: v in (None, "") or (isinstance(v, str) and re.fullmatch(r"[0-9A-Fa-f]{2}", v)), 'use two hex digits like "4F" or None')
    need("tab_bar_color", lambda v: v is None or (isinstance(v, str) and re.fullmatch(r"#[0-9A-Fa-f]{6}", v)), 'use a color like "#3B78FF" or None')

    if get("package_environment") == "interpreter_site_packages" and get("python_source") in ("local", "uv_user"):
        problems.append(
            'package_environment = "interpreter_site_packages" only works with python_source = "system_if_matching_else_local" '
            'or "system_default_any_version" (a uv-managed Python must not be modified directly). Use "project_venv".'
        )
    if problems:
        raise SettingsError(
            "Please fix developer_settings.py:\n  "
            + "\n  ".join(problems)
            + f'\n  File: "{DEV_SETTINGS_PATH}"'
        )


def edit_settings(changes: dict) -> list[str]:
    """Rewrite top-level `name = value` lines in developer_settings.py; return a readable diff."""
    with open(DEV_SETTINGS_PATH, encoding="utf-8") as stream:
        lines = stream.read().splitlines(keepends=True)
    diff = []
    remaining = dict(changes)
    for index, line in enumerate(lines):
        for name in list(remaining):
            match = re.match(r"^(" + re.escape(name) + r"\s*(?::[^=]*)?=\s*)(.*?)(\r?\n)?$", line)
            if match:
                new = match.group(1) + repr(remaining.pop(name)).replace("'", '"') + (match.group(3) or "")
                if new != line:
                    diff.append(f"- {line.rstrip()}\n+ {new.rstrip()}")
                lines[index] = new
    if remaining:
        raise SettingsError("Could not find these settings to edit: " + ", ".join(remaining))
    with open(DEV_SETTINGS_PATH, "w", encoding="utf-8", newline="") as stream:
        stream.write("".join(lines))
    sys.modules.pop("backend.developer_settings", None)
    return diff


def set_list_setting(name: str, values) -> list[str]:
    """Rewrite the top-level list setting `name` (it may span several lines); return a readable diff."""
    with open(DEV_SETTINGS_PATH, encoding="utf-8", newline="") as stream:
        source = stream.read()
    newline = "\r\n" if "\r\n" in source else "\n"
    lines = source.splitlines(keepends=True)
    node = None
    for item in ast.parse(source).body:
        target = item.target if isinstance(item, ast.AnnAssign) else (item.targets[0] if isinstance(item, ast.Assign) and len(item.targets) == 1 else None)
        if isinstance(target, ast.Name) and target.id == name and item.value is not None:
            node = item
    if node is None:
        raise SettingsError(f"Could not find the setting {name} in developer_settings.py to edit.")
    first, last = node.lineno - 1, node.end_lineno - 1
    # ast offsets count UTF-8 bytes
    head = lines[first].encode("utf-8")[: node.value.col_offset].decode("utf-8")  # e.g. "packages: list[str] = "
    tail = lines[last].encode("utf-8")[node.value.end_col_offset :].decode("utf-8").rstrip("\r\n")  # e.g. a comment
    if values:
        body = "[" + newline + "".join("    " + _quoted(v) + "," + newline for v in values) + "]"
    else:
        body = "[]"
    replacement = (head + body + tail).rstrip() + newline
    old = "".join(lines[first : last + 1])
    if replacement == old:
        return []
    lines[first : last + 1] = [replacement]
    with open(DEV_SETTINGS_PATH, "w", encoding="utf-8", newline="") as stream:
        stream.write("".join(lines))
    sys.modules.pop("backend.developer_settings", None)
    return [f"- {line}" for line in old.rstrip().splitlines()] + [f"+ {line}" for line in replacement.rstrip().splitlines()]


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
