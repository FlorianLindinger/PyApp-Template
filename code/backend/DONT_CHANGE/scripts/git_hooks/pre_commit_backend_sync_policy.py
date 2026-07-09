"""Pre-commit policy for generated backend runtime/package folders."""

import ast
import subprocess
import sys
from pathlib import Path

SETTING_NAME = "sync_backend_python_and_backend_packages_to_git"
SETTINGS_PATH = Path("code/backend/developer_settings.py")
PROTECTED_PATHS = (
    "code/backend/DONT_CHANGE/backend_python",
    "code/backend/DONT_CHANGE/backend_packages",
)


def load_backend_sync_setting():
    try:
        source = SETTINGS_PATH.read_text(encoding="utf-8")
    except OSError as exc:
        raise RuntimeError('Could not read "{}": {}'.format(SETTINGS_PATH, exc))

    try:
        module = ast.parse(source, filename=str(SETTINGS_PATH))
    except SyntaxError as exc:
        raise RuntimeError('"{}" has a syntax error: {}'.format(SETTINGS_PATH, exc))

    for node in module.body:
        value_node = None
        if isinstance(node, ast.Assign):
            names = [target.id for target in node.targets if isinstance(target, ast.Name)]
            value_node = node.value
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names = [node.target.id]
            value_node = node.value
        else:
            continue

        if SETTING_NAME not in names:
            continue

        if value_node is None:
            raise RuntimeError('"{}" must be assigned True or False.'.format(SETTING_NAME))

        try:
            value = ast.literal_eval(value_node)
        except (ValueError, TypeError) as exc:
            raise RuntimeError('"{}" must be set to True or False.'.format(SETTING_NAME))

        if not isinstance(value, bool):
            raise RuntimeError('"{}" must be set to True or False.'.format(SETTING_NAME))
        return value

    raise RuntimeError('"{}" is missing from "{}".'.format(SETTING_NAME, SETTINGS_PATH))


def staged_backend_changes():
    result = subprocess.run(
        [
            "git",
            "diff",
            "--cached",
            "--name-status",
            "--",
            *PROTECTED_PATHS,
        ],
        check=False,
        universal_newlines=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "Could not inspect staged Git changes.")

    return [line for line in result.stdout.splitlines() if line.strip()]


def main():
    try:
        allow_backend_sync = load_backend_sync_setting()
        staged_changes = staged_backend_changes()
    except RuntimeError as exc:
        print("[pre-commit] {}".format(exc), file=sys.stderr)
        return 1

    if allow_backend_sync or not staged_changes:
        return 0

    print(
        "[pre-commit] Generated backend runtime/package files are staged, but {} = False in {}.".format(
            SETTING_NAME, SETTINGS_PATH
        ),
        file=sys.stderr,
    )
    print("", file=sys.stderr)
    print("Staged protected paths:", file=sys.stderr)
    for line in staged_changes[:30]:
        print("  {}".format(line), file=sys.stderr)
    if len(staged_changes) > 30:
        print("  ... {} more".format(len(staged_changes) - 30), file=sys.stderr)
    print("", file=sys.stderr)
    print(
        "Set {} = True for commits that intentionally sync these folders, ".format(SETTING_NAME)
        + "or unstage them with:",
        file=sys.stderr,
    )
    print(
        "  git restore --staged -- code/backend/DONT_CHANGE/backend_python code/backend/DONT_CHANGE/backend_packages",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
