# Runtime settings and implementation notes

## Working folder

`working_directory = ""` preserves `start_in_shortcut_position`. A nonempty value takes
precedence: use an absolute path or a path relative to `code/pyapp/developer_settings.py`,
such as `".."` for the code folder. The folder must exist. This changes the app's working
directory, not its import paths. The Windows/Linux fallback start also honors this setting.
`WDIR_IS_SCRIPT_DIR` reflects an explicit directory correctly.

## Ctrl+C

`keyboard_interrupt_action` accepts:

| Value | Behavior in the managed app |
| --- | --- |
| `"interrupt"` | Normal SIGINT / KeyboardInterrupt handling (default). |
| `"ignore"` | Ignore Ctrl+C / SIGINT while app code runs. |
| `"confirm"` | Show a Windows Yes/No dialog, defaulting to No; Yes raises KeyboardInterrupt. |

The dialog does not read from or write to an interrupted Python stream. Repeated Ctrl+C
while it is open does not create another dialog. If Windows cannot show it, interruption
remains possible. Explicit Stop/replacement requests bypass ignore/confirmation and retain
the existing forced-stop timeout. This does not block Ctrl+Break, Task Manager, explicit
`raise KeyboardInterrupt`, or signal handlers installed later by the app. Completion menus
and the direct fallback start retain their own behavior.

Python runs signal handlers on its main interpreter thread; long-running native operations
can delay them. This setting does not make uninterruptible native code immediately responsive.
See the [official signal documentation](https://docs.python.org/3.14/library/signal.html).

## Cleanup after an interpreter crash

`after_interpreter_crash_script = ""` is disabled. Otherwise provide an absolute path or a
path relative to developer settings. A recognized hard interpreter crash without a wrapper
completion report launches it once, directly, in a fresh managed app Python. Ordinary exceptions,
`sys.exit`, Ctrl+C, Stop and watchdog errors do not trigger it. Detection uses the existing
native-crash-code classifier; not every possible abrupt exit can be identified as a crash.

The script inherits the app's chosen working folder/environment and receives:

- `CRASH_EXIT_CODE`: the original native exit status.
- `CRASH_MAIN_SCRIPT`: the original main-script path.
- `CRASH_RECOVERY_LOG`: its output log path.

It is non-interactive (stdin is NUL). Stdout/stderr go to a separate `.recovery.log` beside
the app log, or `tmp/runs/<run-id>/crash-recovery.log` when app logging is disabled; the latter
is temporary. The normal crash window names the recovery log or reports a launch failure.
The original crash report and completion policy still run, without waiting for cleanup.

Write a short, bounded repair/cleanup routine. This is not a replacement managed app: it is
not supervised by Stop, does not recursively invoke crash recovery, and does not restore lost
in-memory state. It can outlive the original watchdog; its log is not a completion report.

## Start when signing in to Windows

Set `start_on_windows_start = True` and run Setup. `windows_startup_launch_mode` selects
`"no_terminal"` (default), `"terminal"` (configured conhost/WT), or `"browser"`.
Setup creates a shortcut in this user's Startup folder, using the existing launchers and
app identity. A project-specific filename suffix distinguishes copies with the same app name.
No administrator rights, scheduled tasks or machine-wide registry entries are needed.

Set the option back to False and rerun Setup to remove the generated entry. It is recorded
with the other owned shortcuts, so stale entries and manual shortcut removal use the existing
cleanup rules. Unrelated files are not overwritten. The normal configured startup/window
behavior still applies, including showing a failure report after a no-terminal failure.

## Is logging useful here? What about `-u`?

Python's standard-library `logging` is useful for application levels, named components and
structured events. It can write to stderr, which the launcher already captures. It does not
replace this launcher's stream mirroring/native-output capture: it cannot automatically turn
arbitrary `print`, native writes and subprocess output into logging records. The launcher
should not configure the application's root logger or duplicate its handlers.
See the [Logging HOWTO](https://docs.python.org/3.14/howto/logging.html).

`-u` disables Python stdout/stderr buffering; it does not affect stdin. It can make small,
frequent writes more expensive because they cannot be batched, and it does not control C
libraries' own buffers, other programs' buffers, unrelated open files, or disk durability.
The current app flags do not add `-u`; the wrapper already flushes mirrored text/binary output
and log writes. Keep that behavior rather than adding a redundant global switch without a
workload-specific latency/throughput measurement.
See [Python's `-u` option](https://docs.python.org/3.14/using/cmdline.html#cmdoption-u).

## Startup laziness review (2026-11-15)

Startup is reasonably lazy, but not maximally lazy. The entrypoint loads the selected tool;
environment validation has a fingerprint fast path; notifications, sounds, browser helpers,
tray controllers and the new optional actions are generally conditional. Recovery does no
launch work unless configured and triggered; the Startup folder is queried only by enabled Setup.

Import-only profiles on this checkout's Python 3.14.9 (`-I -S -X importtime`) observed about
186 ms cumulative imports for `actions.start_program`, 220 ms for `runtime.bg_watchdog`, and
112 ms for `scripts.entrypoint`, in separate fresh interpreters. These are single local
observations, not end-to-end launch measurements. `start_program` still imports environment
management eagerly (about 52 ms inclusive in that sample), and the launch chain starts several
Python processes. There is room to investigate, but moving imports alone does not remove work
that every run needs and can postpone useful errors. No speedup is claimed or applied here.

Use `pyapp_tools/get_startup_time.bat` for an end-to-end warmed comparison before changing the
launch architecture. Import profiling is documented under
[Python's command-line options](https://docs.python.org/3.14/using/cmdline.html#cmdoption-X).
