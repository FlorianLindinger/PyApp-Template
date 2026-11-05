# Application backend

Configure the application in [developer_settings.py](developer_settings.py): name,
Python version, where uv/Python/packages come from, shortcuts, logging and completion behavior.

Change packages and the Python version with the tools in [dev_tools](dev_tools/README.md)
(or uv commands in `../`). Dependencies are declared in `../pyproject.toml` and locked in
`../uv.lock`; the app environment is `../.venv`.

Generated folders here: `pythons/` and `uv/` (only when installed locally), `uv-cache/`
(only with `uv_cache = "local"`) and `shortcuts_created_by_setup.json` (the shortcuts Setup created, so it can
remove stale ones). All are ignored by Git.

For normal development edit `../main.py`, `../settings.py` and `developer_settings.py`.
See the [backend internals](DONT_CHANGE/README.md) when maintaining the template itself.
