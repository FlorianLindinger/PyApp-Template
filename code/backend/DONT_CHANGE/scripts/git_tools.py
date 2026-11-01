"""Repository inspection for developer tools."""

from pathlib import Path


def git_repository_root() -> Path:
    """Return the Git work tree containing this project."""
    import subprocess

    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=Path(__file__).parent,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "Could not find a Git work tree.")
    return Path(result.stdout.strip())


def run_git(arguments: list[str]) -> int:
    """Run Git in the project repository and return its exit code."""
    import subprocess

    try:
        root = git_repository_root()
    except (FileNotFoundError, RuntimeError) as error:
        print(f"[Error] {error}")
        return 2
    return subprocess.run(["git", *arguments], cwd=root, check=False).returncode


def show_git_results(
    arguments: list[str], *, heading: str, no_results_message: str
) -> int:
    """Run a Git listing command and make an empty result explicit."""
    import subprocess

    try:
        root = git_repository_root()
    except (FileNotFoundError, RuntimeError) as error:
        print(f"[Error] {error}")
        return 2

    print(f"[Info] {heading}")
    result = subprocess.run(
        ["git", *arguments],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.stdout:
        print(result.stdout, end="" if result.stdout.endswith("\n") else "\n")
    elif result.returncode == 0:
        print(f"[Info] {no_results_message}")
    if result.stderr:
        print(result.stderr, end="" if result.stderr.endswith("\n") else "\n")
    return result.returncode
