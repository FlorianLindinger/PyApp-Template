"""Dev tool list-packages: the app's packages, split into what you asked for and what they need.

The data comes from uv, so it is what the environment really gets: after the usual preparation
(developer_settings.py -> pyproject.toml -> uv.lock -> .venv, as every dev tool does),
"uv export --frozen" reads uv.lock without resolving anything; its "# via" notes say which
package needs which. "uv pip list" adds what is actually installed in .venv, so packages that
are missing, at another version or installed by hand show up too.
"""

from __future__ import annotations

import json
import re
from typing import Dict, FrozenSet, List, NamedTuple, Optional, Sequence, Set, Tuple

from pyapp.DONT_CHANGE import backend_settings as paths
from pyapp.DONT_CHANGE.scripts.config import (
    display_path,
    package_entries,
    requirement_key,
    requirements_file_entries,
    settings,
)
from pyapp.DONT_CHANGE.scripts.console_tools import (
    ANSI_BOLD,
    ANSI_DIM,
    ANSI_GOOD,
    print_fields,
    print_heading,
    print_info,
    print_success,
    print_warn,
    styled,
)
from pyapp.DONT_CHANGE.scripts.dev_tools.common import normalized, prepare
from pyapp.DONT_CHANGE.scripts.env.uv import run_uv_captured

# "requests==2.32.3 ; sys_platform == 'win32'" or "pkg @ https://..." (a direct reference).
_REQUIREMENT = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._-]*)(?:\[[^\]]*\])?\s*(?:==\s*([^\s;\\]+)|@\s*([^\s;\\]+))")


class Locked(NamedTuple):
    version: str  # the locked version, or the URL of a direct reference
    needed_by: List[str]  # normalized names; the project itself for a main package


def parse_export(text: str) -> Dict[str, Locked]:
    """{normalized name: Locked} from "uv export --format requirements-txt" with its "# via" notes.

    uv writes one requirer as "# via requests", several as "# via" followed by "#   name" lines.
    """
    packages: Dict[str, Locked] = {}
    current: Optional[str] = None
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if not line.startswith((" ", "\t", "#")):
            match = _REQUIREMENT.match(stripped)
            current = normalized(match.group(1)) if match else None
            if match and current:
                packages[current] = Locked(match.group(2) or match.group(3), [])
            continue
        if current is None or not stripped.startswith("#"):
            continue  # a continuation line ("--hash=...") or uv's header comment
        note = stripped[1:].strip()
        if note.startswith("via"):
            note = note[3:].strip()
        if note and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", note):
            packages[current].needed_by.append(normalized(note))
    return packages


def parse_installed(text: str) -> Dict[str, str]:
    """{normalized name: version} from "uv pip list --format json"."""
    try:
        rows = json.loads(text or "[]")
    except ValueError:
        return {}
    return {normalized(str(row["name"])): str(row["version"]) for row in rows if "name" in row and "version" in row}


def served_main_packages(name: str, locked: Dict[str, Locked], main: Set[str]) -> List[str]:
    """The main packages a dependency is (directly or further down) installed for."""
    found: Set[str] = set()
    seen: Set[str] = set()
    stack = [name]
    while stack:
        current = stack.pop()
        for parent in locked[current].needed_by if current in locked else []:
            if parent in seen:
                continue
            seen.add(parent)
            if parent in main:
                found.add(parent)
            elif parent in locked:
                stack.append(parent)
    return sorted(found)


def dependency_count(name: str, locked: Dict[str, Locked], main: Set[str]) -> int:
    """How many dependencies (not main packages themselves) a main package brings in, in total."""
    return sum(1 for other in locked if other not in main and name in served_main_packages(other, locked, main))


def _table(rows: Sequence[Sequence[str]], styles: Sequence[str] = ()) -> None:
    """Left-aligned columns as wide as their content; styles[i] colors column i."""
    if not rows:
        return
    widths = [max(len(row[i]) for row in rows) for i in range(len(rows[0]))]
    for row in rows:
        cells = []
        for index, cell in enumerate(row):
            text = cell.ljust(widths[index]) if index < len(row) - 1 else cell
            style = styles[index] if index < len(styles) else ""
            cells.append(styled(text, style) if style and cell.strip() else text)
        print("    " + "  ".join(cells).rstrip())


def _limit(requirement: str) -> str:
    """The version limit of a requirement: "numpy>=2,<3 ; python_version<'3.12'" -> ">=2,<3"."""
    rest = re.sub(r"^\s*[A-Za-z0-9][A-Za-z0-9._-]*(?:\[[^\]]*\])?", "", requirement).split(";")[0].strip()
    return "(direct link)" if rest.startswith("@") else rest


def _shown_version(version: str) -> str:
    """A direct reference (a URL or path) would make the version column as wide as the link."""
    return "(link)" if "/" in version or "\\" in version else version


def _version_note(name: str, locked: Dict[str, Locked], installed: Dict[str, str]) -> str:
    """ "" when .venv has the locked version, else what is wrong."""
    if name not in installed:
        return "not installed (run sync_packages)"
    version = locked[name].version
    if "/" not in version and installed[name] != version:
        return f"installed: {installed[name]} (run sync_packages)"
    return ""


class Extras(NamedTuple):
    """What the report can add: unused main packages, and newer versions (only with --outdated)."""

    unused: FrozenSet[str]  # main packages whose imports no file of the code folder uses
    newest: Optional[Dict[str, str]]  # {name: newest version on PyPI}; None: not checked
    allowed: Dict[str, str]  # {name: version an upgrade within the limits would install}


def parse_outdated(text: str) -> Dict[str, str]:
    """{normalized name: newest version} from "uv pip list --outdated --format json"."""
    try:
        rows = json.loads(text or "[]")
    except ValueError:
        return {}
    return {normalized(str(row["name"])): str(row["latest_version"]) for row in rows if "latest_version" in row}


def parse_upgrades(text: str) -> Dict[str, str]:
    """{normalized name: new version} from "uv lock --upgrade --dry-run" ("Update idna v3.4 -> v3.20")."""
    return {
        normalized(name): new for name, new in re.findall(r"^Update (\S+) v\S+ -> v(\S+)", text, flags=re.MULTILINE)
    }


def unused_packages(main: Set[str], providers: Dict[str, List[str]], imported: Set[str]) -> Set[str]:
    """Main packages that provide import names, none of which the code imports.

    providers = {import name: distributions} of the installed packages; a package whose import
    names are unknown (not installed) is not judged.
    """
    imports: Dict[str, Set[str]] = {}
    for import_name, distributions in providers.items():
        for distribution in distributions:
            imports.setdefault(normalized(distribution), set()).add(import_name)
    return {name for name in main if name in imports and not imports[name] & imported}


def _update_note(name: str, extras: Extras) -> str:
    """What an upgrade would bring ("" if the package is current or was not checked)."""
    if extras.newest is None or name not in extras.newest:
        return ""
    newest = extras.newest[name]
    if name in extras.allowed:
        note = f"update: {extras.allowed[name]} (upgrade_packages)"
        return note if extras.allowed[name] == newest else f"{note}, newest {newest} needs other limits"
    return f"newest {newest}, held back by the limits"


def show(
    declared: Sequence[Tuple[str, str]],
    locked: Dict[str, Locked],
    installed: Optional[Dict[str, str]],
    extras: Optional[Extras] = None,
) -> int:
    """Print the report; declared = (requirement, where it is written). Returns the number of problems."""
    main = {requirement_key(requirement) for requirement, _ in declared}
    problems = 0
    extras = extras or Extras(frozenset(), None, {})

    print_heading(f"Main packages ({len(declared)})")
    print_info("  What the app asks for: packages in developer_settings.py (and requirements_path).")
    rows: List[List[str]] = []
    for requirement, source in declared:
        name = requirement_key(requirement)
        limit = _limit(requirement)
        if name not in locked:
            rows.append([name, limit, "-", "not in uv.lock yet: start the app or run sync_packages"])
            problems += 1
            continue
        count = dependency_count(name, locked, main)
        notes = [f"+ {count} dependenc{'y' if count == 1 else 'ies'}" if count else "no dependencies"]
        if source != "packages":
            notes.append(f"from {source}")
        other_main = [parent for parent in locked[name].needed_by if parent in main]
        if other_main:
            notes.append("also needed by " + ", ".join(other_main))
        if installed is not None and _version_note(name, locked, installed):
            notes.append(_version_note(name, locked, installed))
            problems += 1
        if name in extras.unused:
            notes.append("not imported in code/ (still needed, e.g. as a tool or plugin?)")
        if _update_note(name, extras):
            notes.append(_update_note(name, extras))
        rows.append([name, limit, _shown_version(locked[name].version), "  ".join(notes)])
    if rows:
        _table([["package", "limit", "version", ""], *rows], ["", ANSI_DIM, ANSI_GOOD, ANSI_DIM])
    else:
        print_info("    none: add some with add_packages, or in packages of developer_settings.py")

    dependencies = sorted(name for name in locked if name not in main)
    print_heading(f"Dependencies ({len(dependencies)})")
    print_info("  Installed because a main package needs them; uv adds and removes them by itself.")
    rows = []
    for name in dependencies:
        direct = locked[name].needed_by
        served = served_main_packages(name, locked, main)
        needed = ", ".join(direct)
        if served and set(served) != set(direct):
            needed += f"  (for {', '.join(served)})"
        note = _version_note(name, locked, installed) if installed is not None else ""
        problems += bool(note)
        note = "  ".join(part for part in (note, _update_note(name, extras)) if part)
        rows.append([name, _shown_version(locked[name].version), "needed by " + needed if needed else "", note])
    if rows:
        _table(rows, ["", ANSI_GOOD, ANSI_DIM, ANSI_BOLD + "\x1b[33m"])
    else:
        print_info("    none")

    extra = sorted(set(installed or {}) - set(locked))
    if extra:
        print_heading(f"Installed by hand ({len(extra)})")
        print_info("  In .venv, but not in uv.lock (e.g. uv pip install): sync_packages removes them.")
        _table([[name, (installed or {})[name]] for name in extra], ["", ANSI_GOOD])
    return problems


def read_extras(main: Set[str], outdated: bool) -> Tuple[Extras, str]:
    """Unused main packages (offline), and newer versions if asked (online); plus a problem note."""
    from pyapp.DONT_CHANGE.scripts.import_finder import imports_in_project, installed_providers

    imported, _ = imports_in_project()
    unused = frozenset(unused_packages(main, installed_providers(), set(imported)))
    if not outdated:
        return Extras(unused, None, {}), ""
    code, listed, _ = run_uv_captured(
        ["pip", "list", "--outdated", "--format", "json", "--python", paths.VENV_PYTHON_EXE], check=False
    )
    if code:
        return Extras(unused, None, {}), "Newer versions could not be checked (no internet?)."
    # What upgrade_packages would install: a resolution within the limits that writes nothing.
    _, out, err = run_uv_captured(["lock", "--upgrade", "--dry-run"], check=False)
    return Extras(unused, parse_outdated(listed), parse_upgrades(out + "\n" + err)), ""


def cmd_list_packages(arguments: List[str]) -> None:
    """Show the main packages, their dependencies, and anything not as uv.lock says.

    --outdated also asks PyPI for newer versions (needs internet).
    """
    s = settings()
    app_python = prepare(s)  # also brings pyproject.toml, uv.lock and .venv up to date
    declared = [(requirement, "packages") for requirement in package_entries(s)]
    declared += [(requirement, "requirements_path") for requirement in requirements_file_entries(s)]
    _, exported, _ = run_uv_captured(
        ["export", "--frozen", "--format", "requirements-txt", "--no-hashes", "--no-emit-project"]
    )
    locked = parse_export(exported)
    code, listed, _ = run_uv_captured(
        ["pip", "list", "--format", "json", "--python", paths.VENV_PYTHON_EXE], check=False
    )
    installed = parse_installed(listed) if code == 0 else None
    extras, extras_problem = read_extras({requirement_key(r) for r, _ in declared}, "--outdated" in arguments)

    print_heading("Packages")
    print_fields(
        [
            ("Environment", display_path(paths.VENV_DIR)),
            ("Python", display_path(app_python.exe)),
            ("Lock file", display_path(paths.UV_LOCK_PATH)),
        ]
    )
    problems = show(declared, locked, installed, extras)
    print()
    if extras_problem:
        print_warn(extras_problem)
    if extras.newest is not None:
        newer = sorted(set(extras.newest) & set(locked))
        allowed = sorted(set(extras.allowed) & set(locked))
        print_info(
            f"{len(newer)} package(s) have newer versions; upgrade_packages installs the {len(allowed)} the limits allow."
            if newer
            else "Every package is at its newest version."
        )
    elif not extras_problem:
        print_info("list_packages.cmd --outdated (or outdated_packages.cmd) also shows newer versions.")
    if installed is None:
        print_warn("The installed packages could not be read; only uv.lock is shown.")
    elif problems:
        print_warn("Some packages are not as uv.lock says; sync_packages installs exactly what it lists.")
    elif set(installed) - set(locked):
        extra = len(set(installed) - set(locked))
        print_success(
            f"{len(locked)} package(s) installed as uv.lock says, and {extra} more installed by hand.\n"
            "sync_packages removes those; add_packages records one for good."
        )
    else:
        print_success(f"{len(locked)} package(s) installed, exactly as uv.lock says.")
