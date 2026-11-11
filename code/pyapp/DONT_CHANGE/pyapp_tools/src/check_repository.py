"""Check the Git repository for problems that break clones, other PCs or Windows.

    check_repository.bat               all checks
    check_repository.bat --max-mb 10   report files larger than 10 MB (default 5)
    check_repository.bat --why PATH    which .gitignore rule decides PATH (also explains exceptions)
    check_repository.bat --ignored     the ignored files and folders, largest first (what stays local)

Finds tracked files that .gitignore says to ignore, "!" exceptions in .gitignore files that do not
take effect, files with mixed line endings, paths that differ only in letter case, names Windows
cannot use, paths too long for Windows, oversized files, tracked caches and environments, and
nested Git repositories. Secrets and personal data are check_git_leaks.bat's job.

Exit code 1 means problems were found. Everything is read-only.
"""

from __future__ import annotations

import argparse
import contextlib
import os
import subprocess
from pathlib import Path
from typing import Dict, Iterable, List, NamedTuple, Optional, Tuple

import _ui
from _paths import PROJECT_ROOT

# Windows refuses these names with any extension (CON.txt too), in any letter case.
RESERVED_NAMES = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}
FORBIDDEN_CHARACTERS = set('<>:"|?*')
# MAX_PATH is 260 characters including the drive and the end; leave room for a deeper clone folder.
LONG_PATH = 240
# Folders and files that are generated on each PC and should never be tracked.
GENERATED_PARTS = {"__pycache__", ".venv", "venv", "site-packages", "node_modules", ".ruff_cache", ".pytest_cache"}
GENERATED_SUFFIXES = (".pyc", ".pyo")
MAX_SHOWN = 15


class Problem(NamedTuple):
    check: str
    detail: str


def git(*arguments: str, stdin: Optional[str] = None, root: Path = PROJECT_ROOT) -> str:
    """Output of a git command; "" when it fails. Bytes in and out, so Windows adds no CR."""
    # Fixed Git commands in the project folder.
    completed = subprocess.run(  # noqa: S603
        ["git", "-C", str(root), "-c", "core.quotepath=off", *arguments],  # noqa: S607
        input=None if stdin is None else stdin.encode("utf-8"),
        capture_output=True,
        check=False,
    )
    return completed.stdout.decode("utf-8", "replace") if completed.returncode in (0, 1) else ""


def tracked_files(root: Path = PROJECT_ROOT) -> List[str]:
    return [name for name in git("ls-files", "-z", root=root).split("\0") if name]


def tracked_but_ignored(root: Path = PROJECT_ROOT) -> List[Problem]:
    """Tracked files that an ignore rule matches: a fresh clone has them, but new changes are easy to miss."""
    names = git("ls-files", "-z", "--cached", "--ignored", "--exclude-standard", root=root).split("\0")
    return [Problem("Tracked but ignored", name) for name in names if name]


def broken_exceptions(root: Path = PROJECT_ROOT) -> List[Problem]:
    """Files that a "!" line in a .gitignore is meant to keep, but that Git still ignores.

    Usually the folder above is excluded (e.g. "folder/" instead of "folder/*"), and Git never
    looks inside an excluded folder, so the exception cannot apply.
    """
    candidates: Dict[str, str] = {}
    for gitignore in [
        root / ".gitignore",
        *(root / name for name in tracked_files(root) if name.endswith("/.gitignore")),
    ]:
        if not gitignore.is_file():
            continue
        base = gitignore.parent
        for line in gitignore.read_text(encoding="utf-8", errors="replace").splitlines():
            pattern = line.strip()
            if not pattern.startswith("!") or pattern.startswith("!#"):
                continue
            pattern = pattern[1:].strip().lstrip("/")
            if not pattern or "**" in pattern:
                continue
            for path in base.glob(pattern.rstrip("/")):
                if path.is_file():
                    relative = path.relative_to(root).as_posix()
                    candidates[relative] = (
                        f"{relative} (kept by {gitignore.relative_to(root).as_posix()}: {line.strip()})"
                    )
    if not candidates:
        return []
    ignored = git("check-ignore", "--stdin", stdin="\n".join(candidates) + "\n", root=root).splitlines()
    return [Problem("Exception without effect", candidates[name]) for name in ignored if name in candidates]


def mixed_line_endings(root: Path = PROJECT_ROOT, names: Optional[Iterable[str]] = None) -> List[Problem]:
    """Text files with both CRLF and bare LF line ends, which Git and editors handle inconsistently."""
    problems: List[Problem] = []
    for name in tracked_files(root) if names is None else names:
        path = root / name
        try:
            data = path.read_bytes()
        except OSError:
            continue
        if b"\0" in data[:8000]:
            continue  # binary
        crlf = data.count(b"\r\n")
        bare_lf = data.count(b"\n") - crlf
        if crlf and bare_lf:
            problems.append(Problem("Mixed line endings", f"{name} ({crlf} CRLF, {bare_lf} LF)"))
    return problems


def case_conflicts(names: Iterable[str]) -> List[Problem]:
    """Paths that differ only in letter case: on Windows only one of them can exist."""
    by_lower: Dict[str, List[str]] = {}
    for name in names:
        by_lower.setdefault(name.lower(), []).append(name)
    return [Problem("Case-only difference", " / ".join(group)) for group in by_lower.values() if len(group) > 1]


def windows_unsafe(names: Iterable[str], root: Path = PROJECT_ROOT) -> List[Problem]:
    """Names Windows cannot create, and paths too long for programs without long-path support."""
    problems: List[Problem] = []
    for name in names:
        for part in name.split("/"):
            if part.split(".")[0].upper() in RESERVED_NAMES:
                problems.append(Problem("Reserved Windows name", name))
            elif FORBIDDEN_CHARACTERS & set(part) or any(ord(c) < 32 for c in part):
                problems.append(Problem("Character Windows forbids", name))
            elif part.endswith((".", " ")):
                problems.append(Problem("Ends with a dot or space", name))
            else:
                continue
            break
        length = len(str(root / name))
        if length > LONG_PATH:
            problems.append(Problem("Long path", f"{name} ({length} characters here)"))
    return problems


def oversized(names: Iterable[str], max_mb: float, root: Path = PROJECT_ROOT) -> List[Problem]:
    problems: List[Problem] = []
    for name in names:
        try:
            size = (root / name).stat().st_size
        except OSError:
            continue
        if size > max_mb * 1_048_576:
            problems.append(Problem("Large file", f"{name} ({size / 1_048_576:.1f} MB)"))
    return problems


def generated_tracked(names: Iterable[str]) -> List[Problem]:
    """Caches and environments that belong in .gitignore, not in the repository."""
    return [
        Problem("Generated file tracked", name)
        for name in names
        if GENERATED_PARTS.intersection(name.split("/")) or name.endswith(GENERATED_SUFFIXES)
    ]


def nested_repositories(root: Path = PROJECT_ROOT) -> List[Problem]:
    """Git folders inside the project: their files are not part of this repository's clones."""
    # Folders Git ignores (e.g. a cache with Git sources in it) never reach a clone: not a problem.
    ignored = {
        name.rstrip("/")
        for name in git(
            "ls-files", "-z", "--others", "--ignored", "--exclude-standard", "--directory", root=root
        ).split("\0")
        if name.endswith("/")
    }
    problems: List[Problem] = []
    for folder, folders, files in os.walk(str(root)):
        current = Path(folder)
        relative = "" if current == root else current.relative_to(root).as_posix()
        if relative and (".git" in folders or ".git" in files):
            problems.append(Problem("Nested Git repository", relative))
            folders[:] = []  # its contents belong to that repository
            continue
        folders[:] = [
            name
            for name in folders
            if name != ".git" and name not in GENERATED_PARTS and f"{relative}/{name}".lstrip("/") not in ignored
        ]
    return problems


def all_problems(root: Path, max_mb: float) -> List[Problem]:
    names = tracked_files(root)
    return [
        *tracked_but_ignored(root),
        *broken_exceptions(root),
        *mixed_line_endings(root, names),
        *case_conflicts(names),
        *windows_unsafe(names, root),
        *oversized(names, max_mb, root),
        *generated_tracked(names),
        *nested_repositories(root),
    ]


def show(problems: List[Problem]) -> None:
    by_check: Dict[str, List[str]] = {}
    for problem in problems:
        by_check.setdefault(problem.check, []).append(problem.detail)
    for check, details in by_check.items():
        _ui.heading(f"{check} ({len(details)})")
        for detail in details[:MAX_SHOWN]:
            _ui.info("  " + detail)
        if len(details) > MAX_SHOWN:
            _ui.info(f"  ... and {len(details) - MAX_SHOWN} more.")


def why_ignored(paths: Iterable[str], root: Path = PROJECT_ROOT) -> List[Tuple[str, str]]:
    """(path, the ignore rule that decides it) for each path; "" when no rule ignores it.

    A rule starting with "!" is an exception: Git keeps that path although an earlier rule matched.
    """
    answers: List[Tuple[str, str]] = []
    for path in paths:
        # --no-index: also explain tracked files, which Git otherwise never reports as ignored.
        line = git("check-ignore", "-v", "--no-index", "--", path, root=root).strip()
        source, _, matched = line.partition("\t")
        answers.append((path, source if matched else ""))
    return answers


def folder_size(path: Path) -> int:
    if path.is_file():
        return path.stat().st_size
    total = 0
    for folder, _, files in os.walk(str(path)):
        for name in files:
            with contextlib.suppress(OSError):  # e.g. removed meanwhile
                total += (Path(folder) / name).stat().st_size
    return total


def ignored_entries(root: Path = PROJECT_ROOT) -> List[Tuple[str, int, int]]:
    """(folder or file, size, number of files) of everything ignored that exists here, largest first.

    Git names a fully ignored folder once, but each ignored file of a partly tracked folder (e.g.
    logs/ with its tracked .gitkeep); those files are added up per folder.
    """
    names = git("ls-files", "-z", "--others", "--ignored", "--exclude-standard", "--directory", root=root).split("\0")
    groups: Dict[str, List[int]] = {}
    for name in filter(None, names):
        path = root / name
        key = name if name.endswith("/") or "/" not in name else name.rsplit("/", 1)[0] + "/"
        size, count = (
            (folder_size(path), sum(len(files) for _, _, files in os.walk(str(path))))
            if path.is_dir()
            else (
                folder_size(path),
                1,
            )
        )
        group = groups.setdefault(key, [0, 0])
        group[0] += size
        group[1] += count
    return sorted(
        ((key, size, count) for key, (size, count) in groups.items()), key=lambda entry: entry[1], reverse=True
    )


def readable_size(size: int) -> str:
    return f"{size / 1_048_576:.1f} MB" if size >= 1_048_576 else f"{size / 1024:.0f} KB"


def show_why(paths: List[str]) -> int:
    _ui.heading("Why ignored")
    for path, rule in why_ignored(paths):
        if not rule:
            _ui.info(f"  {path}: not ignored")
        elif rule.split(":", 2)[-1].startswith("!"):
            _ui.info(f"  {path}: kept by the exception {rule}")
        else:
            _ui.info(f"  {path}: ignored by {rule}")
    _ui.info("  (rule format: file:line:pattern)")
    return 0


def show_ignored() -> int:
    entries = ignored_entries()
    shown = 20
    _ui.heading("Ignored files and folders, largest first")
    _ui.table(("size", "files", "path"), [(readable_size(size), count, name) for name, size, count in entries[:shown]])
    if len(entries) > shown:
        _ui.info(f"  ... and {len(entries) - shown} smaller ones.")
    _ui.blank_line()
    total = sum(size for _, size, _ in entries)
    _ui.info(f"Total: {readable_size(total)} that stays on this PC and is not in Git.")
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--max-mb", type=float, default=5.0, help="report tracked files larger than this (default 5)")
    parser.add_argument("--why", nargs="+", metavar="PATH", help="show which ignore rule decides these paths")
    parser.add_argument("--ignored", action="store_true", help="list the ignored files and folders by size")
    arguments = parser.parse_args(argv)
    _ui.heading("Check the repository")
    _ui.fields([("Repository", PROJECT_ROOT)])
    if not (PROJECT_ROOT / ".git").exists():
        _ui.error("This project is not a Git repository.")
        return 2
    if arguments.why:
        return show_why(arguments.why)
    if arguments.ignored:
        return show_ignored()
    problems = all_problems(PROJECT_ROOT, arguments.max_mb)
    show(problems)
    _ui.blank_line()
    if problems:
        _ui.error(f"{len(problems)} problem(s) found. See above.")
        return 1
    _ui.success("No problems found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(_ui.run(main))
