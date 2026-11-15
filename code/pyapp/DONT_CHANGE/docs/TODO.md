# TODO

Sections and items are ordered by priority: release blockers and reliability first,
then documentation, usability, integrations, and optional future features.
Questions are review tasks, not claims that a feature is missing or already implemented.

## 1. Release validation and publishing

- Complete [RELEASE_CHECKLIST.md](RELEASE_CHECKLIST.md) for the exact release candidate;
  record results and unresolved issues before release 1.0.0.
- Build the release ZIP with `pyapp_tools/release.bat`, verify it against the final tested
  commit, and attach it to the corresponding GitHub release.
- Test a fresh download, new app creation, and first use by someone else. Test moved and
  copied project folders and conversion of the template into an application.
- Test on Windows: Setup, first and second starts (the second should be fast), Stop on the
  example window, Logs/Settings/Edit-Code shortcuts, `status.cmd`, `change_python`,
  `make_self_contained`, and a failing `main.py` (black window, traceback, and No-Terminal grouping).
- Run `tests/run_launcher_tests.cmd` on Windows (`test_windows.py` and the batch/Stop paths
  are skipped elsewhere) and `pyapp_tools/verify_launcher.bat`.
- Test all developer and backend tools.
- Test offline portability of local installations and self-contained distributions.
- Test interrupted installations and verify that retrying leaves a working environment.
- Test multiprocessing in `main.py` under the wrapper.
- Test the supported Linux fallback behavior.
- Review Git hooks and GitHub workflows for the launcher and developer tools.
- Review simplification opportunities, robustness, startup speed, comments, docstrings,
  missing checks, and actionable error messages. Compare features across launch modes
  where the hosts support them.
- Tag the release on GitHub and review the repository description and topics.

## 2. Error handling and window lifecycle

- Test all Python-script and interpreter crash paths, including deliberately broken files,
  no-terminal runs with and without a custom GUI, and PySide6 crashes.
- Test a silent failure while minimized: no earlier prints, then an exception.
  Verify that `foreground_after_failure` restores the window.
- Validate the combinations in [WINDOW_LIFECYCLE.md](WINDOW_LIFECYCLE.md), especially
  foreground restoring from the tray and preserving normal/maximized placement.
- Check whether the tray's Stop action respects the intended stop/completion rules.
- Check whether a blocked X button should be re-enabled after completion.
- Review additional interpreter crash codes, including `0xC0000374` (heap corruption),
  `0xC0000135` (missing DLL), and divide-by-zero failures.
- Consider adding the package list and other useful environment details to crash reports.
- Verify that logs update live and remain viewable while the program runs.
- Review use of Python's `logging` package and the drawbacks of `-u`.
- Improve clickable traceback links in Windows Terminal: open `path:line` and the main
  script in a configurable editor (VS Code, Notepad++, or PyCharm). Check conhost limitations.
- Consider a graceful-stop callback so the app can save data and release hardware before
  forced termination; review `future/graceful_shutdown` and other useful app/backend helpers.

## 3. Documentation and onboarding

- Review all READMEs and check that the following existing features are explained clearly:
  - Developer tools, GitHub workflows, and automatic package mapping for missing imports.
  - Fast uv setup compared with classic pip installation; no preinstalled Python or uv;
    easy Python-version switching; isolation from global Python changes.
  - Supported Python versions, shared caches, small launcher footprint, and offline portability,
    including the environment and other files needed for a self-contained folder.
  - Minimal Linux support and selecting the Python executable in the Linux fallback script.
  - Ready-to-use licensing and Git ignore rules.
  - Fully reviewable, editable source and the tradeoffs of compilation: antivirus warnings,
    startup/build time, redistribution size, Git sharing, and bundled licenses.
  - Debugging and running without a terminal; stopping invisible background apps;
    automatic output logs and crash reports.
  - Readable tracebacks with launcher frames hidden, and status titles/icons after success or failure.
  - `settings.py` and its shortcut; exported app name, paths, and other environment variables,
    with small Tkinter/Qt examples (`PROGRAM_NAME`, `ICON_PATH`, `LOG_PATH`, `APP_ID`,
    `PROGRAM_HAS_TERMINAL`, and others).
  - Automatic shortcut creation in the project folder, Start Menu, and desktop;
    generating icons and variants from a PNG, and replacing individual `.ico` files.
  - Terminal/GUI taskbar grouping and the AppUserModelID carried by shortcuts;
    explain why integrating a custom launcher requires more than setting a window icon.
  - Compatibility with restrictive company-managed Windows settings.
  - Short internal paths to reduce legacy Windows path-length problems in deeply nested projects.
- Check screenshots and other published data for personal names or unintended information.
- Review screenshots/GIFs of shortcut icons, terminal appearance, taskbar grouping, and
  colored tracebacks. Check the comparison image of batch/terminal/Tkinter entries versus
  the app's single taskbar entry.
- Explain editor interpreter selection for `code/pyapp/generated/.venv`; VS Code/PyCharm may
  need explicit selection, and `uv add` must run in the generated project folder or through
  the developer tools.
- Add comments where Python or batch behavior is difficult for inexperienced readers to follow.
- Consider flowcharts for the launch and recovery paths.

## 4. Terminal and browser usability

- Improve Windows tray notifications and their recovery instructions.
- Make overlay icons more visible, darken the log icon for differentiation, and consider
  a folder overlay for folder shortcuts.
- Test developer-settings readability and organization.
- Test all browser-terminal buttons: labels, icons, order, and touchpad resizing; adjust
  the button order and consider configurable button visibility.
- Add configurable text wrapping where supported by conhost/WT, with a live browser toggle
  and a browser default setting.
- Review whether each developer setting is supported as far as possible in the browser terminal.
- Consider live toggles for print/input prefixes and timestamps; account for input synchronization
  and whether formatting must run in browser logic.
- Offer both Open Log and Open Log Folder if useful.
- Consider a clear running/completed indicator or busy animation; review its colors and meaning.
- Review additional browser-terminal feature ideas.

## 5. Windows integration

- Add actual taskbar progress percentages and status/overlay badges through an app-facing
  progress API (percentage, current operation, and estimated remaining time).
- Consider taskbar thumbnail controls, hover buttons, and shortcut context-menu customization.
- Check whether the X button can be hidden where supported.
- Consider a tray-minimize action separate from replacing the normal minimize action.
- Consider a maximize-on-start setting.
- Consider preventing sleep and optionally keeping the display awake; first document current behavior.
- Review Windows notifications: correct program name/AppUserModelID, clickable actions,
  and guidance when Windows blocks delivery. Check whether identity affects notification grouping.
- Consider an option to forward printed output to Windows notifications.
- Consider starting the app with Windows.
- Review opening code with the default associated application versus a configurable editor;
  ensure a `.py` association does not accidentally execute the script.
- Consider file associations for opening supported data files directly in the app.

## 6. Optional features

- Review startup laziness and measure opportunities to reduce startup work.
- Consider `restart_on_crash` / `restart_on_failure`, including an optional interpreter-crash
  recovery script, delay, retry limits, a time window, and immediate-failure/crash-loop protection.
  Clarify which failures benefit from automatic restart.
- Consider an execution timeout for stalled runs.
- Consider a setting for how to handle or prevent `KeyboardInterrupt`.
- Consider app/backend communication helpers beyond graceful shutdown and progress reporting.
- Add shortcuts with extra arguments: configurable `.lnk` and/or editable `.cmd` launchers;
  verify how additional arguments are forwarded.
- Add an explicit absolute/relative working-directory setting beyond script/shortcut folder selection.
- Consider generating VS Code interpreter settings for `code/pyapp/generated/.venv`.
- Consider a launcher update check with a link/changelog, skip-version and disable options,
  optional installation, and possibly a shortcut.
- Explore plotting directly in the terminal.
- Consider an optional, inexpensive browser resource monitor for CPU, memory, and disk usage,
  hidden by default or with configurable warning thresholds.

## 7. Compilation experiments

- Explore a Nuitka build command using the managed Python and `main_script`, with dependencies,
  the app icon, console/no-console outputs, and a cleanup command under `dev_tools`.
- Decide how to install Nuitka and expose editable compilation arguments/file lists while keeping
  a separate defaults script that can be copied into the developer's compilation configuration.
- Provide build presets for antivirus compatibility, small output, and fast startup.
- Consider GitHub Actions builds so the executable's relationship to the source is reviewable.
- Investigate faster repeated builds and the appropriate buffering/faulthandler/compiler options.
