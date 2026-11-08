"""Look for secrets and personal data in this Git repository, before it gets published.

Scans the files Git would publish (tracked, and new ones that are not ignored) and every commit,
because something deleted later is still readable in the history. Secrets are masked in the output.

    check_git_leaks.bat                current files and the whole history
    check_git_leaks.bat --no-history   current files only

Exit code 1 means secrets were found. Personal data (home folder paths, email addresses, machine
files) is listed as a warning. Put "leak-check: ignore" on a line to accept it. This finds common
token formats and obvious credentials; it cannot prove that a repository is clean.
"""

from __future__ import annotations

import argparse
import fnmatch
import re
import subprocess
from pathlib import Path
from typing import Dict, Iterable, List, NamedTuple, Optional, Set, Tuple

import _ui
from _paths import PROJECT_ROOT

SECRET = "secret"  # noqa: S105 - a category name
PERSONAL = "personal"
IGNORE_MARKER = "leak-check: ignore"
MAX_FILE_BYTES = 5_000_000
MAX_ROWS = 40

SECRET_PATTERNS = (
    ("Private key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("AWS access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b|\bgithub_pat_[A-Za-z0-9_]{22,}")),
    ("GitLab token", re.compile(r"\bglpat-[A-Za-z0-9_-]{20,}")),
    ("Slack token", re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}")),
    ("Slack webhook", re.compile(r"hooks\.slack\.com/services/[A-Za-z0-9/]{20,}")),
    ("Stripe key", re.compile(r"\b[sr]k_live_[A-Za-z0-9]{16,}")),
    ("Google API key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b")),
    ("Anthropic key", re.compile(r"\bsk-ant-[A-Za-z0-9_-]{20,}")),
    ("OpenAI key", re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{32,}")),
    ("PyPI token", re.compile(r"\bpypi-AgEIcHlwaS5vcmc[A-Za-z0-9_-]{30,}")),
    ("Password in URL", re.compile(r"\b[a-z][a-z0-9+.-]*://[^/\s:@'\"]+:([^/\s:@'\"]{3,})@")),
    (
        "Hard-coded credential",
        re.compile(
            r"(?i)\b(?:password|passwd|pwd|secret|api[_-]?key|access[_-]?token|auth[_-]?token)\b"
            r"\s*[:=]\s*[\"']([^\"'\s]{8,})[\"']"
        ),
    ),
)
# The whole value must look like a placeholder: "SuperSecret123" is a real password.
PLACEHOLDER = re.compile(
    r"(?i)^(?:[{<$%].*|your[-\w]*|.*example.*|changeme|placeholder|(?:my)?(?:password|secret)|x{4,}|\*{3,}|\.\.\..*)$"
)

HOME_FOLDER = re.compile(r"(?i)\b[A-Z]:[\\/]+Users[\\/]+([^\\/\s\"'<>|:*?`]+)|(?<![\w.])/home/([a-z_][\w.-]*)")
PLACEHOLDER_USERS = {"public", "default", "all users", "name", "user", "username", "you", "yourname", "me", "runner"}
# Not after ":" or "/" (the password of a URL), and not ending like a file name.
EMAIL = re.compile(
    r"(?<![:/\w.+-])[\w.+-]+@[\w-]+(?:\.[\w-]+)*\.(?!(?:json|py|txt|toml|lock|md|js|css|png|whl)\b)[A-Za-z]{2,}\b"
)
HARMLESS_EMAIL = re.compile(
    r"(?i)@(?:[\w-]+\.)*(?:example\.\w+|noreply\.\w+|users\.noreply\.github\.com)$|^git@|noreply@"
)

SECRET_FILES = (".env", ".env.*", "*.pem", "*.key", "*.p12", "*.pfx", "id_rsa", "id_ed25519", ".netrc", ".pypirc")
SAFE_SECRET_FILES = (".env.example", ".env.sample", ".env.template")
SECRET_FILES += ("credentials.json", "secrets.json")
MACHINE_FILES = ("*.lnk", "shortcuts_created_by_setup.json", "runtime.cmd", "diagnostics.log")
# These name the patterns or example values themselves; license texts and lock files hold other people's addresses.
SKIPPED_FILES = {
    "code/backend/DONT_CHANGE/scripts/tools/check_git_leaks.py",
    "code/backend/DONT_CHANGE/tests/test_git_leaks.py",
}
NO_PERSONAL_CHECK = ("LICENSE*", "*/LICENSES/*", "*.lock")
# Other people's published code, also in old commits: its examples, CA bundles and author addresses are not leaks.
THIRD_PARTY = (
    "*/site-packages/*",
    "*.dist-info/*",
    "*/py_env/*",
    "*/python_packages/*",
    "*/backend_packages/*",
    "*/backend_py_pckgs/*",
    "*/ascii_fonts/*",
    "*/data/fonts/*",
)


class Finding(NamedTuple):
    level: str
    kind: str
    value: str
    where: str
    path: str


def mask(value: str) -> str:
    """Enough of a secret to recognize it, not enough to use it."""
    return value[:4] + "****" if len(value) > 8 else "****"


def _matches(name: str, patterns: Iterable[str]) -> bool:
    return any(fnmatch.fnmatch(name, pattern) for pattern in patterns)


def line_findings(line: str, path: str, where: str) -> List[Finding]:
    """Everything suspicious in one line of text."""
    if IGNORE_MARKER in line or path in SKIPPED_FILES or _matches(path, THIRD_PARTY):
        return []
    found: List[Finding] = []
    for kind, pattern in SECRET_PATTERNS:
        for match in pattern.finditer(line):
            value = match.group(match.lastindex or 0)
            if not (match.lastindex and PLACEHOLDER.search(value)):
                found.append(Finding(SECRET, kind, mask(value), where, path))
    if not _matches(path, NO_PERSONAL_CHECK):
        for match in HOME_FOLDER.finditer(line):
            user = match.group(1) or match.group(2)
            if user.lower() not in PLACEHOLDER_USERS:
                found.append(Finding(PERSONAL, "Home folder path", user, where, path))
        for match in EMAIL.finditer(line):
            if not HARMLESS_EMAIL.search(match.group(0)):
                found.append(Finding(PERSONAL, "Email address", match.group(0), where, path))
    return found


def file_name_findings(path: str, where: str) -> List[Finding]:
    """Files that should not be in a repository, whatever they contain."""
    if _matches(path, THIRD_PARTY):
        return []
    name = path.rsplit("/", 1)[-1]
    if _matches(name, SECRET_FILES) and name not in SAFE_SECRET_FILES:
        return [Finding(SECRET, "Secret file", name, where, path)]
    if _matches(name, MACHINE_FILES):
        return [Finding(PERSONAL, "Machine-specific file", name, where, path)]
    return []


def git(*arguments: str) -> str:
    """Run Git in the project; paths stay readable (no octal escapes for non-ASCII names)."""
    command = ["git", "-C", str(PROJECT_ROOT), "-c", "core.quotepath=off", *arguments]
    # Fixed Git commands; their output is only read.
    completed = subprocess.run(command, capture_output=True, check=False)  # noqa: S603
    if completed.returncode:
        raise RuntimeError(completed.stderr.decode("utf-8", "replace").strip() or "git failed")
    return completed.stdout.decode("utf-8", "replace")


def scan_current_files() -> List[Finding]:
    """The files Git would publish: tracked ones, and new ones that are not ignored."""
    found: List[Finding] = []
    names = git("ls-files", "-z", "--cached", "--others", "--exclude-standard").split("\0")
    for name in filter(None, names):
        found += file_name_findings(name, name)
        path = PROJECT_ROOT / name
        try:
            if not path.is_file() or path.stat().st_size > MAX_FILE_BYTES:
                continue
            data = path.read_bytes()
        except OSError:
            continue
        if b"\0" in data[:8192]:
            continue  # binary
        for number, line in enumerate(data.decode("utf-8", "replace").splitlines(), 1):
            found += line_findings(line, name, f"{name}:{number}")
    return found


def parse_history(log: str) -> List[Finding]:
    """Findings in the added lines of a `git log -p --format="commit %h"` output."""
    found: List[Finding] = []
    commit = path = previous = ""
    for line in log.splitlines():
        if line.startswith("commit "):
            commit = line[7:].strip()
        elif previous.startswith("--- ") and line.startswith("+++ "):
            path = line[6:] if line.startswith("+++ b/") else ""
        elif line.startswith("+") and path:
            found += line_findings(line[1:], path, f"{path} (commit {commit})")
        previous = line
    return found


def scan_history() -> List[Finding]:
    """Every commit on every branch and tag, including what was deleted later."""
    log = git("log", "--all", "-p", "--unified=0", "--no-color", "--no-ext-diff", "--format=commit %h")
    found = parse_history(log)
    for name in set(git("log", "--all", "--format=", "--name-only").splitlines()):
        if name:
            found += file_name_findings(name, f"{name} (in history)")
    return found


def only_new_history(current: List[Finding], history: List[Finding]) -> List[Finding]:
    """One entry per leak that is no longer visible in the current files."""
    known: Set[Tuple[str, str, str]] = {(f.kind, f.value, f.path) for f in current}
    result: List[Finding] = []
    for finding in history:
        key = (finding.kind, finding.value, finding.path)
        if key not in known:
            known.add(key)
            result.append(finding)
    return result


def show(title: str, findings: List[Finding]) -> None:
    """One row per distinct value, with the number of files and the first place it appears."""
    if not findings:
        return
    groups: Dict[Tuple[str, str], List[Finding]] = {}
    for finding in findings:
        groups.setdefault((finding.kind, finding.value), []).append(finding)
    # Names and addresses first: old shortcut files are many, and would push them off the list.
    rows = sorted(groups.values(), key=lambda g: (g[0].kind == "Machine-specific file", g[0].kind, g[0].value.lower()))
    _ui.heading(f"{title} ({len(rows)})")
    _ui.table(
        ("files", "value", "kind", "first place"),
        [(len({f.path for f in group}), group[0].value, group[0].kind, group[0].where) for group in rows[:MAX_ROWS]],
    )
    if len(rows) > MAX_ROWS:
        _ui.info(f"... and {len(rows) - MAX_ROWS} more.")


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--no-history", action="store_true", help="check the current files only")
    arguments = parser.parse_args(argv)

    _ui.heading("Check Git for leaks")
    _ui.fields([("Repository", PROJECT_ROOT)])
    if not Path(PROJECT_ROOT, ".git").exists():
        _ui.error("This project is not a Git repository.")
        return 2
    try:
        _ui.step("Checking the current files ...")
        current = scan_current_files()
        history: List[Finding] = []
        authors: Set[str] = set()
        if not arguments.no_history:
            _ui.step("Checking every commit ...")
            history = only_new_history(current, scan_history())
            authors = set(filter(None, git("log", "--all", "--format=%ae").splitlines()))
    except (OSError, RuntimeError) as error:
        _ui.error(f"Git could not be used: {error}")
        return 2

    everything = current + history
    show("Secrets in the current files", [f for f in current if f.level == SECRET])
    show("Secrets only in old commits", [f for f in history if f.level == SECRET])
    show("Personal data in the current files", [f for f in current if f.level == PERSONAL])
    show("Personal data only in old commits", [f for f in history if f.level == PERSONAL])
    if authors:
        _ui.heading("Author emails, public once the commits are")
        for author in sorted(authors):
            _ui.info("  " + author)

    secrets = sum(f.level == SECRET for f in everything)
    personal = sum(f.level == PERSONAL for f in everything)
    _ui.blank_line()
    if secrets:
        _ui.error(
            f"{secrets} possible secret(s) found. Replace each real one with a new secret: "
            "deleting it from the files does not remove it from the history."
        )
        return 1
    if personal:
        _ui.warn(f"No secrets found, but {personal} place(s) with personal data. Review them before publishing.")
        return 0
    _ui.success("No secrets or personal data found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(_ui.run(main))
