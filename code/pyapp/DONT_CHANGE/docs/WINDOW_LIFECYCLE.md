# Window lifecycle rules

These rules coordinate `terminal_window`, `standalone/system_tray`, `taskbar_status`, `console_tools`,
`process_exit` and `bg_watchdog`. They describe existing settings and the order in which they apply.

## Ownership and host capabilities

Native controls apply only to the remembered terminal handle, with its owning PID checked again
before use. Conhost supports caption-button controls and `confirm_on_close="block"`.
WT uses a dedicated window for window-wide options; other WT tabs/windows must remain untouched.
Browser close/prompt/hide behavior belongs to the browser terminal; native tray, taskbar,
alpha and topmost controls do not manage the browser or an application's own GUI.

`wrap_terminal_output` defaults to True. For conhost/WT the watchdog sets the native
`ENABLE_WRAP_AT_EOL_OUTPUT` mode before starting the app, preserving other console flags.
False can overwrite the rightmost buffer cell; it does not create horizontal scrolling.
The browser instead resizes its xterm/ConPTY pair together: wrapping fits the viewport,
while off uses a horizontally scrollable 1,000-column terminal. The live gear-menu switch
is remembered and overrides the developer default. Longer lines still wrap at 1,000 columns.
Redirected files/pipes and the full text saved in logs are not reformatted by this setting.

`allow_minimize=False` disables the normal conhost minimize route. Hiding its minimize button
removes that route too. Tray replacement observes an actual minimized window; it does not
override those restrictions or turn browser hide into native minimize-to-tray.

## Native transitions

| Starting state / event | Next state and required effects |
| --- | --- |
| Visible normal or maximized; minimize with tray replacement off | Ordinary Windows minimized state; no launcher tray icon. |
| Visible normal or maximized; minimize with tray replacement on (including start minimized) | Register a recovery icon **before** hiding. Preserve Windows' normal placement/maximized restore state. Request one explanatory tray notification per minimize cycle, titled with the app name and using its icon. Request immediate delivery; discard rather than queue stale notices. |
| Icon creation or notification request fails | Keep/restore access to the terminal; record diagnostics. Never leave it hidden without a recovery route. Windows may accept a notification but suppress its banner. |
| Hidden; tray icon/notification click or Restore menu | Restore and request foreground; remove the tray icon. A second restore callback must not unmaximize an already visible maximized window. |
| Hidden; another launcher foreground request restores it | The timer notices visibility and removes the icon. No second minimize/restore cycle is required. |
| Hidden; Explorer broadcasts `TaskbarCreated` | Treat the old icon as lost, restore the window immediately, and leave no icon for the now-visible window. Recreate one on its next minimize. |
| Visible; Explorer restarts | Keep placement/state; no idle tray icon is created. |
| Hidden; controller fails | Restore access and remove any surviving icon. |
| Hidden; normal watchdog shutdown | Remove the icon; return a surviving terminal to the taskbar minimized, without foreground activation. Normally the launcher-owned terminal then exits. |
| Handle disappears or its owner changes | Do not operate on the reused handle; clean up the controller's icon/thread. |

The launcher relies on Windows' saved placement instead of rewriting screen coordinates.
Always-on-top and alpha are window properties, independent of normal/maximized/minimized/hidden
state. They do not authorize an extra foreground request.

## Completion priority

1. Determine `stays_open`: `close_after_<outcome> is False` or recovery explicitly requires
   `keep_open=True`. Recovery owns its menu; the normal completion wait must not run twice.
2. Write the report/logs and apply configured title/icon/sound/notifications. Closing does not
   suppress configured completion notifications. Ctrl+C has no success/failure sound.
3. Only a kept-open success/failure with `foreground_after_<outcome>=True` restores/requests
   foreground. Ctrl+C never requests completion foreground. Windows may deny focus.
4. Finish taskbar activity even if the remembered terminal is hidden. A kept-open success/failure
   may receive steady green/red and/or flashing attention. Closing and Ctrl+C clear running activity.
   Attention does not restore a hidden window; native taskbar appearance while hidden is Shell-dependent.
5. Wait if kept open, unless recovery owns the interaction. Without foreground enabled, hidden
   completion remains recoverable from its tray icon until the user restores/closes it.
6. Watchdog cleanup removes the icon and stops the controller after completion/recovery finishes.

First-print foreground is a separate, one-time request while the application runs. If it restores
a hidden terminal, the same visibility timer removes the icon. Browser foreground requests use
the browser UI, and a no-terminal run has no native terminal to restore.

## Evidence and remaining manual checks

`tests/src/test_system_tray.py` covers repeated cycles, external/duplicate restore, icon and
notification failures, owner safety, Explorer's restart message and native conhost cleanup.
Its live conhost probe checks normal geometry, maximized restoration, duplicate callbacks,
and drives caption-system commands through `SendMessageTimeoutW` to acknowledge the conhost
UI thread. It observes the restored/maximized state before advancing; acknowledging the tray
thread alone does not establish the console window's transition order. It also checks
simulated Explorer recovery and quiet shutdown. It deliberately delays tray callbacks and
acknowledges their completion before the next transition; fixed sleeps do not establish event
ordering on a busy desktop. It does not restart the user's Explorer.
The native probe intercepts balloon-delivery requests while validating their app title/icon
and count; icon creation/removal and window operations still use Windows. Automated validation
does not display tray balloons. Real banner appearance remains a manual release check.
The separate native taskbar/console API probe stays hidden by default; set
`PYAPP_TEST_VISIBLE_WINDOWS=1` to inspect it visibly. The tray lifecycle probe retains its
real visible minimize/restore/maximize operations: hiding or isolating its target changes
Windows behavior and made the check unreliable. No native assertions are skipped to make
validation quieter. Background checker/WPF workers do not open extra consoles, and their
captured diagnostics are preserved.

`tests/src/test_completion_attention.py` checks close/keep-open/foreground combinations for all
three outcomes, hidden-window taskbar completion, activity/highlight/flash and notifications.
`test_terminal_window.py` covers host capabilities and window styles. These regressions cannot
prove WT/Shell rendering, notification banner delivery or multi-monitor/DPI behavior; use the
[release checklist](RELEASE_CHECKLIST.md) for those desktop checks.
