# App compilation

The developer menu and this folder provide three tools:

- `validate_syntax.cmd`: use the managed app Python's compiler on app `.py` files. It checks
  syntax without importing/executing the app or writing bytecode. CPython normally compiles
  code when running/importing it; this catches syntax problems ahead of a run. It does not
  check imports, types, runtime behavior, or compiler packaging.
- `compile_app.cmd terminal --mode standalone`: build `main_script_path` and its dependencies
  with the managed Python and Nuitka. `no_terminal` builds without a console. `--mode onefile`
  makes a single executable; `--dry-run` prints the command without compiling/installing.
- `clean_compilation.cmd`: remove only this tool's marked output under
  `code/pyapp/generated/compilation`. Shared compiler caches are preserved for later builds.

Nuitka and a supported C compiler must already be available. Nothing is installed automatically.
Open the dev tool `terminal`, then explicitly install the build dependencies if wanted:

```bat
uv pip install nuitka ordered-set zstandard
```

Build requirements belong in your build environment, rather than the app's runtime package
list unless the app itself needs them. Re-syncing the app environment may remove build tools.
The shipped JSON `compilation_settings.json` is developer-owned and survives replacing
`DONT_CHANGE`; use its `extra_args` list for Nuitka plugins, data files and resource options.
Arguments are passed separately without a shell. Relative resource paths start at `code`.
Output/report overrides are reserved by the tool. Each build writes a Nuitka XML report.

Start with standalone mode and test that folder on a clean target computer before onefile.
These compile the **app entry script**; launcher supervision, logs, browser controls, recovery,
and developer settings are not automatically embedded in the executable. An app that needs
those services should continue using the folder launcher, or implement its required runtime
services explicitly. In particular a no-console executable needs its own visible error UI/logs.
There is no antivirus-safe preset or guarantee that a successful build will run on every PC.
Build on the target OS/architecture with a supported Python/compiler; these Windows tools are
not a cross-compiler for Linux/macOS. Actual executable smoke tests are separate from syntax
validation and should use the app's own safe test mode.

Nuitka documents `--python-flag=unbuffered` for apps needing immediate stdout/stderr writes.
It can be added to `extra_args`; no speculative flag is enabled by default. App-level
`faulthandler.enable()` requires a suitable diagnostic stream, particularly without a console.

References: [Nuitka manual](https://nuitka.net/user-documentation/user-manual.html),
[standalone/onefile workflow](https://nuitka.net/user-documentation/use-cases.html),
[data paths and no-console diagnostics](https://nuitka.net/user-documentation/common-issue-solutions.html),
[compiler caches](https://nuitka.net/user-documentation/tips.html).
