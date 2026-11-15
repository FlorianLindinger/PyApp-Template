# PyApp-Template launcher changelog

Changes of this `DONT_CHANGE` folder. Versions follow Semantic Versioning as described in
README.md ("Versions"); `LAUNCHER_VERSION` in `backend_settings.py` names the current one.

## 0.0.1 - unreleased

The first versioned release; it contains every change below.

### 2026-11-15

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

