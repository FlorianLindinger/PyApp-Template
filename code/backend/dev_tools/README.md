# Application package tools

**Use the batches in this folder to change application packages.** They select
the managed application Python and package directory, coordinate environment
changes and update the installation state. Close running app instances first.

## Recommended workflow

For a deliberate dependency change:

1. Edit [DEFAULT_PYTHON_PACKAGES.txt](DEFAULT_PYTHON_PACKAGES.txt), adding, removing
   or changing the required distributions. For explicit requirements, set its
   `auto_find_required_packages_here_and_reset_installed_packages_to_them` flag
   to `False`; `True` requests reviewed import inference on supported repair paths.
2. Run `reset_packages_default.bat` to replace the application packages with that
   list and its dependencies. This removes packages outside the declared set.
3. Run and check the application, then commit the requirements file.

For interactive experiments:

1. Run `open_package_terminal.bat`.
2. Enter package names or commands at `packages>`, for example `requests rich`,
   `pip install requests` or `uv pip install requests`. No Python/module prefix
   is needed. See the command examples below.
3. Type `exit` when finished so the tool validates dependencies and records the
   resulting package state.
4. To make that environment the defaults for future installations, enter `save`
   before exiting, or run `set_default_packages_versions.bat` (pinned versions) or
   `set_default_packages_names.bat` (names only). Review and commit the resulting
   `DEFAULT_PYTHON_PACKAGES.txt`.

The manual terminal changes installed packages; it does not automatically change
the defaults file. Its operations modify the live environment, whereas reset and
requirements-install tools prepare and validate a staging environment first.

## Package console

Run `open_package_terminal.bat`, then use commands such as:

```text
requests
requests rich>=13
requests, rich
["requests[socks,security]", "rich>=13,<14"]
install -r "my requirements.txt"
upgrade requests rich
uninstall requests
pip install requests
uv pip install requests
list
list --outdated
show requests
check
freeze
status
help
save
exit
```

Bare packages and unprefixed install/uninstall/list/freeze/show/check commands
prefer uv when `use_uv_to_install_packages = True`; an unavailable or failed uv
operation falls back to pip. With that setting disabled, they use pip. Explicit
`pip ...` selects pip; explicit `uv pip ...` selects uv and reports uv failures
without substituting pip. `uv --version` and `uv --help` are also available.

The console resolves uv from the managed backend or an available `uv.exe`. If
neither exists, it attempts to install the pinned optional uv tool locally once
per session. Failure still allows automatic commands to use pip. uv project
commands such as `uv init` and `uv run` are outside this app-package console.

Requirements options are forwarded to the installer; tool-specific flags may
require an explicit `pip` or `uv` command. Double-quote paths and requirements
containing spaces. Version constraints, extras and URLs are literal arguments;
this prompt does not evaluate CMD redirection, pipes or command chaining.
Environment-selection overrides are rejected so operations stay with the app.

Errors and Ctrl+C leave the prompt open. `status` shows the interpreter, package
target, default installer and last command's exit code. `save` first validates
dependencies, writes installed versions as defaults with automatic inference
disabled, and refreshes the installation state. Changes to defaults are explicit;
review and commit the resulting file.

The installation lock is held during the session. `exit` or end-of-input validates
dependencies and records package state; a broken environment is reported rather
than marked healthy. You can also pass a command directly, for example
`open_package_terminal.bat pip list`. Portable `pip`, `pip3`, versioned pip and
`uv` adapters are generated inside the application Python folder; these and
the recovery launcher use the same command implementation after folder moves.

Using a system `pip` or an unrelated terminal can install into the wrong Python.
Direct changes outside these tools can leave the saved package state stale and
cause startup to rebuild packages from the declared defaults. Global-Python mode
is a separate workflow: these tools maintain the managed local environment.

## Commands

| Batch | Action |
| --- | --- |
| `install_imports.bat` | Infer dependencies from project imports, review and install them. |
| `install_local_reqs.bat` | Install `requirements.txt` from this folder into the current package set. |
| `open_package_terminal.bat` | Open a terminal using the application Python and package target. |
| `reset_packages_default.bat` | Replace installed packages with the declared defaults. |
| `reset_packages_empty.bat` | Replace application packages with an empty environment. |
| `reset_packages_imports.bat` | Replace packages with reviewed inferred dependencies. |
| `upgrade_packages.bat` | Upgrade installed application packages. |
| `save_current_packages_names.bat` | Save installed distribution names to a generated list. |
| `save_current_packages_versions.bat` | Save installed distributions and versions to a generated list. |
| `save_imported_packages_names.bat` | Save inferred distribution names to a generated list. |
| `save_imported_packages_versions.bat` | Save inferred requirements with determined versions. |
| `set_default_packages_names.bat` | Save installed package names as the default dependency list. |
| `set_default_packages_versions.bat` | Save installed packages and versions as the default dependency list. |

## Files and execution

Keep `DEFAULT_PYTHON_PACKAGES.txt` in Git, even if it declares no packages. Its
adjacent `.lock.json` and determined/auto-found lists are generated local state.
Import inference proposes dependencies for review; it cannot reliably discover
all dynamic or optional imports. Explicit requirements are the normal input.

Each batch calls its matching `DONT_CHANGE/scripts/dev_tools/*.py` through the
shared backend bootstrap/runner. Generated shortcuts are unnecessary. Paths are
resolved relative to each batch, so these tools work after moving the project.
Failures preserve nonzero exit codes; interactive tools retain their configured
completion prompts.
