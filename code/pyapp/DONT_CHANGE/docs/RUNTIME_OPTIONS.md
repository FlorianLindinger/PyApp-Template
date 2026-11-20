# Runtime options and host support

`start_maximized = False` maximizes the managed native terminal or browser window when enabled.
It takes precedence over `start_minimized`; it does not resize windows created by the app.
Windows Terminal gets a dedicated window for this setting. A browser may reuse an existing
window, so maximizing it can affect other tabs in that window.

`prevent_sleep = False` and `keep_display_awake = False` preserve Windows power behavior by
default. While the application process runs, each can request protection against its respective
automatic idle timer. The watchdog releases requests when the app ends, before completion
prompts, and also on errors; Windows releases them when the requesting thread/process exits.
Explicit Sleep, lid actions and enforced power policy can still suspend the computer. These
managed-launcher options do not change the direct standalone fallback or app GUI behavior.
See [Microsoft's execution-state API](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-setthreadexecutionstate).

`confirm_on_close = "block"` disables conhost's X while the app runs; X is re-enabled before
completion reporting. The tray's **Stop program** follows the Stop shortcut's policy: request
shutdown, wait `stop_timeout_seconds`, then terminate if needed. It deliberately bypasses
close blocking, Ctrl+C ignore/confirmation, completion prompts and crash recovery. Stop must
remain available when closing is blocked. A foreground/focus request restores hidden or
minimized terminals before requesting activation; already visible maximized windows stay
maximized. Windows may deny actual foreground focus. The tray removes its icon after an
external restore, and recreates it only on the next minimize.

## One recovery attempt

`after_interpreter_crash_script` may point to `main.py`, e.g. `"..\\main.py"`. It runs once
after a recognized native interpreter crash, in a fresh managed Python with the app's working
folder/environment. Its arguments are `args_for_main_py`, additional batch-launch arguments,
then a final `"crashed"`. For example:

```python
import sys

if sys.argv[-1:] == ["crashed"]:
    # Restore saved state or perform a bounded retry.
    pass
```

This is an unwrapped, noninteractive recovery process, with output in a separate `.recovery.log`.
Its own crash does not trigger recovery. `CRASH_RECOVERY=1` is inherited by its children;
if it deliberately invokes the launcher, that descendant run also cannot start recovery.
A later independent normal launch is eligible again. There is no timer-based retry loop.
Stop and ordinary exceptions/exits do not trigger it. Existing recognition includes heap
corruption, missing/failed DLLs and integer divide-by-zero; floating-point divide-by-zero,
invalid operation/overflow, integer overflow and in-page errors are also recognized. Statuses
are normalized from signed or unsigned NTSTATUS values. A Python `ZeroDivisionError` is an
ordinary reported exception, not a native crash.

## Batch entry points

Set `generate_batch_shortcuts_for_args_launch = True`, then run Setup. `batch_shortcuts` in
the project root contains a `.cmd` counterpart for every enabled project shortcut. Disabled
shortcut names produce no batch. Start batches append supplied arguments to `args_for_main_py`,
preserving empty arguments and quoted spaces through the Python/host handoff. Quote shell
metacharacters as usual when calling a batch file. Other batches open the matching project
shortcut. Stale generated batches are removed; unrelated files are preserved and never
overwritten. The folder is ignored by Git and regenerated after moving the project. No-terminal
entry points can show their calling console briefly and return after startup acknowledgement.

## Browser support

| Developer settings | Browser behavior |
| --- | --- |
| Python, packages, script/arguments, working folder, app environment, instance policy | Same managed backend |
| Logs, crash reports, recovery, Ctrl+C policy, Stop timeout | Same managed wrapper/watchdog |
| Print/input prefixes | Configured formats; separate remembered live on/off controls affect future console output; log prefixes stay unchanged |
| `wrap_terminal_output` | Initial Wrap lines value; remembered toolbar button/gear switch overrides it |
| `start_maximized` | Maximize browser window after locating it |
| `prevent_sleep`, `keep_display_awake` | Watchdog requests, independent of browser visibility |
| Colors, titles, icons, foreground on input/first output/completion | Page UI requests and host window activation, subject to browser/Windows restrictions |
| Close-after/completion actions, sounds, log opening, Windows notifications | Backend completion rules; tab closing can be refused by the browser |
| `confirm_on_close` | `close`, `prompt`, `hide`; `block` rejected because a browser cannot guarantee blocking |
| Native caption minimize/maximize buttons, terminal opacity, always-on-top, tray replacement | Native terminal controls; not applied to a potentially shared browser window |
| Taskbar animation/highlight/flash | Native terminal settings; browser page has its own activity/outcome indicator |
| Shortcut/open paths | Managed page open buttons follow enabled shortcuts and valid configured paths |

The page always shows a labeled activity indicator: animated blue **Running**, green **Finished**,
red **Failed**, or amber **Interrupted**. It stops at the app outcome, even while completion
waits for Enter. Reconnecting retains the reported outcome. A lost connection is labeled
**Disconnected** rather than claiming the app finished. Reduced-motion preferences disable
rotation without hiding the running state.

For the standalone `browser_terminal` folder, `settings.py` supplies `WRAP_OUTPUT` and `BUTTONS`.
`BUTTONS` selects toolbar controls; open controls also need their corresponding configured paths.
Managed starts use these same toolbar settings. Prefix toggles are exposed only for the managed
Python wrapper; arbitrary commands in the standalone terminal cannot have their output prefixes
changed by the host. Existing text is not rewritten by a live toggle.

## Communication from main.py

The existing public environment supplies paths/identity such as `PROGRAM_NAME`, `LOG_PATH`,
`PROJECT_DIR`, `ICON_PATH` and `APP_ID`. These are useful for naming a GUI, locating logs/settings,
and matching taskbar identity. For a managed browser run the existing request channel can report
application details, change the title/icon, request input attention or publish an explicit state:

```python
import os
from pyapp.DONT_CHANGE.browser_terminal import ui

if os.environ.get("BROWSER_TERMINAL_UI"):
    ui.request(info={"Operation": "Processing measurements"}, title="Processing")
```

Use the backend's normal completion reporting for the final outcome. A typed progress/operation
API, cooperative stop callbacks and checkpoint requests would be useful future extensions;
no general bidirectional RPC or hardware-control API is introduced here. Application-created
GUI windows still own their own controls and geometry.

## Validation presentation

Hooks and maintainer tools share ANSI formatting in terminals, with support for GitHub Actions
and `FORCE_COLOR=1` logs. `NO_COLOR` or `FORCE_COLOR=0` forces plain text. Test-run headings and
parallel summaries use the same colors; original compiler diagnostics and tracebacks remain
intact. Git clients without ANSI support receive plain output by default.

See [app compilation tools](../../compilation/README.md) for Nuitka builds and the managed
Python syntax-validation command. Compilation does not automatically embed launcher services.
