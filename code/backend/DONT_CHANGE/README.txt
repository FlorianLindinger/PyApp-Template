PyApp-Template backend internals
================================

This folder contains the backend code copied from PyApp-Template:
https://github.com/FlorianLindinger/PyApp-Template

It is named DONT_CHANGE because normal app customization should happen in
the files outside this folder, especially:

- code/main.py
- code/settings.py
- code/developer_settings.py
- code/icons
- code/developer_tools

The backend code here is responsible for shortcut startup, local Python
handling, package installation helpers, logging, terminal behavior, and error
handling around the user-facing Python app.


Backend and frontend terminology
================================

In this project, "backend" means the launcher and support code that makes the
app portable and easy to start.

Inside this folder, "backend Python" means the small embedded Python runtime
used to run the launcher/support scripts. "Frontend Python" means the full local Python installation that runs code/main.py.


Folder contents
===============

- B
  Short batch files used as shortcut targets. The short names help avoid
  Windows shortcut target length limits and keep startup paths predictable.

- ascii_fonts
  ASCII-art font data used by backend terminal output.

- backend_packages
  Third-party Python packages used only by the backend launcher/tooling code.
  The expected package list is documented in backend_packages_list.txt.

- backend_python
  Embedded Python distribution used by backend scripts. It is modified during
  backend setup; see scripts/setup/finish_backend_installation.py and
  backend_python/LICENSE.txt.

- backend_test_tools
  Local helper scripts for measuring startup/import times and testing backend
  launch behavior.

- future
  Notes, experiments, and deferred ideas for future PyApp-Template work.

- icon_related
  Backend icon resources and icon-generation support files.

- scripts
  Main backend Python scripts. Important entry points include start_program.py,
  background_washdog.py, open_settings.py, open_log.py, and stop_program.py.

- temporary
  Temporary backend working folder. Generated files here should not be treated
  as project source.


Important files
===============

- LICENSE.md
  Composite license for this folder, the embedded backend Python runtime, and
  bundled backend packages.

- backend_packages_list.txt
  Source list for backend-only Python packages.

- PyApp-Template_TODO.txt
  Development notes for the template itself.

- PyApp-Template_VERSION_x.y.txt
  Version marker for the copied backend template.

- .gitignore and .gitattributes
  Git rules for keeping generated or redistributability-sensitive files under
  control.


Distribution notes
==================

If you distribute this folder, keep LICENSE.md and the license/metadata files
inside backend_python and backend_packages. If you change bundled packages,
update both backend_packages_list.txt and LICENSE.md.

If you only build an app from the template, prefer changing the files outside
DONT_CHANGE instead of editing these internals. That keeps future template
updates easier to apply.
