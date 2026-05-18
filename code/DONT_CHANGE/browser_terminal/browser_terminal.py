"""Run a Python script in a real browser terminal using xterm.js and pywinpty."""

import atexit
import html
import json
import mimetypes
import os
import secrets
import subprocess
import sys
import threading
import time
import traceback
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlparse

# add root dir for debug cases where this script is called on its own:
root_dir = os.path.dirname(__file__) + "\\..\\.."
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from winpty import PtyProcess

from DONT_CHANGE.specific_scripts.launcher_common import (
    CompletionAlerts,
    ProcessIdRegistry,
    TerminalLogger,
    arg_to_bool,
    arg_to_wav_path,
    create_signal_file,
    looks_like_interpreter_crash,
)

MAX_STORED_EVENTS = 10000
SHUTDOWN_AFTER_CLOSE_SECONDS = 0.4
DEFAULT_ROWS = 30
DEFAULT_COLS = 100

ASSET_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "browser_terminal_assets"))


def run_text_in_new_terminal(text: str) -> None:
    subprocess.Popen(  # noqa:S603
        [sys.executable, "-X", "faulthandler", "-c", text],
        creationflags=getattr(subprocess, "CREATE_NEW_CONSOLE", 0),
    )


def show_browser_open_failure(url: str, error: BaseException | None = None) -> None:
    error_text = "" if error is None else f"\nAutomatic browser opening failed:\n{error!r}\n"
    script = f"""
print({error_text!r})
print("Browser terminal is running at:")
print({url!r})
print()
input("Copy/open the URL above, then press Enter to close this helper window.")
"""
    try:
        run_text_in_new_terminal(script)
    except Exception:
        print(error_text)
        print(f"Browser terminal is running at: {url}")


def open_browser(url: str, start_minimized: bool) -> bool:
    if start_minimized and os.name == "nt":
        try:
            import ctypes

            SW_SHOWMINNOACTIVE = 7
            result = ctypes.windll.shell32.ShellExecuteW(None, "open", url, None, None, SW_SHOWMINNOACTIVE)
            return int(result) > 32
        except Exception:
            pass

    return webbrowser.open(url)


class BrowserTerminalState:
    def __init__(
        self,
        *,
        title: str,
        app_id: str,
        close_on_success: bool,
        close_on_failure: bool,
        open_log_file_after_success: bool,
        open_log_file_after_failure: bool,
        open_log_file_after_python_interpreter_crash: bool,
        play_sound_on_success: str,
        send_Windows_notification_on_success: bool,
        play_sound_on_failure: str,
        send_Windows_notification_on_failure: bool,
        play_sound_on_python_interpreter_crash: str,
        send_Windows_notification_on_python_interpreter_crash: bool,
        logger: TerminalLogger,
        registry: ProcessIdRegistry,
    ) -> None:
        self.title = title
        self.app_id = app_id
        self.close_on_success = close_on_success
        self.close_on_failure = close_on_failure
        self.alerts = CompletionAlerts(
            title=title,
            app_id=app_id,
            log_path=logger.path,
            play_sound_on_success=play_sound_on_success,
            send_windows_notification_on_success=send_Windows_notification_on_success,
            play_sound_on_failure=play_sound_on_failure,
            send_windows_notification_on_failure=send_Windows_notification_on_failure,
            play_sound_on_python_interpreter_crash=play_sound_on_python_interpreter_crash,
            send_windows_notification_on_python_interpreter_crash=send_Windows_notification_on_python_interpreter_crash,
            open_log_file_after_success=open_log_file_after_success,
            open_log_file_after_failure=open_log_file_after_failure,
            open_log_file_after_python_interpreter_crash=open_log_file_after_python_interpreter_crash,
        )
        self.logger = logger
        self.registry = registry
        self.pty_process: Any = None
        self.child_process_id: int | None = None
        self.exit_code: int | None = None
        self.shutdown_server: Any = None

        self._events: list[dict[str, Any]] = []
        self._next_event_id = 1
        self._condition = threading.Condition()
        self._pty_lock = threading.RLock()

    @property
    def process_running(self) -> bool:
        return self.pty_process is not None and self.pty_process.isalive()

    def add_output(self, text: str, *, log: bool = True) -> None:
        if text == "":
            return

        if log:
            self.logger.write(text)

        with self._condition:
            event = {"id": self._next_event_id, "text": text}
            self._next_event_id += 1
            self._events.append(event)
            if len(self._events) > MAX_STORED_EVENTS:
                del self._events[: len(self._events) - MAX_STORED_EVENTS]
            self._condition.notify_all()

    def get_events_after(self, event_id: int, timeout_seconds: float = 20.0) -> list[dict[str, Any]]:
        deadline = time.monotonic() + timeout_seconds
        with self._condition:
            while not any(event["id"] > event_id for event in self._events):
                if self.exit_code is not None:
                    break
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    break
                self._condition.wait(remaining)
            return [event for event in self._events if event["id"] > event_id]

    def send_input(self, text: str) -> None:
        if not self.process_running:
            return

        try:
            with self._pty_lock:
                self.pty_process.write(text)
        except Exception as error:
            self.add_output(f"\r\n[failed sending input: {error}]\r\n", log=False)

    def resize(self, cols: int, rows: int) -> None:
        if cols <= 0 or rows <= 0 or not self.process_running:
            return

        try:
            with self._pty_lock:
                self.pty_process.setwinsize(rows, cols)
        except Exception as error:
            self.add_output(f"\r\n[failed resizing terminal: {error}]\r\n", log=False)

    def stop_process(self) -> None:
        process = self.pty_process
        if process is None or not process.isalive():
            return

        self.add_output("\r\n[stopping process]\r\n")
        try:
            process.terminate(force=True)
        except Exception:
            if self.child_process_id is not None and os.name == "nt":
                subprocess.run(
                    ["taskkill", "/PID", str(self.child_process_id), "/T", "/F"],
                    check=False,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                )

    def request_shutdown(self, delay_seconds: float = 0.0) -> None:
        if self.shutdown_server is None:
            return

        def shutdown_later() -> None:
            if delay_seconds > 0:
                time.sleep(delay_seconds)
            self.shutdown_server()

        threading.Thread(target=shutdown_later, daemon=True).start()

    def run_completion_alerts(self, kind: str, exit_code: int) -> None:
        self.alerts.run(kind, exit_code)


def resolve_pty_python_exe(python_exe: str) -> str:
    if os.path.basename(python_exe).lower() != "python.bat":
        return python_exe

    venv_dir = os.path.normpath(os.path.join(os.path.dirname(python_exe), ".."))
    resolved_python_exe = os.path.join(venv_dir, "Scripts", "python.exe")
    if os.path.exists(resolved_python_exe):
        return resolved_python_exe
    return python_exe


def make_handler(state: BrowserTerminalState, title: str, token: str, icon_path: str):
    class BrowserTerminalHandler(BaseHTTPRequestHandler):
        server_version = "PyAppBrowserTerminal/2.0"

        def log_message(self, _format: str, *args: Any) -> None:
            return

        def _token_ok(self) -> bool:
            query = parse_qs(urlparse(self.path).query)
            return query.get("token", [""])[0] == token

        def _send(self, status: int, content_type: str, body: bytes) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _send_json(self, data: dict[str, Any], status: int = 200) -> None:
            self._send(status, "application/json; charset=utf-8", json.dumps(data).encode("utf-8"))

        def _read_json(self) -> dict[str, Any]:
            content_length = int(self.headers.get("Content-Length", "0") or "0")
            if content_length <= 0:
                return {}
            body = self.rfile.read(content_length)
            return json.loads(body.decode("utf-8"))

        def _send_file(self, path: str, fallback_content_type: str) -> None:
            if not self._token_ok() or not os.path.isfile(path):
                self._send(404, "text/plain; charset=utf-8", b"")
                return

            try:
                with open(path, "rb") as file:
                    data = file.read()
            except OSError:
                self._send(404, "text/plain; charset=utf-8", b"")
                return

            content_type = mimetypes.guess_type(path)[0] or fallback_content_type
            self._send(200, content_type, data)

        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path == "/favicon.ico":
                self._send_file(icon_path, "image/x-icon")
                return

            if parsed.path == "/assets/xterm.js":
                self._send_file(os.path.join(ASSET_DIR, "xterm.js"), "text/javascript; charset=utf-8")
                return

            if parsed.path == "/assets/xterm.css":
                self._send_file(os.path.join(ASSET_DIR, "xterm.css"), "text/css; charset=utf-8")
                return

            if parsed.path == "/assets/addon-fit.js":
                self._send_file(os.path.join(ASSET_DIR, "addon-fit.js"), "text/javascript; charset=utf-8")
                return

            if not self._token_ok():
                self._send(403, "text/plain; charset=utf-8", b"Forbidden")
                return

            if parsed.path == "/":
                self._send(200, "text/html; charset=utf-8", render_html(title, token).encode("utf-8"))
                return

            if parsed.path == "/events":
                query = parse_qs(parsed.query)
                try:
                    after = int(query.get("after", ["0"])[0])
                except ValueError:
                    after = 0
                self._send_json(
                    {
                        "events": state.get_events_after(after),
                        "running": state.process_running,
                        "exitCode": state.exit_code,
                    }
                )
                return

            self._send(404, "text/plain; charset=utf-8", b"Not found")

        def do_POST(self) -> None:
            parsed = urlparse(self.path)
            if not self._token_ok():
                self._send(403, "text/plain; charset=utf-8", b"Forbidden")
                return

            if parsed.path == "/input":
                data = self._read_json()
                state.send_input(str(data.get("data", "")))
                self._send_json({"ok": True, "running": state.process_running})
                return

            if parsed.path == "/resize":
                data = self._read_json()
                try:
                    cols = int(data.get("cols", DEFAULT_COLS))
                    rows = int(data.get("rows", DEFAULT_ROWS))
                except (TypeError, ValueError):
                    cols = DEFAULT_COLS
                    rows = DEFAULT_ROWS
                state.resize(cols, rows)
                self._send_json({"ok": True})
                return

            if parsed.path == "/stop":
                state.stop_process()
                self._send_json({"ok": True})
                return

            if parsed.path == "/shutdown":
                state.add_output("\r\n[closing browser terminal server]\r\n", log=False)
                state.request_shutdown(SHUTDOWN_AFTER_CLOSE_SECONDS)
                self._send_json({"ok": True})
                return

            self._send(404, "text/plain; charset=utf-8", b"Not found")

    return BrowserTerminalHandler


def render_html(title: str, token: str) -> str:
    safe_title = html.escape(title)
    token_json = json.dumps(token)
    favicon_url = f"/favicon.ico?token={token}"
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{safe_title}</title>
<link rel="icon" href="{html.escape(favicon_url)}">
<link rel="stylesheet" href="/assets/xterm.css?token={token}">
<style>
* {{ box-sizing: border-box; }}
html, body {{
  height: 100%;
}}
body {{
  margin: 0;
  display: grid;
  grid-template-rows: auto 1fr;
  background: #0b0f14;
  color: #d8dee9;
  font-family: "Segoe UI", Arial, sans-serif;
}}
header {{
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  min-height: 42px;
  padding: 8px 10px;
  background: #141a22;
  border-bottom: 1px solid #253041;
}}
h1 {{
  margin: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 14px;
  font-weight: 600;
}}
.actions {{
  display: flex;
  flex: 0 0 auto;
  gap: 8px;
}}
button {{
  border: 1px solid #3a4657;
  border-radius: 4px;
  background: #1c2531;
  color: #eef2f7;
  font: inherit;
  font-size: 13px;
  padding: 5px 9px;
  cursor: pointer;
}}
button:hover {{ background: #263244; }}
button:disabled {{
  opacity: 0.55;
  cursor: default;
}}
#terminal {{
  min-height: 0;
  width: 100%;
  height: 100%;
  padding: 8px;
}}
.xterm {{
  height: 100%;
}}
.xterm .xterm-viewport {{
  overflow-y: auto;
}}
</style>
</head>
<body>
<header>
  <h1>{safe_title}</h1>
  <div class="actions">
    <button id="stop" type="button">Stop</button>
    <button id="close" type="button">Close server</button>
  </div>
</header>
<div id="terminal"></div>
<script src="/assets/xterm.js?token={token}"></script>
<script src="/assets/addon-fit.js?token={token}"></script>
<script>
const TOKEN = {token_json};
const stopButton = document.getElementById("stop");
const closeButton = document.getElementById("close");
const termElement = document.getElementById("terminal");
const term = new Terminal({{
  cursorBlink: true,
  convertEol: false,
  fontFamily: 'Consolas, "Cascadia Mono", "Lucida Console", monospace',
  fontSize: 13,
  scrollback: 5000,
  theme: {{
    background: "#0b0f14",
    foreground: "#d8dee9",
    cursor: "#f8f8f2",
    selectionBackground: "#31415a"
  }}
}});
const fitAddon = new FitAddon.FitAddon();
term.loadAddon(fitAddon);
term.open(termElement);
fitAddon.fit();
term.focus();

let lastEventId = 0;
let running = true;
let lastResize = {{cols: term.cols, rows: term.rows}};

function setRunning(value) {{
  running = value;
  stopButton.disabled = !value;
}}

async function postJson(path, payload) {{
  return fetch(`${{path}}?token=${{encodeURIComponent(TOKEN)}}`, {{
    method: "POST",
    headers: {{"Content-Type": "application/json"}},
    body: JSON.stringify(payload || {{}})
  }});
}}

function scheduleResize() {{
  fitAddon.fit();
  if (term.cols === lastResize.cols && term.rows === lastResize.rows) return;
  lastResize = {{cols: term.cols, rows: term.rows}};
  postJson("/resize", lastResize);
}}

term.onData(data => {{
  if (!running) return;
  postJson("/input", {{data}});
}});

term.onResize(size => {{
  lastResize = {{cols: size.cols, rows: size.rows}};
  postJson("/resize", lastResize);
}});

window.addEventListener("resize", () => {{
  window.clearTimeout(window.__resizeTimer);
  window.__resizeTimer = window.setTimeout(scheduleResize, 80);
}});

async function poll() {{
  while (true) {{
    try {{
      const response = await fetch(`/events?after=${{lastEventId}}&token=${{encodeURIComponent(TOKEN)}}`);
      if (!response.ok) throw new Error(`HTTP ${{response.status}}`);
      const payload = await response.json();
      for (const event of payload.events) {{
        lastEventId = Math.max(lastEventId, event.id);
        term.write(event.text);
      }}
      setRunning(payload.running);
      if (!payload.running && payload.exitCode !== null) {{
        term.write(`\\r\\n[browser terminal server may close now]\\r\\n`);
        return;
      }}
    }} catch (error) {{
      setRunning(false);
      term.write(`\\r\\n[disconnected from browser terminal server]\\r\\n`);
      return;
    }}
  }}
}}

stopButton.addEventListener("click", async () => {{
  await postJson("/stop");
}});

closeButton.addEventListener("click", async () => {{
  await postJson("/shutdown");
}});

scheduleResize();
poll();
</script>
</body>
</html>
"""


def read_pty_output(state: BrowserTerminalState) -> None:
    process = state.pty_process
    if process is None:
        return

    while True:
        try:
            data = process.read(4096)
        except EOFError:
            break
        except OSError:
            break
        except Exception as error:
            if state.process_running:
                state.add_output(f"\r\n[failed reading terminal output: {error}]\r\n", log=False)
            break

        if data:
            state.add_output(data)
        elif not state.process_running:
            break
        else:
            time.sleep(0.01)


def wait_for_process(state: BrowserTerminalState) -> None:
    process = state.pty_process
    if process is None:
        return

    exit_code = process.wait()
    state.exit_code = exit_code
    if state.child_process_id is not None:
        state.registry.remove(state.child_process_id)
    state.add_output(f"\r\n[process exited with code {exit_code}]\r\n")
    if exit_code == 0:
        state.run_completion_alerts("success", exit_code)
    elif looks_like_interpreter_crash(exit_code):
        state.run_completion_alerts("crash", exit_code)
    else:
        state.run_completion_alerts("failure", exit_code)
    if (exit_code == 0 and state.close_on_success) or (exit_code != 0 and state.close_on_failure):
        state.request_shutdown(2.0)


def start_pty_process(
    *,
    state: BrowserTerminalState,
    script_path: str,
    python_exe: str,
    wdir_is_script_dir: bool,
) -> None:
    cwd = os.path.dirname(script_path) if wdir_is_script_dir else os.getcwd()
    resolved_python_exe = resolve_pty_python_exe(python_exe)
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    command = [resolved_python_exe, "-u", "-X", "faulthandler", script_path]

    try:
        from winpty import PtyProcess
    except Exception as error:
        raise RuntimeError(
            "[Error] pywinpty is required for browser terminal mode.\n"
            "Install/reinstall backend packages so the 'winpty' module is complete and exposes PtyProcess in "
            "code\\DONT_CHANGE\\python_packages.\n"
            "Expected requirement: pywinpty==3.0.3"
        ) from error

    try:
        process = PtyProcess.spawn(
            command,
            cwd=cwd,
            env=env,
            dimensions=(DEFAULT_ROWS, DEFAULT_COLS),
        )
    except Exception:
        state.exit_code = 1
        state.add_output(
            "\r\n[Error] Failed to start browser terminal process.\r\n"
            f"Python exe: {resolved_python_exe}\r\n"
            f"Python script: {script_path}\r\n\r\n"
            f"{traceback.format_exc()}\r\n",
            log=False,
        )
        return

    state.pty_process = process
    state.child_process_id = int(process.pid)
    state.registry.add(process.pid)

    threading.Thread(target=read_pty_output, args=(state,), daemon=True).start()
    threading.Thread(target=wait_for_process, args=(state,), daemon=True).start()


def main() -> None:
    if len(sys.argv) < 17:
        raise ValueError(
            "Usage: browser_terminal.py script_path python_exe title icon_path app_id wdir_is_script_dir "
            "close_on_crash close_on_failure close_on_success print_timestamp_format log_path "
            "log_timestamp_format overwrite_log script_after_crash "
            "input_prepend process_id_file_path "
            "[play_sound_on_success send_Windows_notification_on_success "
            "play_sound_on_failure send_Windows_notification_on_failure "
            "play_sound_on_python_interpreter_crash send_Windows_notification_on_python_interpreter_crash "
            "open_log_file_after_success open_log_file_after_failure open_log_file_after_python_interpreter_crash "
            "start_minimized correct_start_signal_file_path]"
        )

    script_path = sys.argv[1]
    python_exe = sys.argv[2]
    title = sys.argv[3]
    icon_path = sys.argv[4]
    app_id = sys.argv[5]
    wdir_is_script_dir = arg_to_bool(6, True)
    close_on_failure = arg_to_bool(8)
    close_on_success = arg_to_bool(9, True)
    log_path = sys.argv[11]
    log_timestamp_format = sys.argv[12]
    overwrite_log = arg_to_bool(13, True)
    process_id_file_path = sys.argv[15]
    play_sound_on_success = arg_to_wav_path(16)
    send_Windows_notification_on_success = arg_to_bool(17)
    play_sound_on_failure = arg_to_wav_path(18)
    send_Windows_notification_on_failure = arg_to_bool(19)
    play_sound_on_python_interpreter_crash = arg_to_wav_path(20)
    send_Windows_notification_on_python_interpreter_crash = arg_to_bool(21)
    open_log_file_after_success = arg_to_bool(22)
    open_log_file_after_failure = arg_to_bool(23)
    open_log_file_after_python_interpreter_crash = arg_to_bool(24)
    start_minimized = arg_to_bool(25)
    correct_start_signal_file_path = sys.argv[26] if len(sys.argv) > 26 else ""

    registry = ProcessIdRegistry(process_id_file_path)
    registry.add(os.getpid())
    atexit.register(registry.cleanup)

    logger = TerminalLogger(log_path, overwrite_log, log_timestamp_format)
    state = BrowserTerminalState(
        title=title,
        app_id=app_id,
        close_on_success=close_on_success,
        close_on_failure=close_on_failure,
        open_log_file_after_success=open_log_file_after_success,
        open_log_file_after_failure=open_log_file_after_failure,
        open_log_file_after_python_interpreter_crash=open_log_file_after_python_interpreter_crash,
        play_sound_on_success=play_sound_on_success,
        send_Windows_notification_on_success=send_Windows_notification_on_success,
        play_sound_on_failure=play_sound_on_failure,
        send_Windows_notification_on_failure=send_Windows_notification_on_failure,
        play_sound_on_python_interpreter_crash=play_sound_on_python_interpreter_crash,
        send_Windows_notification_on_python_interpreter_crash=send_Windows_notification_on_python_interpreter_crash,
        logger=logger,
        registry=registry,
    )

    token = secrets.token_urlsafe(24)
    server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(state, title, token, icon_path))
    state.shutdown_server = server.shutdown
    url = f"http://127.0.0.1:{server.server_port}/?token={token}"

    start_pty_process(
        state=state,
        script_path=script_path,
        python_exe=python_exe,
        wdir_is_script_dir=wdir_is_script_dir,
    )
    create_signal_file(correct_start_signal_file_path)

    try:
        opened = open_browser(url, start_minimized)
    except Exception as error:
        opened = False
        show_browser_open_failure(url, error)
    if not opened:
        show_browser_open_failure(url)
    try:
        server.serve_forever()
    finally:
        state.stop_process()
        server.server_close()
        logger.close()


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"[Error] Browser terminal failed: {error}")
        raise
