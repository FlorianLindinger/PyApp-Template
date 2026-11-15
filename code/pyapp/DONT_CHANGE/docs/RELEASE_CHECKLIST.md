# Launcher release checklist

Keep release guidance in `docs`, linked from the launcher README: it describes the release process;
`pyapp_tools` contains the commands that perform it. Copy this checklist into the release notes
or an issue for each candidate. Record **passed**, **failed**, or **not run** with evidence;
an automated pass does not replace the desktop checks below.

Candidate commit: __________  Version: __________  Date/tester: __________
Windows version: __________  Python versions: __________  WT/browser versions: __________
Evidence (command output, logs, screenshots): __________

Run commands from the repository root in PowerShell. Use the project's configured environment:

```powershell
$releasePython = '.\code\pyapp\generated\.venv\Scripts\python.exe'
$releaseTools = '.\code\pyapp\DONT_CHANGE\pyapp_tools\src'
```

## 1. Prepare the candidate

- [ ] Review the diff, intentional default changes in both developer-settings files, and
  `CHANGELOG.md`. Check compatibility registrations and the protected baseline.
- [ ] Commit the intended files. Record `git rev-parse HEAD` and `git status --short`.
  Run the release checks from a clean checkout of that commit, so local preferences cannot
  affect the evidence. Keep experimental settings changes in a disposable copy.
- [ ] Run `& $releasePython "$releaseTools\check_all.py"`; require no failed or skipped checks.
  This includes Ruff lint/format, strict Pyrefly, repository/leak/changelog checks and regressions.

## 2. Validate installation and supported Pythons

- [ ] Run `& $releasePython "$releaseTools\test_all_pythons.py"` for Python 3.8 and the newest
  stable Python. Record the actual versions and any platform skips.
- [ ] Run `& $releasePython "$releaseTools\fresh_clone_test.py"`. Require the fresh Setup,
  hidden launch/output log, Python error, hard crash, offline restart, moved-folder restart
  and refreshed shortcuts to pass. This command tests committed files in a temporary clone.
- [ ] In a disposable copy, check a missing-package recovery menu and a self-contained/offline
  distribution. Confirm Stop ends child processes and a second app instance stays independent.

## 3. Check the desktop

Use a small probe that prints, waits, and can finish successfully, raise an exception or receive
Ctrl+C. Follow [window lifecycle rules](WINDOW_LIFECYCLE.md); record unsupported options separately.

| Host | Required manual check | Result/evidence |
| --- | --- | --- |
| Classic console | Normal and maximized minimize-to-tray cycles; restore removes icon and preserves placement; start minimized; allowed/hidden caption buttons and close policy | |
| Dedicated Windows Terminal | Same tray/placement checks; no other WT window/tab affected; configured alpha and always-on-top | |
| Both native hosts | Finish while hidden: success/failure with foreground off/on, Ctrl+C, automatic close, missing-module recovery; animation clears, green/red highlight and flash match settings | |
| Both native hosts | Restart Explorer while hidden in a disposable desktop/session; window becomes accessible and no stale tray icon remains | |
| Browser terminal | Input, Ctrl+C, resize, logs, completion title/icon, close/prompt/hide policies and browser notification permission | |
| No terminal / app GUI | Logs, failure report, Stop and configured completion notifications; native terminal controls do not alter the app GUI | |

- [ ] Check notification text, tray recovery instructions and repeated minimize notices with
  Windows notifications enabled. With Do not disturb/notifications disabled, verify recovery
  still works and diagnostics explain blocked completion notifications.
- [ ] Check multi-monitor placement/DPI and keyboard restore/focus. A simulated `TaskbarCreated`
  regression is useful evidence, but does not replace the real Explorer restart above.

## 4. Build and verify the release artifact

- [ ] Run `& $releasePython "$releaseTools\release.py" patch` (or the intended `minor`, `major`,
  or explicit version). Use the full checks; `--quick` is for iteration. The tool changes the
  version, changelog and protected baseline, creates a ZIP, and does not commit or publish.
- [ ] Review and commit those release changes. Record the final commit, rerun sections 1 and 2
  on it, and repeat desktop checks if anything besides release metadata changed.
- [ ] Check the ZIP version/content against that final commit. Install it into a disposable
  existing project, run Setup and verify its code, settings, environment and shortcuts survive.
- [ ] Record remaining limitations and every **not run** item before publishing the exact
  tested commit and artifact. Any subsequent code change creates a new candidate.
