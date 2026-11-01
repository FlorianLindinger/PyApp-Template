# Application backend

Configure the application in [developer_settings.py](developer_settings.py).
Change application dependencies using the batches in [dev_tools](dev_tools/README.md).
That guide explains how to install, remove, upgrade and save package defaults.

The generated `python/` and `packages/` folders are maintained by those tools.
The launcher's own Python and dependencies are separate, inside `DONT_CHANGE`.
Application packages belong in the application environment.

For normal development, edit `../main.py`, `../settings.py`,
`developer_settings.py` and `dev_tools/DEFAULT_PYTHON_PACKAGES.txt`.
See [backend internals](DONT_CHANGE/README.md) when maintaining the template itself.
