# Application pyapp

Configure the application in [developer_settings.py](developer_settings.py): name,
Python version, the packages it needs (`packages`), where uv/Python/packages come from,
shortcuts, logging and completion behavior.

The app's uv project is in [generated](generated/README.md). Generated on the first run:

- `generated/uv.lock` and `generated/.python-version`: the locked package versions and the recorded Python version request. **Commit them.**
- `generated/pyproject.toml`: generated from `packages` and `python_version` for uv. Do not edit it;
  changes made to it anyway (e.g. `uv add`) are copied into `packages`. Ignored by Git.
- `generated/.venv/`: the app environment. Ignored by Git.

Change packages and the Python version in `developer_settings.py` or with the tools in
[dev_tools](dev_tools/README.md).

Other generated items in `generated/`: `pythons/` and `uv/` (only when installed locally), `uv-cache/`
(only with `uv_cache = "local"`) and `shortcuts_created_by_setup.json` (the shortcuts Setup created, so it can
remove stale ones). All are ignored by Git.

If the launcher itself is broken, double-click [Start without launcher.cmd](Start%20without%20launcher.cmd)
(its code: `DONT_CHANGE/actions/start_without_launcher.py`, which uses nothing else of the launcher):
it runs the main script directly with the app's environment (`generated/.venv`), or with the global
default Python when that environment is missing or broken. It shows the main script, Python,
packages (installed or missing) and their folders first. There is no setup, no package installation,
no log, no crash log and no STOP shortcut. Run Setup to repair the launcher.

For normal development edit `../main.py`, `../settings.py` and `developer_settings.py`.
See the [pyapp internals](DONT_CHANGE/README.md) when maintaining the template itself.
