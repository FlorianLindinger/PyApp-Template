# Application backend

Configure the application in [developer_settings.py](developer_settings.py): name,
Python version, the packages it needs (`packages`), where uv/Python/packages come from,
shortcuts, logging and completion behavior.

This folder is also the app's uv project. Generated on the first run:

- `environment/uv.lock` and `environment/.python-version`: the exact package and Python versions. **Commit them.**
- `environment/pyproject.toml`: generated from `packages` and `python_version` for uv. Do not edit it;
  changes made to it anyway (e.g. `uv add`) are copied into `packages`. Ignored by Git.
- `environment/.venv/`: the app environment. Ignored by Git.

Change packages and the Python version in `developer_settings.py` or with the tools in
[dev_tools](dev_tools/README.md).

Other generated items here: `pythons/` and `uv/` (only when installed locally), `uv-cache/`
(only with `uv_cache = "local"`) and `shortcuts_created_by_setup.json` (the shortcuts Setup created, so it can
remove stale ones). All are ignored by Git.

For normal development edit `../main.py`, `../settings.py` and `developer_settings.py`.
See the [backend internals](DONT_CHANGE/README.md) when maintaining the template itself.
