"""Offline import finder: which PyPI packages does the application import?

1. Parse every .py file below the code folder (not backend/, .venv, caches) with ast.
2. Drop standard-library modules (for the running Python version) and local modules.
3. Map import names to distributions: installed packages' metadata first (exact),
   then the bundled mapping file (data/import_to_package.txt), else the import name itself.

Like any static finder it cannot see dynamic imports (importlib.import_module("x")).
Imports inside try/except ImportError are reported as optional.
"""

from __future__ import annotations

import ast
import os
import sys
import sysconfig
from collections import namedtuple

from backend.DONT_CHANGE.backend_settings import (
    BACKEND_DIR,
    EXCLUDED_FOLDERS_FOR_IMPORT_SEARCH,
    IMPORT_MAPPING_PATH,
    PYTHON_SCRIPTS_DIR,
    VENV_DIR,
)

Requirement = namedtuple("Requirement", "distribution imports source files optional")
"""source: "installed" (from package metadata), "mapping" (bundled list) or "guess" (same as import name)."""


def standard_library_names() -> set:
    """Top-level standard-library module names for the running Python."""
    names = set(sys.builtin_module_names) | {"__future__", "__main__"}
    if hasattr(sys, "stdlib_module_names"):  # Python 3.10+
        return names | set(sys.stdlib_module_names)
    paths = sysconfig.get_paths()
    folders = {paths.get("stdlib"), paths.get("platstdlib"), os.path.join(sys.base_prefix, "DLLs")}
    for folder in filter(None, folders):
        try:
            entries = os.listdir(folder)
        except OSError:
            continue
        for entry in entries:
            if entry in ("site-packages", "dist-packages", "__pycache__"):
                continue
            base = entry.split(".")[0]
            if entry.endswith((".py", ".pyd", ".pyc")) or os.path.isdir(os.path.join(folder, entry)):
                names.add(base)
    return names


# The launcher (code/backend) is skipped only directly below the code folder.
LAUNCHER_FOLDER = os.path.basename(BACKEND_DIR)


def _excluded(folder_name: str) -> bool:
    return folder_name in EXCLUDED_FOLDERS_FOR_IMPORT_SEARCH or folder_name.startswith(".")


def python_files(root: str = PYTHON_SCRIPTS_DIR):
    root_key = os.path.normcase(os.path.abspath(root))
    for current, folders, files in os.walk(root):
        at_root = os.path.normcase(os.path.abspath(current)) == root_key
        folders[:] = [f for f in folders if not _excluded(f) and not (at_root and f == LAUNCHER_FOLDER)]
        for name in files:
            if name.endswith((".py", ".pyw")):
                yield os.path.join(current, name)


def local_module_names(root: str = PYTHON_SCRIPTS_DIR) -> set:
    """Names importable from the code folder itself and the main script's folder (sys.path[0])."""
    folders = {root}
    if root == PYTHON_SCRIPTS_DIR:
        from backend.DONT_CHANGE.scripts.config import main_script_path

        folders.add(os.path.dirname(main_script_path()))
    names = set()
    for folder in folders:
        for entry in os.listdir(folder):
            path = os.path.join(folder, entry)
            if entry.endswith((".py", ".pyw")):
                names.add(entry.rsplit(".", 1)[0])
            elif os.path.isdir(path) and not _excluded(entry) and any(f.endswith(".py") for f in os.listdir(path)):
                names.add(entry)
    return names


def _handler_names(handler: ast.ExceptHandler) -> list:
    """Exception class names an except clause catches ([] for a bare "except:")."""
    if handler.type is None:
        return []
    nodes = handler.type.elts if isinstance(handler.type, ast.Tuple) else [handler.type]
    names = []
    for node in nodes:
        if isinstance(node, ast.Name):
            names.append(node.id)
        elif isinstance(node, ast.Attribute):
            names.append(node.attr)
    return names


def _only_imports(body) -> bool:
    """True for a try body that just imports (optionally setting simple flags like HAS_X = True)."""
    for statement in body:
        if isinstance(statement, (ast.Import, ast.ImportFrom, ast.Pass)):
            continue
        if isinstance(statement, (ast.Assign, ast.AnnAssign)) and isinstance(statement.value, ast.Constant):
            continue
        return False
    return True


def _is_import_error_guard(node) -> bool:
    """Is this try statement an optional-import guard?

    "except ImportError/ModuleNotFoundError" always is. A broad "except:", "except Exception" or
    "except BaseException" only counts when the try body does nothing but import, so code that
    wraps a whole program in try/except still has its imports reported as required.
    """
    broad_only_imports = None
    for handler in node.handlers:
        names = _handler_names(handler)
        if any(n in ("ImportError", "ModuleNotFoundError") for n in names):
            return True
        if not names or any(n in ("Exception", "BaseException") for n in names):
            if broad_only_imports is None:
                broad_only_imports = _only_imports(node.body)
            if broad_only_imports:
                return True
    return False


class _ImportVisitor(ast.NodeVisitor):
    def __init__(self):
        self.required = set()
        self.optional = set()
        self._guard = 0

    def visit_Try(self, node):
        guarded = _is_import_error_guard(node)
        if guarded:
            self._guard += 1
        for child in node.body:
            self.visit(child)
        if guarded:
            self._guard -= 1
        for child in node.handlers + node.orelse + node.finalbody:
            self.visit(child)

    visit_TryStar = visit_Try  # Python 3.11+ "except*"

    def _add(self, name):
        if name:
            (self.optional if self._guard else self.required).add(name.split(".")[0])

    def visit_Import(self, node):
        for alias in node.names:
            self._add(alias.name)

    def visit_ImportFrom(self, node):
        if node.level == 0:
            self._add(node.module)


def imports_in_project(root: str = PYTHON_SCRIPTS_DIR):
    """Return {import name: (files, optional)} for third-party candidates."""
    found = {}
    problems = []
    for path in python_files(root):
        try:
            with open(path, "rb") as stream:
                tree = ast.parse(stream.read(), path)
        except (SyntaxError, ValueError, OSError) as error:
            problems.append(f"{os.path.relpath(path, root)}: {error}")
            continue
        visitor = _ImportVisitor()
        visitor.visit(tree)
        for name in visitor.required | visitor.optional:
            files, optional = found.get(name, (set(), True))
            files.add(os.path.relpath(path, root))
            found[name] = (files, optional and name not in visitor.required)
    excluded = standard_library_names() | local_module_names(root)
    return {name: value for name, value in found.items() if name not in excluded}, problems


def installed_import_map(site_packages: str | None = None) -> dict:
    """{top-level import name: distribution} from installed metadata (top_level.txt or RECORD)."""
    from importlib import metadata

    if site_packages is None:
        site_packages = os.path.join(VENV_DIR, "Lib", "site-packages")
    result = {}
    if not os.path.isdir(site_packages):
        return result
    for dist in metadata.distributions(path=[site_packages]):
        name = dist.metadata["Name"]
        if not name:
            continue
        tops = (dist.read_text("top_level.txt") or "").split()
        if not tops:
            for file in dist.files or []:
                first = file.parts[0] if file.parts else ""
                if (
                    not first
                    or first.endswith((".dist-info", ".egg-info", ".data"))
                    or first in ("..", "__pycache__", "bin", "Scripts")
                ):
                    continue
                tops.append(first[:-3] if first.endswith(".py") else first.split(".")[0])
        for top in tops:
            result.setdefault(top, name)
    return result


def bundled_mapping(path: str = IMPORT_MAPPING_PATH) -> dict:
    mapping = {}
    try:
        with open(path, encoding="utf-8") as stream:
            for line in stream:
                line = line.strip()
                if line and not line.startswith("#") and ":" in line:
                    module, distribution = line.split(":", 1)
                    mapping[module.strip()] = distribution.strip()
    except OSError:
        pass
    return mapping


def find_requirements(root: str = PYTHON_SCRIPTS_DIR, site_packages: str | None = None):
    """Return (list of Requirement sorted by distribution, list of unparsable-file messages)."""
    imports, problems = imports_in_project(root)
    installed = installed_import_map(site_packages)
    mapping = bundled_mapping()
    distributions: dict[str, tuple[str, str]] = {}  # lowercase name -> (distribution, source)
    import_names: dict[str, set[str]] = {}
    files_by_distribution: dict[str, set[str]] = {}
    all_optional: dict[str, bool] = {}
    for name, (files, optional) in imports.items():
        if name in installed:
            distribution, source = installed[name], "installed"
        elif name in mapping:
            distribution, source = mapping[name], "mapping"
        else:
            distribution, source = name, "guess"
        key = distribution.lower()
        distributions.setdefault(key, (distribution, source))
        import_names.setdefault(key, set()).add(name)
        files_by_distribution.setdefault(key, set()).update(files)
        all_optional[key] = all_optional.get(key, True) and optional
    requirements = [
        Requirement(
            distribution, sorted(import_names[key]), source, sorted(files_by_distribution[key]), all_optional[key]
        )
        for key, (distribution, source) in distributions.items()
    ]
    return sorted(requirements, key=lambda r: r.distribution.lower()), problems


def distribution_for_import(import_name: str, site_packages: str | None = None) -> str:
    """Best distribution name for one missing import (used by the missing-package menu)."""
    top = import_name.split(".")[0]
    return installed_import_map(site_packages).get(top) or bundled_mapping().get(top) or top
