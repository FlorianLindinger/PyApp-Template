"""Run hook checks in disposable Git checkouts of the index or pushed commit tips.

Only the temporary repository is written: no stash, checkout, staging, or commit in the source.
A shared mirror retains the source refs/history for leak and release checks, while checkout-index
applies the submitted .gitattributes and the caller's checkout line-ending policy.
"""

from __future__ import annotations

import contextlib
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, Generator, List, Optional

from _paths import PROJECT_ROOT

LAUNCHER = Path("code/pyapp/DONT_CHANGE")
SNAPSHOT_ENV = "PYAPP_CHECKING_GIT_SNAPSHOT"


def clean_environment() -> Dict[str, str]:
    """Git hook variables must not redirect commands in the temporary repo to the source index."""
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    # Author/committer overrides describe the attempted commit, rather than a repository location.
    for key in (
        "GIT_AUTHOR_NAME",
        "GIT_AUTHOR_EMAIL",
        "GIT_AUTHOR_DATE",
        "GIT_COMMITTER_NAME",
        "GIT_COMMITTER_EMAIL",
        "GIT_COMMITTER_DATE",
    ):
        if key in os.environ:
            env[key] = os.environ[key]
    env.pop("PYAPP_SETTINGS_PUSH_REFS", None)
    env["PYTHONIOENCODING"] = "utf-8"
    return env


def git(
    root: Path, *arguments: str, data: Optional[bytes] = None, optional: bool = False, source_index: bool = False
) -> bytes:
    """A fixed Git operation; callers never ask this helper to mutate the source repo."""
    env = clean_environment()
    if source_index and "GIT_INDEX_FILE" in os.environ:
        # Partial/path-only commits may give the hook a temporary index rather than .git/index.
        env["GIT_INDEX_FILE"] = str(Path(os.environ["GIT_INDEX_FILE"]).absolute())
    completed = subprocess.run(  # noqa: S603
        ["git", "-C", str(root), *arguments],  # noqa: S607
        env=env,
        input=data,
        capture_output=True,
        check=False,
    )
    if completed.returncode:
        if optional:
            return b""
        raise RuntimeError(completed.stderr.decode("utf-8", "replace").strip() or "Git snapshot command failed")
    return completed.stdout


def validate_entries(entries: bytes) -> None:
    """Fail closed on unresolved merges and entries whose contents cannot be isolated here."""
    for entry in entries.split(b"\0"):
        if not entry:
            continue
        metadata, name = entry.split(b"\t", 1)
        mode, _object_id, stage = metadata.split()
        if stage != b"0":
            raise RuntimeError("Resolve the staged merge conflict before checking: " + name.decode("utf-8", "replace"))
        if mode not in (b"100644", b"100755"):
            raise RuntimeError(
                "Snapshot checks require regular files (no symlinks/submodules): " + name.decode("utf-8", "replace")
            )


@contextlib.contextmanager
def checkout(root: Path, revision: Optional[str] = None) -> Generator[Path, None, None]:
    """A submitted checkout: None exports the index; a revision exports that immutable commit.

    The generated directory and its .git metadata are owned by TemporaryDirectory, which removes
    only that directory on exit. Shared object access is read-only; writes stay in the mirror.
    """
    entries = git(root, "ls-files", "--stage", "-z", source_index=True) if revision is None else None
    if entries is not None:
        # git add -N records a placeholder that git commit deliberately omits. It must not
        # become an empty submitted file merely because ls-files includes it.
        visible = set(
            git(root, "diff", "--cached", "--name-only", "-z", "--ita-visible-in-index", source_index=True).split(b"\0")
        )
        submitted = set(
            git(root, "diff", "--cached", "--name-only", "-z", "--ita-invisible-in-index", source_index=True).split(
                b"\0"
            )
        )
        placeholders = visible - submitted
        entries = (
            b"\0".join(
                entry for entry in entries.split(b"\0") if entry and entry.split(b"\t", 1)[1] not in placeholders
            )
            + b"\0"
        )
        validate_entries(entries)
    with tempfile.TemporaryDirectory(prefix="pyapp-check-") as folder:
        target = Path(folder) / "repo"
        target.mkdir()
        # --mirror preserves the real refs/remotes rather than treating all source commits as
        # already published to an artificial origin (which would weaken first-push leak checks).
        git(root, "clone", "--quiet", "--mirror", "--shared", str(root), str(target / ".git"))
        git(target, "config", "core.bare", "false")
        git(target, "config", "core.hooksPath", str(target / ".git" / "disabled-hooks"))
        for key in ("core.autocrlf", "core.eol", "core.symlinks", "user.name", "user.email", "remote.origin.url"):
            value = git(root, "config", "--get", key, optional=True).decode("utf-8").strip()
            if value:
                git(target, "config", key, value)
            elif key == "remote.origin.url":
                git(target, "config", "--unset", key, optional=True)
        if revision is None:
            git(target, "read-tree", "--empty")
            git(target, "update-index", "-z", "--index-info", data=entries)
        else:
            # Detached HEAD ensures code/tests that inspect HEAD see the exact pushed tip,
            # including a branch other than the one currently checked out in the source.
            git(target, "update-ref", "--no-deref", "HEAD", revision)
            git(target, "read-tree", "--reset", revision)
            validate_entries(git(target, "ls-files", "--stage", "-z"))
        git(target, "checkout-index", "--all", "--force")
        yield target


def run(
    root: Path, snapshot: Path, command: List[str], *, refs: Optional[str] = None, scope: Optional[str] = None
) -> int:
    """Run submitted check code/configuration; retain diagnostics after the checkout is removed."""
    env = clean_environment()
    env[SNAPSHOT_ENV] = "1"
    completed = subprocess.run(  # noqa: S603
        command,
        cwd=snapshot,
        env=env,
        input=refs.encode("utf-8") if refs is not None else None,
        capture_output=True,
        check=False,
    )
    output = (completed.stdout + completed.stderr).decode("utf-8", "replace")
    # Links must remain usable after cleanup. The scope label explains that line
    # numbers/content belong to the submitted snapshot, which may differ from the editor.
    output = output.replace(snapshot.as_uri(), root.as_uri())
    output = output.replace(str(snapshot), str(root)).replace(snapshot.as_posix(), root.as_posix())
    if output.strip():
        lines = output.strip().splitlines()
        # Editors use the first line as the failure headline: keep its actionable cause first.
        print(lines[0], file=sys.stderr)
        if scope:
            print(scope, file=sys.stderr)
        if len(lines) > 1:
            print("\n".join(lines[1:]), file=sys.stderr)
    elif scope:
        print(scope, file=sys.stderr)
    return completed.returncode


def commit_checks(root: Path = PROJECT_ROOT) -> int:
    """Leaks, Ruff (including its staged configuration), settings and compatibility on the index."""
    with checkout(root) as snapshot:
        source = snapshot / LAUNCHER / "pyapp_tools" / "src"
        commands = (
            [sys.executable, "-B", str(source / "check_git_leaks.py"), "--committing"],
            [sys.executable, "-B", str(source / "check_staged_ruff.py")],
            [sys.executable, "-B", str(snapshot / LAUNCHER / "scripts" / "settings_defaults.py"), "--staged"],
            [sys.executable, "-B", str(source / "check_protected.py")],
        )
        for command in commands:
            code = run(root, snapshot, command)
            if code:
                print(
                    "Commit checks used the staged snapshot. Locations refer to staged content; "
                    'click "Show Command Output" for details.',
                    file=sys.stderr,
                )
                return code
    return 0


def push_checks(refs: str, root: Path = PROJECT_ROOT) -> int:
    """Run the complete submitted pre-push pipeline for every distinct non-deletion local tip."""
    revisions: List[str] = []
    for line in refs.splitlines():
        if not line.strip():
            continue
        fields = line.split()
        if len(fields) != 4:
            raise ValueError("Invalid pre-push input: expected four fields per ref.")
        revision = fields[1]
        # rev-parse rejects non-commit/tag targets before any submitted Python is executed.
        if set(revision) == {"0"}:
            continue
        resolved = git(root, "rev-parse", "--verify", "--end-of-options", revision + "^{commit}").decode().strip()
        if resolved not in revisions:
            revisions.append(resolved)
    for revision in revisions:
        with checkout(root, revision) as snapshot:
            checker = snapshot / LAUNCHER / "pyapp_tools" / "src" / "check_all.py"
            code = run(
                root,
                snapshot,
                [sys.executable, "-B", str(checker), "--pushing"],
                refs=refs,
                scope=f"Checked submitted commit {revision} (isolated checkout).",
            )
            if code:
                return code
    return 0


def main() -> int:
    if sys.argv[1:] != ["--committing"]:
        raise SystemExit("Usage: git_snapshot.py --committing")
    return commit_checks()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError) as error:
        print(
            f'Commit blocked: Could not check staged snapshot: {error}. Click "Show Command Output" for details.',
            file=sys.stderr,
        )
        raise SystemExit(1) from None
