"""Look for secrets and personal data in this Git repository, before it gets published.

Scans the files Git would publish (tracked, and new ones that are not ignored) and every commit,
because something deleted later is still readable in the history. Secrets are masked in the output.

    check_git_leaks.bat                current files and the whole history
    check_git_leaks.bat --no-history   current files only
    check_git_leaks.py --committing    used by git_hooks/pre-commit: only the staged changes
    check_git_leaks.py --pushing       used by git_hooks/pre-push: only the commits being pushed

Exit code 1 means secrets were found. Personal data (home folder paths, email addresses, machine
files) is listed as a warning. Put "leak-check: ignore" on a line to accept it. This finds common
token formats and obvious credentials; it cannot prove that a repository is clean.
"""

from __future__ import annotations

import argparse
import fnmatch
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, Iterable, List, NamedTuple, Optional, Set, Tuple, Union

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

# The user name ends at punctuation that usually follows a path in text, e.g. "(see C:\Users\bob)".
HOME_FOLDER = re.compile(r"(?i)\b[A-Z]:[\\/]+Users[\\/]+([^\\/\s\"'<>|:*?`(),;]+)|(?<![\w.])/home/([a-z_][\w.-]*)")
PLACEHOLDER_USERS = {"public", "default", "all users", "name", "user", "username", "you", "yourname", "me", "runner"}
# Not after ":" or "/" (the password of a URL), and not ending like a file name.
EMAIL = re.compile(
    r"(?<![:/\w.+-])[\w.+-]+@[\w-]+(?:\.[\w-]+)*\.(?!(?:json|py|txt|toml|lock|md|js|css|png|whl)\b)[A-Za-z]{2,}\b"
)
HARMLESS_EMAIL = re.compile(
    r"(?i)@(?:[\w-]+\.)*(?:example\.\w+|noreply\.\w+|users\.noreply\.github\.com)$|^git@|^WIP@|noreply@"
)

SECRET_FILES = (".env", ".env.*", "*.pem", "*.key", "*.p12", "*.pfx", "id_rsa", "id_ed25519", ".netrc", ".pypirc")
SAFE_SECRET_FILES = (".env.example", ".env.sample", ".env.template")
SECRET_FILES += ("credentials.json", "secrets.json")
MACHINE_FILES = ("*.lnk", "*.pyc", "shortcuts_created_by_setup.json", "runtime.cmd", "diagnostics.log")
# These name the patterns or example values themselves; license texts and lock files hold other people's addresses.
SKIPPED_FILES = {
    "code/pyapp/DONT_CHANGE/pyapp_tools/src/check_git_leaks.py",
    "code/pyapp/DONT_CHANGE/tests/src/test_git_leaks.py",
}
NO_PERSONAL_CHECK = ("*LICENSE*", "*/LICENSES/*", "*.lock")
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
    "*/ruamel/*",
)


class Finding(NamedTuple):
    level: str
    kind: str
    value: str
    where: str
    path: str
    source: str = ""


def mask(value: str) -> str:
    """Enough of a secret to recognize it, not enough to use it."""
    return value[:4] + "****" if len(value) > 8 else "****"


def _matches(name: str, patterns: Iterable[str]) -> bool:
    return any(fnmatch.fnmatch(name, pattern) for pattern in patterns)


def redacted_source(line: str) -> str:
    """Keep the source readable without printing any recognized secret, including overlapping matches."""
    spans = sorted(
        match.span(match.lastindex or 0) for _, pattern in SECRET_PATTERNS for match in pattern.finditer(line)
    )
    merged: List[Tuple[int, int]] = []
    for start, end in spans:
        if merged and start < merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    # Replace from right to left so the original character positions stay valid.
    for start, end in reversed(merged):
        line = line[:start] + mask(line[start:end]) + line[end:]
    return line


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
        found.extend(
            Finding(PERSONAL, "Email address", match.group(0), where, path)
            for match in EMAIL.finditer(line)
            if not HARMLESS_EMAIL.search(match.group(0))
        )
    if found:
        source = redacted_source(line)
        return [finding._replace(source=source) for finding in found]
    return []


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


def decoded_text(data: bytes) -> Optional[str]:
    """The text of a file, or None for a binary one.

    UTF-16 text (PowerShell 5.1 redirections, some exports) is full of NUL bytes, so it is
    recognized by its byte-order mark before the NUL test that marks binary files.
    """
    if data.startswith((b"\xff\xfe", b"\xfe\xff")):
        return data.decode("utf-16", "replace")
    if b"\0" in data[:8192]:
        return None
    return data.decode("utf-8", "replace")


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
        text = decoded_text(data)
        if text is None:
            continue  # binary
        for number, line in enumerate(text.splitlines(), 1):
            found += line_findings(line, name, f"{name}:{number}")
    return found


def parse_history(log: Union[str, Iterable[str]], place: str = "") -> List[Finding]:
    """Findings in the added lines of a `git log -p --format="commit %h"` or `git diff` output.

    place names where a finding is, e.g. "staged"; by default the commit of each change.
    """
    found: List[Finding] = []
    commit = path = previous = ""
    new_line: Optional[int] = None
    for raw_line in log.splitlines() if isinstance(log, str) else log:
        line = raw_line.rstrip("\r\n")
        if line.startswith("commit "):
            commit = line[7:].strip()
            path = ""
            new_line = None
        elif line.startswith("diff --git "):
            path = ""
            new_line = None
        elif previous.startswith("--- ") and line.startswith("+++ "):
            path = line[6:] if line.startswith("+++ b/") else ""
            new_line = None
        elif line.startswith("@@ "):
            hunk = re.match(r"@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@", line)
            new_line = int(hunk.group(1)) if hunk else None
        elif line.startswith("+") and path:
            location = f"{path}:{new_line}" if new_line is not None else path
            found += line_findings(line[1:], path, f"{location} ({place or 'commit ' + commit})")
            if new_line is not None:
                new_line += 1
        elif line.startswith(" ") and new_line is not None:
            # Context exists in both versions; removed lines and Git's no-newline marker do not
            # advance the line number in the staged file (or the file at the reported commit).
            new_line += 1
        previous = line
    return found


def scan_history() -> List[Finding]:
    """Every commit on every branch and tag, including what was deleted later."""
    # Read line by line: the whole history of a large repository can be gigabytes as one string.
    command = [
        *("git", "-C", str(PROJECT_ROOT), "-c", "core.quotepath=off", "log", "--all", "-p", "--unified=0"),
        *("--no-color", "--no-ext-diff", "--format=commit %h"),
    ]
    # A fixed Git command; its output is only read. stderr is discarded: an unread second pipe
    # could fill up and block Git while the history is still being read.
    with subprocess.Popen(  # noqa: S603
        command, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, encoding="utf-8", errors="replace"
    ) as process:
        found = parse_history(process.stdout) if process.stdout is not None else []
    if process.returncode:
        raise RuntimeError(f"git log failed (exit code {process.returncode})")
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


def working_file_link(finding: Finding) -> str:
    """A link to the place in the working file, for staged and current-file findings ("" otherwise).

    A finding in a commit gets none: the file on disk may have changed since, or no longer exist.
    """
    if not finding.path or not (finding.where.endswith(" (staged)") or "(" not in finding.where):
        return ""
    path = PROJECT_ROOT / finding.path
    if not path.is_file():
        return ""
    line = re.match(r"^.*?:(\d+)(?: \(|$)", finding.where)
    return _ui.file_link(path, int(line.group(1)) if line else None)


def show(title: str, findings: List[Finding]) -> None:
    """Group values and show every distinct location with its source line, masking recognized secrets."""
    if not findings:
        return
    groups: Dict[Tuple[str, str], List[Finding]] = {}
    for finding in findings:
        groups.setdefault((finding.kind, finding.value), []).append(finding)
    # Names and addresses first: old shortcut files are many, and would push them off the list.
    rows = sorted(groups.values(), key=lambda g: (g[0].kind == "Machine-specific file", g[0].kind, g[0].value.lower()))
    _ui.heading(f"{title} ({len(rows)})")
    table_rows: List[Tuple[Union[int, str], str, str, str]] = []
    for group in rows[:MAX_ROWS]:
        locations = {finding.where: finding for finding in group}
        for index, (location, finding) in enumerate(locations.items()):
            table_rows.append(
                (len({f.path for f in group}), group[0].value, group[0].kind, location)
                if index == 0
                else ("", "", "", location)
            )
            if finding.source:
                table_rows.append(("", "", "", "    | " + finding.source))
            link = working_file_link(finding)
            if link:
                table_rows.append(("", "", "", "    " + link))
    _ui.table(
        ("files", "value", "kind", "place"),
        table_rows,
    )
    if len(rows) > MAX_ROWS:
        _ui.info(f"... and {len(rows) - MAX_ROWS} more.")


def pushed_revisions(hook_input: str) -> List[List[str]]:
    """`git log` selections for the lines Git gives a pre-push hook: only what the remote does not have."""
    revisions: List[List[str]] = []
    for line in hook_input.splitlines():
        fields = line.split()
        if len(fields) != 4 or not fields[1].strip("0"):
            continue  # a deleted branch publishes nothing
        local, remote = fields[1], fields[3]
        if remote.strip("0") and commit_exists(remote):
            revisions.append([f"{remote}..{local}"])
        else:
            revisions.append([local, "--not", "--remotes"])
    return revisions


def commit_exists(name: str) -> bool:
    try:
        git("cat-file", "-e", name + "^{commit}")
    except RuntimeError:
        return False
    return True


def scan_revisions(revisions: List[List[str]]) -> List[Finding]:
    """The added lines, file names and commit emails of the selected commits."""
    found: List[Finding] = []
    for selection in revisions:
        found += parse_history(
            git("log", "-p", "--unified=0", "--no-color", "--no-ext-diff", "--format=commit %h", *selection)
        )
        for name in set(git("log", "--format=", "--name-only", *selection).splitlines()):
            if name:
                found += file_name_findings(name, f"{name} (in this push)")
        for email in set(git("log", "--format=%ae%n%ce", *selection).splitlines()):
            if email and not HARMLESS_EMAIL.search(email):
                found.append(Finding(PERSONAL, "Commit email", email, "author or committer of a commit", ""))
    return found


def check_push(hook_input: str) -> int:
    """For the pre-push hook: here personal data stops the push too, because it would become public."""
    revisions = pushed_revisions(hook_input)
    if not revisions:
        return 0
    findings = scan_revisions(revisions)
    if findings:
        hook_summary("Push", findings)
    show("Secrets in this push", [f for f in findings if f.level == SECRET])
    show("Personal data in this push", [f for f in findings if f.level == PERSONAL])
    if findings:
        _ui.blank_line()
        _ui.error(
            "Fix the reported commits before pushing. A working-file edit alone does not remove a leak from history.\n"
            'For an intentional value, put "leak-check: ignore" on that line in the affected commit.\n'
            "To push anyway, once: git push --no-verify"
        )
        return 1
    _ui.success("Nothing found in the commits being pushed.")
    return 0


def hook_summary(action: str, findings: List[Finding]) -> None:
    """Lead with an actionable line: Git clients may show only the first output line in a popup."""
    first = findings[0]
    more = f" (+{len(findings) - 1} more)" if len(findings) > 1 else ""
    _ui.info(
        f"{action} blocked: {first.kind} {first.value!r} at {first.where}{more}. "
        'Click "Show Command Output" for details.'
    )


def check_commit() -> int:
    """For the pre-commit hook: the staged changes, so a leak never gets into a commit at all.

    Stopping here is easier to fix than at the push: nothing has to be taken out of a commit. The
    commit email is left to the pre-push check, as it is not part of the staged changes.
    """
    diff = git("diff", "--cached", "-p", "--unified=0", "--no-color", "--no-ext-diff")
    findings = parse_history(diff, "staged")
    for name in set(git("diff", "--cached", "--name-only", "--diff-filter=AR").splitlines()):
        if name:
            findings += file_name_findings(name, f"{name} (staged)")
    if not findings:
        return 0  # silent: this runs on every commit
    hook_summary("Commit", findings)
    show("Secrets in the staged changes", [f for f in findings if f.level == SECRET])
    show("Personal data in the staged changes", [f for f in findings if f.level == PERSONAL])
    _ui.blank_line()
    _ui.error(
        "Edit the reported lines, stage the corrected files, then commit again.\n"
        'For an intentional value, put "leak-check: ignore" on that line and stage it again.\n'
        "Ctrl+click a file:/// link to open its line. Locations refer to the staged version;\n"
        "unstaged edits can shift the line numbers in the editor.\n"
        "To commit anyway, once: git commit --no-verify"
    )
    return 1


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--no-history", action="store_true", help="check the current files only")
    parser.add_argument("--committing", action="store_true", help="for the pre-commit hook: the staged changes")
    parser.add_argument("--pushing", action="store_true", help="for the pre-push hook: reads its input")
    arguments = parser.parse_args(argv)
    if arguments.committing:
        return check_commit()
    if arguments.pushing:
        return check_push(sys.stdin.read())

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
