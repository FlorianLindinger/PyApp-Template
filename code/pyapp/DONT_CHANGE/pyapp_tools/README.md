# Launcher development tools

Tools for working on the launcher in `code/pyapp/DONT_CHANGE`, not for your app. The launcher never uses this folder, so deleting it doesn't affect anything.

Double-click a `.bat`, or run it from a terminal with arguments. Each one uses the Python the launcher has already set up. When it finishes, press Enter to run it again, with the same arguments, or close the window. The `.bat` files only name their script; `src/_run_tool.bat` does the rest for all of them.

Hook failures begin with a short cause before the detailed output: a failing test or checker,
a compatibility problem, a missing changelog entry, or a possible leak. Leak reports distinguish
staged changes from commits being pushed. Use **Show Command Output** for locations and repair steps.

| Tool | What it does |
| --- | --- |
| `show_splash_screen.bat [--seconds SECONDS]` | Previews the splash exactly as the next no-terminal start shows it (name, icon, next `splash_screen_messages` line), even when the splash setting is disabled. Stays open until you click it or press Escape; `--seconds` optionally enables automatic closing. Does not start the app or prepare its environment. |
| `verify_launcher.bat [--fix]` | Runs Ruff lint (including pathlib `PTH` and security `S` checks), Ruff format and strict Pyrefly on `DONT_CHANGE`, targeting Python 3.8 with its own `ruff.toml` and `pyrefly.toml`. Prints diagnostics and a warning for each check that reports problems; exits nonzero if any check fails. `--fix` applies safe fixes and formatting first; `--unsafe-fixes` also applies Ruff's unsafe ones. Needs `ruff` and `pyrefly` on PATH, or `uvx`. |
| `fresh_clone_test.bat [--timeout] [--keep]` | Clones the current commit into a temporary folder with spaces in its path, runs Setup, starts the launcher without a terminal and runs a dev tool, which finds files missing from Git. Then smoke tests: the log without a terminal (prints and native output), a Python error (crash log), a hard interpreter crash (crash log, last output kept), a start without internet, a start after moving the folder, and Setup updating the shortcuts for the new place. Only committed files are tested, and it lists what isn't committed. `main.py` in the clone is replaced by a probe, and Setup there leaves your Start Menu and Desktop alone. Not covered: a missing package, whose recovery menu waits for an answer. |
| `test_all_pythons.bat [versions] [--pattern]` | Runs the regression tests on Python 3.8 and the newest stable Python, or on the versions you name. The Pythons are kept in your temporary folder. |
| `release.bat [patch\|minor\|major\|X.Y.Z]` | Checks that a release is possible, runs the tests, `test_all_pythons` (Python 3.8 and the newest) and `fresh_clone_test` (`--quick`: only the tests on this Python), sets `LAUNCHER_VERSION`, saves the `PROTECTED_*` lists of `pyapp_settings.py` in `data/protected_baseline.json` (until the next MAJOR version the tests refuse to take an entry off), turns the `## unreleased` changelog section into `## <version> - <date>` and writes a zip of the tracked `DONT_CHANGE` files to `pyapp_tools/zip_releases` (ignored by Git except its `.gitkeep`). Without a version it only checks. It refuses uncommitted changes unless you pass `--allow-dirty`, and commits nothing. It does not offer to run again. |
| `check_repository.bat [--max-mb 5] [--why PATH] [--ignored]` | Finds what breaks clones, other PCs or Windows: tracked files that `.gitignore` says to ignore, `!` exceptions in `.gitignore` files that do not take effect, mixed line endings (fix: `git add --renormalize .`), paths that differ only in letter case, names Windows cannot use, paths too long for Windows, large files, tracked caches and environments, nested Git repositories. `--why PATH` shows which `.gitignore` line decides a path (also an exception that keeps it); `--ignored` lists the ignored files and folders by size, i.e. what stays on this PC. Read-only. Secrets are `check_git_leaks.bat`'s job. |
| `check_all.bat` | Everything at once, with a summary: the leak check over the commits this branch has that its remote does not, the changelog check (`src/check_changelog.py`: for `main`, launcher changes need a `CHANGELOG.md` entry), the repository check, `verify_launcher` and the tests (in parallel). Manual invocation checks working files. The pre-push hook runs these steps in submitted-commit checkouts, stopping at the first failure. |
| `src/git_hooks/pre-commit` | Stops a commit whose staged changes contain secrets or personal data, so nothing has to be taken out of a commit later, or whose staged launcher files fail Ruff's lint or format check (`src/check_staged_ruff.py`; checks what is staged, not the files on disk), or whose staged template settings differ from staged fallback defaults (`../scripts/settings_defaults.py --staged`), or that would break what existing projects rely on (`src/check_protected.py`: runs `test_template_contract.py` when `code/pyapp` changes; the `PROTECTED_*` lists of `pyapp_settings.py` must match the code and keep every entry until a MAJOR version). Runs all four checks from an isolated checkout of the index, including staged checker code, Ruff configuration, exclusions and compatibility tests. Leaves the original index and working files alone; when everything passes it is silent in editors and shows one `✓` line in a terminal. `git commit --no-verify` skips it once. |
| `src/git_hooks/pre-push` | Stops a push whose commits contain secrets or personal data, including private commit emails: the last check before publishing, also for commits made with `--no-verify`. A push to `main` that changes launcher files without changing `CHANGELOG.md` is stopped too. Runs the complete pipeline, including repository checks, `verify_launcher` and regression tests, in an isolated checkout of each distinct submitted commit tip (including non-HEAD branches). All checker code, configuration and tested files come from that commit; original refs/history remain available for leak and changelog checks. In a terminal each step is listed as it finishes, with its time. Without Ruff or Pyrefly, verification is skipped with a note. Git runs it during a push, not you; `git push --dry-run` tests it and `git push --no-verify` skips it once. |
| `enable_git_hooks.bat [--off]` | Turns both hooks on (or off) for this clone and for every later clone of the same repository on this PC: it sets `core.hooksPath` here and adds an `includeIf "hasconfig:remote.*.url:<this origin>**"` to your global Git configuration that points to `~/.gitconfig-pyapp-hooks` (Git 2.36+). Clones of other repositories and other PCs are not affected; Setup never changes Git settings, so people who clone the template do not get the hooks. In VS Code, the popup shows the hook's leading summary; full diagnostics are under **Show Command Output** (or View → Output → Git). |
| `check_git_leaks.bat [--no-history]` | Looks for secrets (token formats, private keys, passwords in code, secret files) and personal data (home folder paths, email addresses, machine files) in the files Git would publish and in every commit. Secrets are masked; exits nonzero if any are found. Put `leak-check: ignore` on a line to accept it. It finds common formats and cannot prove that a repository is clean. |
| `get_startup_time.bat` | Measures the time from starting a shortcut's launcher until the main script runs, compared with starting it directly with the `.venv` Python. Works on a temporary copy of the project. Options: `--runs`, `--timeout`, `--targets` (`terminal`, `no_terminal`, `direct`), `--keep`. |
| `make_import_map.bat` | Regenerates `data/import_to_package.txt`, the import name to PyPI project list that `find_imports` uses for packages that aren't installed yet. Needs internet and takes a few minutes; progress is cached in `DONT_CHANGE/tmp`, so an interrupted run continues. Cached projects older than 30 days are read again. Options: `--count` (default 8000), `--workers`, `--output`, `--cache`, `--max-age-days`, `--refresh` (read every project again). |
| `get_longest_paths.bat [count] [folder]` | Lists the longest paths in the project, including ignored ones such as `.venv` and `__pycache__` files that don't exist yet, and whether they exceed the Windows path limit. |

The code these files run is in `src`.

Hook failures put the cause and repair in the first output line, before test output or tracebacks,
so Git popups can explain the block immediately. Known file checks name CRLF, README-table or
test-group problems; multiple failed checks are summarized together. Lint/leak reports retain
their exact locations, and leak values stay masked. A push leak message requests repairs to
the affected commits, while a commit message requests corrected staged files.
Use **Show Command Output** for every affected file, clickable locations and full repair steps.

## GitHub Actions

The template's own workflows (`.github/workflows/pyapp-template-launcher-tests.yml` and
`pyapp-template-fresh-clone.yml`) run only for pushes and pull requests to `main`, on purpose: work on
`dev` is checked by the pre-push hook and reaches CI through a pull request into `main`. Their actions
are pinned by release tag, not by commit SHA. Changing a workflow also needs its new digest in
`KNOWN_TEMPLATE_WORKFLOWS` (`scripts/github/template_workflows.py`).

All Git-hook checks inspect submitted code. `src/git_snapshot.py` exports the index for pre-commit
and each distinct non-deletion submitted commit tip for pre-push to temporary repositories. Those checkouts
include the submitted checker scripts, configuration, attributes and test fixtures; untracked files and
unstaged preferences cannot cause or hide failures. Shared read-only objects and mirrored refs preserve
history checks. The caller's checkout line-ending policy is retained. Unresolved merges and symlink/submodule
entries fail closed rather than escaping isolation. Diagnostics identify the submitted scope and map paths
back to source locations; the editor may contain different content at those lines. Temporary checkouts are
removed afterwards; the source index, working files and refs are never rewritten. Git's temporary index for
path-only commits is honored. Ordinary tests and manual `check_all` still inspect working files.

Use the [release checklist](../docs/RELEASE_CHECKLIST.md) to record the candidate commit, automated results,
desktop checks and artifact validation. Desktop state/attention rules are in
[WINDOW_LIFECYCLE.md](../docs/WINDOW_LIFECYCLE.md).
