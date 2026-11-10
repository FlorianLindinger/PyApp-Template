# generated

Files the launcher creates for this app: mostly what uv needs to run it. The launcher creates and maintains this folder, so you normally don't edit anything here. Change packages and the Python version in `../developer_settings.py` or with the tools in `../dev_tools`.

| Item | What it is | Git |
| --- | --- | --- |
| `uv.lock` | Exact package versions, with hashes | Commit |
| `.python-version` | The Python version the project uses | Commit |
| `auto_generated_icons.json` | Which icons in `../icons` the generator made, so it can update those and ask about the rest | Commit |
| `pyproject.toml` | Generated from `developer_settings.py`; don't edit it | Ignored |
| `.venv/` | The app's Python environment | Ignored |
| `uv/` | Local copy of uv (only with a local uv, for example after `make_self_contained`) | Ignored |
| `pythons/` | Python installed for this project (only with `python_source = "local"`) | Ignored |
| `uv-cache/` | uv's download cache (only with `uv_cache = "local"`) | Ignored |
| `shortcuts_created_by_setup.json` | Which shortcuts Setup created on this PC, so it can remove old ones | Ignored |

Deleting `.venv/` is safe: the next start rebuilds it. If you delete `uv.lock`, the next start creates a new one, but package versions may change.
