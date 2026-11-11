"""Offline import finder: which PyPI packages does the application import?

1. Parse every .py file below the code folder (not pyapp/, .venv, caches) with ast.
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
from pathlib import Path
from typing import Dict, Iterator, List, NamedTuple, Optional, Set, Tuple

from pyapp.DONT_CHANGE.backend_settings import (
    BACKEND_DIR,
    EXCLUDED_FOLDERS_FOR_IMPORT_SEARCH,
    IMPORT_MAPPING_PATH,
    PYTHON_SCRIPTS_DIR,
    VENV_DIR,
)


class Requirement(NamedTuple):
    """A package the project imports.

    source: "installed" (from package metadata), "ambiguous" (one of several installed packages that
    provide the import name), "mapping" (bundled list) or "guess" (same as import name).
    """

    distribution: str
    imports: List[str]
    source: str
    files: List[str]
    optional: bool


def standard_library_names() -> Set[str]:
    """Top-level standard-library module names for the running Python."""
    names = set(sys.builtin_module_names) | {"__future__", "__main__"}
    if hasattr(sys, "stdlib_module_names"):  # Python 3.10+
        return names | set(sys.stdlib_module_names)
    paths = sysconfig.get_paths()
    folders = {paths.get("stdlib"), paths.get("platstdlib"), str(Path(sys.base_prefix) / "DLLs")}
    for folder in filter(None, folders):
        try:
            entries = [entry.name for entry in Path(folder).iterdir()]
        except OSError:
            continue
        for entry in entries:
            if entry in ("site-packages", "dist-packages", "__pycache__"):
                continue
            base = entry.split(".")[0]
            if entry.endswith((".py", ".pyd", ".pyc")) or (Path(folder) / entry).is_dir():
                names.add(base)
    return names


# The launcher (code/pyapp) is skipped only directly below the code folder.
LAUNCHER_FOLDER = Path(BACKEND_DIR).name


def _excluded(folder_name: str, parent: str = "") -> bool:
    if folder_name in EXCLUDED_FOLDERS_FOR_IMPORT_SEARCH or folder_name.startswith("."):
        return True
    # A virtual environment under any name (venv, env, ...): its packages are not the app's imports.
    return bool(parent) and (Path(parent) / folder_name / "pyvenv.cfg").is_file()


def python_files(root: str = PYTHON_SCRIPTS_DIR) -> Iterator[str]:
    root_key = os.path.normcase(os.path.normpath(str(Path(root).absolute())))
    for current, folders, files in os.walk(root):
        at_root = os.path.normcase(os.path.normpath(str(Path(current).absolute()))) == root_key
        folders[:] = [f for f in folders if not _excluded(f, current) and not (at_root and f == LAUNCHER_FOLDER)]
        for name in files:
            if name.endswith((".py", ".pyw")):
                yield str(Path(current) / name)


def local_module_names(root: str = PYTHON_SCRIPTS_DIR) -> Set[str]:
    """Names importable from the code folder itself and the main script's folder (sys.path[0])."""
    folders = {root}
    if root == PYTHON_SCRIPTS_DIR:
        from pyapp.DONT_CHANGE.scripts.config import main_script_path

        folders.add(str(Path(main_script_path()).parent))
    names = set()
    for folder in folders:
        for entry in Path(folder).iterdir():
            if entry.name.endswith((".py", ".pyw")):
                names.add(entry.name.rsplit(".", 1)[0])
            elif entry.is_dir() and entry.name.isidentifier() and not _excluded(entry.name) and _has_python(entry):
                names.add(entry.name)
    return names


def _has_python(folder: Path) -> bool:
    """A Python file anywhere below: a namespace package (no __init__.py) may hold them only in subfolders."""
    for _, subfolders, files in os.walk(str(folder)):
        if any(name.endswith(".py") for name in files):
            return True
        subfolders[:] = [name for name in subfolders if not _excluded(name)]
    return False


def _handler_names(handler: ast.ExceptHandler) -> List[str]:
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


def _only_imports(body: List[ast.stmt]) -> bool:
    """True for a try body that just imports (optionally setting simple flags like HAS_X = True)."""
    for statement in body:
        if isinstance(statement, (ast.Import, ast.ImportFrom, ast.Pass)):
            continue
        if isinstance(statement, (ast.Assign, ast.AnnAssign)) and isinstance(statement.value, ast.Constant):
            continue
        return False
    return True


def _is_import_error_guard(node: ast.Try) -> bool:
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
    def __init__(self) -> None:
        self.required = set()
        self.optional = set()
        self._guard = 0

    # typing.override requires Python 3.12; keep this override dependency-free on 3.8.
    def visit_Try(self, node: ast.Try) -> None:  # pyrefly: ignore[missing-override-decorator]
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

    def _add(self, name: Optional[str]) -> None:
        if name:
            (self.optional if self._guard else self.required).add(name.split(".")[0])

    # typing.override requires Python 3.12; keep this override dependency-free on 3.8.
    def visit_Import(self, node: ast.Import) -> None:  # pyrefly: ignore[missing-override-decorator]
        for alias in node.names:
            self._add(alias.name)

    # typing.override requires Python 3.12; keep this override dependency-free on 3.8.
    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:  # pyrefly: ignore[missing-override-decorator]
        if node.level == 0:
            self._add(node.module)


def imports_in_project(root: str = PYTHON_SCRIPTS_DIR) -> Tuple[Dict[str, Tuple[Set[str], bool]], List[str]]:
    """Return {import name: (files, optional)} for third-party candidates."""
    found = {}
    problems = []
    for path in python_files(root):
        try:
            with Path(path).open("rb") as stream:
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


def installed_import_map(site_packages: Optional[str] = None) -> Dict[str, str]:
    """{top-level import name: distribution} from installed metadata, for names exactly one distribution provides.

    A namespace (e.g. "google") shared by several distributions has no single answer; see
    installed_providers() and provider_of_module().
    """
    return {top: names[0] for top, names in installed_providers(site_packages).items() if len(names) == 1}


def _site_packages(site_packages: Optional[str]) -> str:
    return str(Path(VENV_DIR) / "Lib" / "site-packages") if site_packages is None else site_packages


def installed_providers(site_packages: Optional[str] = None) -> Dict[str, List[str]]:
    """{top-level import name: sorted distributions providing it} from metadata (top_level.txt or RECORD)."""
    from importlib import metadata

    site_packages = _site_packages(site_packages)
    result: Dict[str, Set[str]] = {}
    if not Path(site_packages).is_dir():
        return {}
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
            result.setdefault(top, set()).add(name)
    return {top: sorted(names) for top, names in result.items()}


def provider_of_module(import_name: str, site_packages: Optional[str] = None) -> Optional[str]:
    """The installed distribution whose files contain a dotted module, e.g. "google.cloud.storage"."""
    from importlib import metadata

    module = import_name.replace(".", "/")
    # A package folder ("google/cloud/storage/...") or a module file (".py", ".pyd", ".cp314-win_amd64.pyd").
    wanted = (module + "/", module + ".")
    for dist in metadata.distributions(path=[_site_packages(site_packages)]):
        if any("/".join(file.parts).startswith(wanted) for file in dist.files or []):
            return dist.metadata["Name"] or None
    return None


def bundled_mapping(path: str = IMPORT_MAPPING_PATH) -> Dict[str, str]:
    mapping = {}
    try:
        with Path(path).open(encoding="utf-8") as stream:
            for raw_line in stream:
                line = raw_line.strip()
                if line and not line.startswith("#") and ":" in line:
                    module, distribution = line.split(":", 1)
                    mapping[module.strip()] = distribution.strip()
    except OSError:
        pass
    return mapping


def find_requirements(
    root: str = PYTHON_SCRIPTS_DIR, site_packages: Optional[str] = None
) -> Tuple[List[Requirement], List[str]]:
    """Return (list of Requirement sorted by distribution, list of unparsable-file messages)."""
    imports, problems = imports_in_project(root)
    providers = installed_providers(site_packages)
    mapping = bundled_mapping()
    distributions: Dict[str, Tuple[str, str]] = {}  # lowercase name -> (distribution, source)
    import_names: Dict[str, Set[str]] = {}
    files_by_distribution: Dict[str, Set[str]] = {}
    all_optional: Dict[str, bool] = {}
    for name, (files, optional) in imports.items():
        if len(providers.get(name, [])) > 1:
            # Several installed packages share this name: offer each, and let the user choose.
            candidates = [(distribution, "ambiguous") for distribution in providers[name]]
        elif name in providers:
            candidates = [(providers[name][0], "installed")]
        elif name in mapping:
            candidates = [(mapping[name], "mapping")]
        else:
            candidates = [(name, "guess")]
        for distribution, source in candidates:
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


def distribution_for_import(import_name: str, site_packages: Optional[str] = None) -> str:
    """Best distribution name for one missing import (used by the missing-package menu)."""
    top = import_name.split(".", maxsplit=1)[0]
    providers = installed_providers(site_packages).get(top, [])
    if len(providers) > 1:
        # A shared namespace: only the distribution that contains this very module is the answer.
        return provider_of_module(import_name, site_packages) or top
    return (providers[0] if providers else None) or bundled_mapping().get(top) or top
