# env

Everything uv needs to run this app. The launcher creates and maintains this folder, so you normally don't edit anything here. Change packages and the Python version in `../developer_settings.py` or with the tools in `../dev_tools`.

| Item | What it is | Git |
| --- | --- | --- |
| `uv.lock` | Exact package versions, with hashes | Commit |
| `.python-version` | The Python version the project uses | Commit |
| `pyproject.toml` | Generated from `developer_settings.py`; don't edit it | Ignored |
| `.venv/` | The app's Python environment | Ignored |
| `uv/` | Local copy of uv (only with a local uv, for example after `make_portable`) | Ignored |
| `pythons/` | Python installed for this project (only with `python_source = "local"`) | Ignored |
| `uv-cache/` | uv's download cache (only with `uv_cache = "local"`) | Ignored |

Deleting `.venv/` is safe: the next start rebuilds it. If you delete `uv.lock`, the next start creates a new one, but package versions may change.
