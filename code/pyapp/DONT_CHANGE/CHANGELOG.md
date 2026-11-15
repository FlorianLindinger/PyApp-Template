# PyApp-Template launcher changelog

Changes of this `DONT_CHANGE` folder. Versions follow Semantic Versioning as described in
README.md ("Versions"); `LAUNCHER_VERSION` in `backend_settings.py` names the current one.

## 0.0.1 - unreleased

The first versioned release; it contains every change below.

### 2026-11-15

- Always include the code folder on the application's import path for normal and fallback starts, retaining main-script-folder precedence so nested entry scripts can import shared root modules and code/settings.py.
- Print the actual unique crash-log filename immediately below the traceback after a successful write; make it clickable through Windows Terminal hyperlinks and browser-terminal file links, with plain paths elsewhere.
- Let Linux fallback users choose a Python executable or versioned command with python_command at the top of the shell file; default to system Python on PATH and remove automatic generated-environment probing. Keep explicit selections strict, paths quoted and dependencies user-managed.
- Make missing-file diagnostics actionable: name the path setting, offer correcting it or restoring the file, explain optional-file disablement and remind users to regenerate shortcuts after path changes.
- Send explicit browser-terminal titles and embedded status icons, including on automatic close, so completion appearance survives server shutdown. Add completion regressions, a settings-print button to the Tkinter example, settings-path/import guidance and rendered traceback images in the README.
- Leave generated shortcuts' Start in empty and rename the working-folder setting to start_in_shortcut_position: True keeps the Windows-supplied starting folder; False selects the main script's folder. Preserve explicit working-directory overrides and accept the legacy setting name for existing projects; document Setup regeneration and inherited-folder semantics.
- Protect the pyapp source tree from parent ignore patterns, re-exclude local caches/environments and allow only four portable generated files. Preserve nested temporary/release exclusions and test broad parent patterns, runtime artifacts and the excluded-ancestor limitation using real disposable Git repositories.
- Use a bold cyan fallback-start heading instead of a yellow background for better terminal readability.
- Add Start without launcher --LINUX.sh, preferring a working Linux .venv and falling back to Python 3.8+ on PATH. Reuse the standalone fallback helper with portable configured paths, Linux diagnostics and no Windows-icon injection or terminal pause; enforce LF for shell files and cover native Linux selection/argument/error behavior.
- Capture bounded, unredacted local/global variable representations in application traceback reports, including chains/groups and captured thread/shutdown errors. Add v to the close/recovery prompts to append the snapshot to the crash log (or export a separate system-temp text file) and open it; keep original tracebacks, automatic-close behavior and reports without frames intact.
- Add independent foreground_after_success=False and foreground_after_failure=True settings. Ctrl+C never requests completion foreground attention. Restore/focus classic-console or browser completion windows only when kept open, after other completion actions, preserving automatic-close behavior and reports if focus is denied.
- Make Git-hook headlines actionable from their first line: translate common test and repository failures into repairs, summarize multiple failures, name formatting/lint fixes and compatibility registrations, prioritize secret findings and explain commit-history repairs, and add clear context when a hook tool cannot run. Keep full diagnostics and file links below the headline.
- Fix CRLF endings in the new package-tool command files and register/document test_app_environment.py in the app test group and test-file table.
- Add foreground_on_first_print (off by default) for one-time classic-console/browser focus on the app's first stdout/stderr output, including imported modules. Keep hidden starts and pseudoconsole message windows hidden; attention failures cannot interrupt printing.
- Expose completion/button icon paths, rendered success/failure titles, resolved user settings/log/crash-log paths, project root and original start folder to the application through environment variables. Disabled paths are empty and path export creates no folders; launcher version is not exported.
- Register install-requirements and reset-imports as protected Developer Tools commands; report missing command registrations by name instead of dumping assertion lists into Git popups, and clarify the repair instructions.
- Install the highest matching stable uv release for uv_version ranges, checking all release-list pages and Windows archive/checksum availability instead of downloading latest and rejecting it. Keep exact-pin, unrestricted and matching-bootstrap download paths; preserve installed uv on lookup failure.
- Add Developer Tools commands to reset package declarations to reviewed imports (keeping retained constraints and requirements_path packages) and import a requirements file with uv add -r; provide standalone .cmd launchers and regression coverage.
- Capture errors from application `atexit` callbacks registered on Python 3.8/3.9, preserving native shutdown order, callback arguments, decorator returns and equality-based unregistration. Document the workaround's pre-setup registration limit.
- Clarify other Git-hook headlines: name failing launcher tests/checkers, explain compatibility and missing changelog failures, distinguish staged leaks from leaks in pushed commits, and give a Setup action when Python is missing.
- State explicitly in the blocked-push headline that developer settings do not match the fallback developer settings, using short filenames; keep full paths in the detailed diff.
- Add working folder, settings paths, crash-log folder, and the actual per-run log file to browser run info. Supply launcher metadata through a generic info-update API so the browser-terminal package remains reusable.
- Show the browser-terminal package folder in the browser run-info panel.
- Use `</>` for the browser code button and document symbols for logs and crash logs; add a crash-log folder button when its shortcut is enabled.
- Move notification options into their own section of the browser gear menu and remove the separate bell button.
- Add an OK button to dismiss the browser bookmark panel and return focus to the terminal.
- Clip browser-terminal selection highlights to each line's text and keep an arrow pointer over the terminal, with a hand for links.
- Browser terminal: zoom in steps of about 15 % (Ctrl+/-, Ctrl+wheel) and smoothly with a touchpad pinch, redrawn at most once per frame; files and folders opened from the page, and the page after clicking one of its notifications, come to the front.
- The raw output is written to the run folder in `tmp\runs` while the app runs; only after a failure with output is it moved next to the log as `.output.log`.
- Browser terminal: new `settings.py` with the defaults of every terminal (font, cursor, colors, zoom, scrolling, the gear menu's switches, notifications, bringing opened windows to the front).
- Enlarge the browser toolbar icons and buttons. Batch fractional touchpad scrolling once per frame, pause following while reading scrollback, and prevent pending output writes from overriding touchpad movements.

### 2026-??-?? - initial release

