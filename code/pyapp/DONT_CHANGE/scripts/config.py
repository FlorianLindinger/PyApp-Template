"""Load and validate developer_settings.py with messages that point at the setting to fix."""

from __future__ import annotations

import ast
import importlib
import math
import os
import re
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Union

from pyapp.DONT_CHANGE.backend_settings import (
    BACKEND_DIR,
    DEFAULT_SETTINGS_PATH,
    DEV_SETTINGS_PATH,
    PYTHON_SCRIPTS_DIR,
)
from pyapp.DONT_CHANGE.scripts.errors import SettingsError

# Read by bootstrap/resolve_runtime.py before Python exists; must stay one-line literals.
BOOTSTRAP_SETTINGS = (
    "python_version",
    "python_source",
    "uv_prefer",
    "uv_install_if_missing",
    "uv_version",
    "uv_user_python_visible_globally",
    "uv_cache",
    "use_system_certificates",
)

CHOICES = {
    "python_source": ("local", "uv_user", "system"),
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
    "open_code",
)
# GitHub Actions an app can choose in github_actions; one data/workflows/<name>.yml each.
APP_WORKFLOWS = ("leaks",)
BOOLEANS = (
    "uv_user_python_visible_globally",
    "use_system_certificates",
    "start_menu_shortcuts",
    "start_in_shortcut_folder",
    "start_minimized",
    "use_classic_terminal",
    "enable_log_for_terminal_start",
    "enable_log_for_no_terminal_start",
    "enable_crash_log",
    "open_crash_log_after_failure",
    "play_sound_after_success",
    "play_sound_after_failure",
    "log_path_is_relative_to_start_folder_if_relative",
    "crash_log_path_is_relative_to_start_folder_if_relative",
)


OUTCOMES = ("success", "failure", "keyboard_interrupt")
SHORTCUT_NAME_SETTINGS = (
    "terminal_shortcut_name",
    "no_terminal_shortcut_name",
    "open_settings_shortcut_name",
    "stop_running_shortcut_name",
    "open_log_folder_shortcut_name",
    "open_crash_log_folder_shortcut_name",
    "open_code_shortcut_name",
)


def _number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _strftime_problem(value: str) -> Optional[str]:
    """Explain a date format Windows' strftime rejects (e.g. "%Q" or a trailing "%")."""
    from datetime import datetime

    try:
        datetime.now().astimezone().strftime(value)
    except ValueError as error:
        return f"invalid date format ({error}); see the strftime codes, e.g. %Y-%m-%d %H:%M:%S"
    return None


# A requirement starts with a distribution name (PEP 508); uv checks the rest (versions, extras, markers).
REQUIREMENT_START = re.compile(r"\s*[A-Za-z0-9][A-Za-z0-9._-]*\s*($|[\[(<>=!~;@ ])")


def main_script_path(s: Optional[Union[ModuleType, SimpleNamespace]] = None) -> str:
    """Absolute path of the file the launcher runs (main_script_path in developer_settings.py)."""
    return _resolve_main_script((s or settings()).main_script_path)


def _resolve_main_script(value: str) -> str:
    # Keep os.path.isabs: rooted Windows paths have different pathlib semantics on Python 3.8-3.12.
    return value if os.path.isabs(value) else os.path.normpath(str(Path(BACKEND_DIR) / value))  # noqa: PTH117


def _main_script_problem(value: str) -> Optional[str]:
    """Tracebacks, the import finder and the launcher's own folders all assume this location."""
    path = _resolve_main_script(value)
    if not Path(path).is_file():
        return f'main_script_path: "{path}" does not exist.'
    root = os.path.normcase(os.path.normpath(str(Path(PYTHON_SCRIPTS_DIR).absolute()))) + os.sep
    full = os.path.normcase(os.path.normpath(str(Path(path).absolute())))
    if not full.startswith(root) or full[len(root) :].split(os.sep, 1)[0] == "pyapp":
        return f'main_script_path: "{path}" must be inside the code folder and not in code\\pyapp.'
    return None


def parse_requirements(text: str) -> List[str]:
    """The packages of a pasted requirements.txt: one per line, without comments and --hash options."""
    entries = []
    pending = ""
    # The extra "" ends a continuation on the last line.
    for line in [*text.splitlines(), ""]:
        # Like pip, join a line ending in a backslash with the next one first, so the --hash
        # options that tools like pip-compile put on their own lines are removed with them.
        if line.rstrip().endswith("\\"):
            pending += line.rstrip()[:-1] + " "
            continue
        line, pending = pending + line, ""
        line = re.sub(r"(^|\s)#.*$", "", line)  # pip's rule: "#" starts a comment only after whitespace
        line = re.sub(r"(^|\s)--hash=\S+", "", line).strip()
        if line:
            entries.append(line)
    return entries


def settings() -> ModuleType:
    """Import developer_settings, turning any error in the file into a short actionable message."""
    from pyapp.DONT_CHANGE.scripts.entrypoint import settings_file_problem

    try:
        module = importlib.import_module("pyapp.developer_settings")
    except Exception as error:
        problem = settings_file_problem(error)
        if problem is None:
            raise
        raise SettingsError(problem) from None
    fill_missing_settings(module)
    packages = getattr(module, "packages", None)
    if isinstance(packages, str):
        vars(module)["packages"] = parse_requirements(packages)
    return module


def default_setting_expressions(path: Optional[str] = None) -> Dict[str, ast.expr]:
    """{name: expression node} of every top-level setting in the defaults file (last one wins)."""
    path = path or DEFAULT_SETTINGS_PATH
    with Path(path).open(encoding="utf-8") as stream:
        tree = ast.parse(stream.read(), path)
    expressions = {}
    for node in tree.body:
        if isinstance(node, (ast.Assign, ast.AnnAssign)) and node.value is not None:
            for name in _assigned_names(node):
                expressions[name] = node.value
    return expressions


def fill_missing_settings(module: Union[ModuleType, SimpleNamespace]) -> List[str]:
    """Give settings that the project's file lacks their default value; return their names.

    Defaults may refer to other settings (f"{program_name}"), which then use the project's values.
    """
    if hasattr(module, "MISSING_SETTINGS_FILLED_IN"):
        return module.MISSING_SETTINGS_FILLED_IN
    filled = []
    try:
        expressions = default_setting_expressions()
    except OSError:
        expressions: Dict[str, ast.expr] = {}
    for name, expression in expressions.items():
        if hasattr(module, name):
            continue
        try:
            # Evaluate expressions only from the bundled defaults, including references and f-strings.
            value = eval(compile(ast.Expression(expression), DEFAULT_SETTINGS_PATH, "eval"), vars(module))  # noqa: S307
        except Exception:
            from pyapp.DONT_CHANGE.scripts.diagnostics import note_ignored

            note_ignored(f"default of {name}")  # validate() then reports the setting as missing
            continue
        setattr(module, name, value)
        filled.append(name)
    vars(module)["MISSING_SETTINGS_FILLED_IN"] = filled
    return filled


def _assigned_names(node: ast.AST) -> List[str]:
    """Names a plain `name = ...` or `name: type = ...` statement assigns."""
    if isinstance(node, ast.Assign):
        return [t.id for t in node.targets if isinstance(t, ast.Name)]
    if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.value is not None:
        return [node.target.id]
    return []


def _bootstrap_literal_problems() -> List[str]:
    """The batch bootstrap reads some settings with a line-based parser; keep them simple and unique.

    It reads only unindented lines and takes the last definition, like Python; a setting that is
    defined twice, indented (e.g. inside an "if") or not a one-line literal could differ between the two.
    """
    problems = []
    with Path(DEV_SETTINGS_PATH).open(encoding="utf-8") as stream:
        tree = ast.parse(stream.read(), DEV_SETTINGS_PATH)
    top_level = {id(node) for node in tree.body}
    definitions: Dict[str, List[Union[ast.Assign, ast.AnnAssign]]] = {}
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


def python_version_problem(value: str) -> Optional[str]:
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


_noted_defaults = set()


def _note_defaults_once(module: Union[ModuleType, SimpleNamespace]) -> None:
    """Tell once per process which settings were missing and use their defaults."""
    names = [n for n in getattr(module, "MISSING_SETTINGS_FILLED_IN", []) if n not in _noted_defaults]
    if not names:
        return
    _noted_defaults.update(names)
    from pyapp.DONT_CHANGE.scripts.console_tools import print_info

    values = ", ".join(f"{name} = {getattr(module, name)!r}" for name in names)
    print_info(
        f"Not in developer_settings.py, using the defaults: {values}. To change them, copy the lines"
        " from pyapp/DONT_CHANGE/data/dev_settings_default.py."
    )


def validate(module: Optional[Union[ModuleType, SimpleNamespace]] = None) -> None:
    """Raise SettingsError listing every unusable setting."""
    s = module or settings()
    problems = list(_bootstrap_literal_problems())
    _note_defaults_once(s)

    def get(name: str, default: object = None) -> Any:
        return getattr(s, name, default)

    def need(name: str, ok: Callable[[Any], object], message: str):
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
        "github_actions",
        lambda v: isinstance(v, (list, tuple)) and all(name in APP_WORKFLOWS for name in v),
        "use a list of " + ", ".join(repr(name) for name in APP_WORKFLOWS),
    )
    need(
        "args_for_main_py",
        lambda v: isinstance(v, (list, tuple)) and all(isinstance(a, str) for a in v),
        "use a list of strings",
    )
    need(
        "main_script_path",
        lambda v: isinstance(v, str) and v.lower().endswith((".py", ".pyw")),
        'use the path of a Python file, relative to developer_settings.py, such as "..\\\\main.py"',
    )
    main_script = get("main_script_path")
    if isinstance(main_script, str) and main_script.lower().endswith((".py", ".pyw")):
        problem = _main_script_problem(main_script)
        if problem:
            problems.append(problem)
    need(
        "environment_for_main_py",
        lambda v: isinstance(v, dict) and all(isinstance(k, str) and k and isinstance(x, str) for k, x in v.items()),
        'use a dict of text values such as {"MY_SETTING": "1"}',
    )
    packages = get("packages")
    entries = parse_requirements(packages) if isinstance(packages, str) else packages
    if isinstance(entries, (list, tuple)):
        problems.extend(
            f'packages: {entry!r} is not a package requirement such as "numpy>=2" (options such as -r or -e are not supported).'
            for entry in entries
            if not (isinstance(entry, str) and REQUIREMENT_START.match(entry))
        )
    else:
        need("packages", lambda v: False, 'use a list such as ["requests", "numpy>=2"] or a triple-quoted block')
    for name in ("traceback_lines_before", "traceback_lines_after"):
        need(
            name,
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
    need(
        "tab_bar_color",
        lambda v: v is None or (isinstance(v, str) and re.fullmatch(r"#[0-9A-Fa-f]{6}", v)),
        'use a color like "#3B78FF" or None',
    )
    need(
        "stop_timeout_seconds",
        lambda v: _number(v) and math.isfinite(v) and v >= 0,
        "use 0 (stop immediately) or a finite number of seconds",
    )

    for name in SHORTCUT_NAME_SETTINGS:
        need(name, lambda v: v is None or (isinstance(v, str) and v.strip()), "use a non-empty text or None")
    for outcome in OUTCOMES:
        for prefix in ("close_after_", "open_log_file_after_"):
            need(prefix + outcome, lambda v: isinstance(v, bool), "use True or False")
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

    if problems:
        raise SettingsError(
            "Please fix developer_settings.py:\n  " + "\n  ".join(problems) + f'\n  File: "{DEV_SETTINGS_PATH}"'
        )


def edit_settings(changes: Mapping[str, object]) -> List[str]:
    """Set top-level settings in developer_settings.py to new values; return a readable diff.

    Only the value is replaced: annotations, trailing comments and line endings are kept.
    """
    diff: List[str] = []
    for name, value in changes.items():
        literal = _literal(value)
        diff += _replace_setting_value(name, lambda newline, node, literal=literal: literal)
    return diff


def set_list_setting(name: str, values: Iterable[str]) -> List[str]:
    """Rewrite the top-level list setting `name` (it may span several lines); return a readable diff.

    A setting written as a triple-quoted block stays one, so a pasted requirements list keeps its form.
    """
    values = list(values)

    def body(newline: str, node: Optional[Union[ast.Assign, ast.AnnAssign]]) -> str:
        was_block = node is not None and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str)
        # A block holds one entry per line, so entries with line breaks need the list form.
        if was_block and not any(c in v for v in values for c in ("\\", '"""', "\n", "\r")):
            return '"""' + newline + "".join(v + newline for v in values) + '"""'
        if not values:
            return "[]"
        return "[" + newline + "".join("    " + _quoted(v) + "," + newline for v in values) + "]"

    return _replace_setting_value(name, body)


def _replace_setting_value(
    name: str, make_value: Callable[[str, Optional[Union[ast.Assign, ast.AnnAssign]]], str]
) -> List[str]:
    """Replace the value of the last top-level assignment to `name` (the one Python uses).

    make_value(newline, node) returns the new value's source text (node: the current assignment or
    None). The file's line endings are kept.
    """
    with Path(DEV_SETTINGS_PATH).open(encoding="utf-8", newline="") as stream:
        source = stream.read()
    newline = "\r\n" if "\r\n" in source else "\n"
    # Split exactly where ast counts lines (str.splitlines also splits at e.g. U+2028).
    lines = re.findall(r"[^\r\n]*(?:\r\n|\r|\n)|[^\r\n]+$", source)
    node = None
    for item in ast.parse(source, DEV_SETTINGS_PATH).body:
        if name in _assigned_names(item):
            node = item
    if node is None:
        if name not in default_setting_expressions():
            raise SettingsError(f"Could not find the setting {name} in developer_settings.py to edit.")
        # A setting that only had its default (added by a newer launcher version): append it.
        addition = f"{name} = {make_value(newline, None)}{newline}"
        _write_settings_source(source + ("" if source.endswith(("\n", "\r")) else newline) + addition)
        sys.modules.pop("pyapp.developer_settings", None)
        return [f"+ {line}" for line in addition.rstrip().splitlines()]
    if not isinstance(node, (ast.Assign, ast.AnnAssign)) or node.value is None:
        raise SettingsError(f"The setting {name} has no editable assignment value.")
    # The value's own lines: with parentheses around it, they differ from the assignment's lines.
    first, last = node.value.lineno - 1, (node.value.end_lineno or node.value.lineno) - 1
    # ast offsets count UTF-8 bytes
    head = lines[first].encode("utf-8")[: node.value.col_offset].decode("utf-8")  # e.g. "packages: list[str] = "
    tail = lines[last].encode("utf-8")[node.value.end_col_offset :].decode("utf-8").rstrip("\r\n")  # e.g. a comment
    replacement = (head + make_value(newline, node) + tail).rstrip() + newline
    old = "".join(lines[first : last + 1])
    if replacement == old:
        return []
    lines[first : last + 1] = [replacement]
    _write_settings_source("".join(lines))
    sys.modules.pop("pyapp.developer_settings", None)
    return [f"- {line}" for line in old.rstrip().splitlines()] + [
        f"+ {line}" for line in replacement.rstrip().splitlines()
    ]


def _literal(value: object) -> str:
    """Python source text for a setting value."""
    if isinstance(value, str):
        return _quoted(value)
    # repr() of inf/nan is a bare name that would fail when the settings are imported.
    if isinstance(value, float) and not math.isfinite(value):
        raise SettingsError(f"Cannot write the value {value!r} into developer_settings.py.")
    if value is None or isinstance(value, (bool, int, float)):
        return repr(value)
    raise SettingsError(f"Cannot write the value {value!r} into developer_settings.py.")


_STRING_ESCAPES = {"\\": "\\\\", '"': '\\"', "\n": "\\n", "\r": "\\r", "\t": "\\t"}


def _quoted(value: str) -> str:
    """Double-quoted Python string literal (the style used in developer_settings.py).

    Other control characters and lone surrogates are escaped too: a raw line break would end the
    literal, and a surrogate cannot be written as UTF-8. Other text is kept readable.
    """

    def escape(character: str) -> str:
        if character in _STRING_ESCAPES:
            return _STRING_ESCAPES[character]
        code = ord(character)
        if code < 0x20 or code == 0x7F:
            return f"\\x{code:02x}"
        if 0xD800 <= code <= 0xDFFF:
            return f"\\u{code:04x}"
        return character

    return '"' + "".join(escape(character) for character in value) + '"'


def _write_settings_source(source: str) -> None:
    """Write developer_settings.py only if it is still valid Python, so a bad edit cannot break it."""
    try:
        ast.parse(source, DEV_SETTINGS_PATH)
    except SyntaxError as error:
        raise SettingsError(
            f"The edit would make developer_settings.py invalid ({error.msg}); nothing was changed."
        ) from error
    with Path(DEV_SETTINGS_PATH).open("w", encoding="utf-8", newline="") as stream:
        stream.write(source)


def describe_python_request(value: str) -> str:
    """Human-readable form of the python_version setting."""
    return f'"{value}"' if value else '"" (newest stable, chosen once)'


def display_path(path: str) -> str:
    """Shorten a path below the repository root for messages."""
    from pyapp.DONT_CHANGE.backend_settings import SHORTCUT_OUTPUT_DIR

    try:
        relative = os.path.relpath(path, SHORTCUT_OUTPUT_DIR)
    except ValueError:
        return path
    return path if relative.startswith("..") else relative
