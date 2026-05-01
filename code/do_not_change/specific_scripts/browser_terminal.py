"""Run a Python script behind a localhost browser terminal.

This is intentionally dependency-free. It supports normal line-based input such
as ``input()`` by writing submitted browser lines to the child process stdin.
It is not a full PTY, so raw keyboard apps and advanced ANSI terminal features
are outside its scope.
"""

import atexit
import html
import json
import locale
import os
import secrets
import subprocess
import sys
import threading
import time
import webbrowser
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlparse

MAX_STORED_EVENTS = 10000
SHUTDOWN_AFTER_CLOSE_SECONDS = 0.4


class ProcessIdRegistry:
    def __init__(self, path: str) -> None:
        self.path = path
        self._process_ids: set[int] = set()
        self._lock = threading.RLock()

    def add(self, process_id: int) -> None:
        if self.path == "" or process_id <= 0:
            return

        with self._lock:
            if process_id in self._process_ids:
                return
            self._process_ids.add(process_id)

            folder = os.path.dirname(self.path)
            if folder:
                os.makedirs(folder, exist_ok=True)
            with open(self.path, "a", encoding="utf-8") as pid_file:
                pid_file.write(f"{process_id}\n")

    def remove(self, process_id: int) -> None:
        if self.path == "" or process_id <= 0:
            return

        with self._lock:
            self._process_ids.discard(process_id)
            try:
                with open(self.path, encoding="utf-8") as pid_file:
                    lines = pid_file.readlines()
            except FileNotFoundError:
                return
            except Exception:
                return

            remaining_lines = []
            process_id_text = str(process_id)
            for line in lines:
                parts = line.strip().split(maxsplit=1)
                if parts and parts[0] == process_id_text:
                    continue
                remaining_lines.append(line)

            try:
                if any(line.strip() for line in remaining_lines):
                    with open(self.path, "w", encoding="utf-8") as pid_file:
                        pid_file.writelines(remaining_lines)
                else:
                    os.remove(self.path)
            except Exception:
                pass

    def cleanup(self) -> None:
        for process_id in list(self._process_ids):
            self.remove(process_id)


class LinePrefixer:
    def __init__(self, timestamp_format: str) -> None:
        self.timestamp_format = timestamp_format
        self._at_line_start = True

    def apply(self, text: str) -> str:
        if text == "":
            return ""

        output: list[str] = []
        for char in text:
            if self._at_line_start and self.timestamp_format:
                output.append(datetime.now().strftime(self.timestamp_format))
            output.append(char)
            self._at_line_start = char == "\n"
        return "".join(output)


class TerminalLogger:
    def __init__(self, path: str, overwrite: bool, date_append_format: str, timestamp_format: str) -> None:
        self.path = self._prepare_log_path(path, date_append_format) if path else ""
        self._lock = threading.RLock()
        self._prefixer = LinePrefixer(timestamp_format)
        self._log_file = None
        if self.path:
            self._log_file = open(self.path, "w" if overwrite else "a", encoding="utf-8", buffering=1)
            atexit.register(self.close)

    @staticmethod
    def _prepare_log_path(path: str, date_append_format: str) -> str:
        if date_append_format:
            folder, filename = os.path.split(path)
            stem, suffix = os.path.splitext(filename)
            path = os.path.join(folder, f"{stem}{datetime.now().strftime(date_append_format)}{suffix}")

        folder = os.path.dirname(path)
        if folder:
            os.makedirs(folder, exist_ok=True)
        return path

    def write(self, text: str) -> None:
        if self._log_file is None or text == "":
            return

        with self._lock:
            self._log_file.write(self._prefixer.apply(text))
            self._log_file.flush()

    def close(self) -> None:
        if self._log_file is not None:
            try:
                self._log_file.close()
            except Exception:
                pass
            self._log_file = None


class BrowserTerminalState:
    def __init__(
        self,
        *,
        input_prepend: str,
        print_timestamp_format: str,
        close_on_success: bool,
        close_on_failure: bool,
        logger: TerminalLogger,
        registry: ProcessIdRegistry,
    ) -> None:
        self.input_prepend = input_prepend
        self.close_on_success = close_on_success
        self.close_on_failure = close_on_failure
        self.logger = logger
        self.registry = registry
        self.process: subprocess.Popen[str] | None = None
        self.exit_code: int | None = None
        self.shutdown_server: Any = None

        self._events: list[dict[str, Any]] = []
        self._next_event_id = 1
        self._condition = threading.Condition()
        self._display_prefixers = {
            "stdout": LinePrefixer(print_timestamp_format),
            "stderr": LinePrefixer(print_timestamp_format),
        }

    @property
    def process_running(self) -> bool:
        return self.process is not None and self.process.poll() is None

    def add_event(self, stream: str, text: str, *, prefix: bool = False, log: bool = True) -> None:
        if text == "":
            return

        if prefix and stream in self._display_prefixers:
            text = self._display_prefixers[stream].apply(text)

        if log:
            self.logger.write(text)

        with self._condition:
            event = {"id": self._next_event_id, "stream": stream, "text": text}
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
        if not self.process_running or self.process is None or self.process.stdin is None:
            self.add_event("system", "[input ignored: process is not running]\n", log=False)
            return

        self.add_event("stdin", f"{self.input_prepend}{text}\n")
        self.process.stdin.write(text + "\n")
        self.process.stdin.flush()

    def stop_process(self) -> None:
        process = self.process
        if process is None or process.poll() is not None:
            return

        self.add_event("system", "[stopping process]\n")
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(process.pid), "/T"], check=False, capture_output=True, text=True)
        else:
            process.terminate()

    def request_shutdown(self, delay_seconds: float = 0.0) -> None:
        if self.shutdown_server is None:
            return

        def shutdown_later() -> None:
            if delay_seconds > 0:
                time.sleep(delay_seconds)
            self.shutdown_server()

        threading.Thread(target=shutdown_later, daemon=True).start()


def make_handler(state: BrowserTerminalState, title: str, token: str):
    class BrowserTerminalHandler(BaseHTTPRequestHandler):
        server_version = "PyAppBrowserTerminal/1.0"

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

        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path == "/favicon.ico":
                self._send(404, "text/plain; charset=utf-8", b"")
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
                state.send_input(str(data.get("text", "")))
                self._send_json({"ok": True, "running": state.process_running})
                return

            if parsed.path == "/stop":
                state.stop_process()
                self._send_json({"ok": True})
                return

            if parsed.path == "/shutdown":
                state.add_event("system", "[closing browser terminal server]\n", log=False)
                state.request_shutdown(SHUTDOWN_AFTER_CLOSE_SECONDS)
                self._send_json({"ok": True})
                return

            self._send(404, "text/plain; charset=utf-8", b"Not found")

    return BrowserTerminalHandler


def render_html(title: str, token: str) -> str:
    safe_title = html.escape(title)
    token_json = json.dumps(token)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{safe_title}</title>
<style>
:root {{
  color-scheme: dark;
  font-family: Consolas, "Cascadia Mono", "Lucida Console", monospace;
}}
* {{ box-sizing: border-box; }}
body {{
  margin: 0;
  height: 100vh;
  display: grid;
  grid-template-rows: auto 1fr auto;
  background: #0b0f14;
  color: #d8dee9;
}}
header {{
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 12px;
  background: #141a22;
  border-bottom: 1px solid #253041;
}}
h1 {{
  margin: 0;
  font-size: 14px;
  font-weight: 600;
}}
.actions {{
  display: flex;
  gap: 8px;
}}
button {{
  border: 1px solid #3a4657;
  border-radius: 4px;
  background: #1c2531;
  color: #eef2f7;
  font: inherit;
  padding: 6px 10px;
  cursor: pointer;
}}
button:hover {{ background: #263244; }}
button:disabled {{
  opacity: 0.55;
  cursor: default;
}}
#terminal {{
  margin: 0;
  padding: 12px;
  overflow: auto;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  font-size: 13px;
  line-height: 1.45;
}}
.stderr {{ color: #ff7676; }}
.stdin {{ color: #8fd694; }}
.system {{ color: #8ab4f8; }}
form {{
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 8px;
  padding: 10px 12px;
  background: #141a22;
  border-top: 1px solid #253041;
}}
#input {{
  min-width: 0;
  border: 1px solid #3a4657;
  border-radius: 4px;
  background: #071018;
  color: #f4f7fb;
  font: inherit;
  padding: 8px 10px;
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
<pre id="terminal" aria-live="polite"></pre>
<form id="form">
  <input id="input" autocomplete="off" spellcheck="false" autofocus>
  <button id="send" type="submit">Send</button>
</form>
<script>
const TOKEN = {token_json};
const terminal = document.getElementById("terminal");
const form = document.getElementById("form");
const input = document.getElementById("input");
const send = document.getElementById("send");
const stopButton = document.getElementById("stop");
const closeButton = document.getElementById("close");
let lastEventId = 0;
let running = true;

function appendEvent(event) {{
  const span = document.createElement("span");
  span.className = event.stream;
  span.textContent = event.text;
  terminal.appendChild(span);
  terminal.scrollTop = terminal.scrollHeight;
}}

function setRunning(value) {{
  running = value;
  input.disabled = !value;
  send.disabled = !value;
  stopButton.disabled = !value;
}}

async function poll() {{
  while (true) {{
    try {{
      const response = await fetch(`/events?after=${{lastEventId}}&token=${{encodeURIComponent(TOKEN)}}`);
      if (!response.ok) throw new Error(`HTTP ${{response.status}}`);
      const payload = await response.json();
      for (const event of payload.events) {{
        lastEventId = Math.max(lastEventId, event.id);
        appendEvent(event);
      }}
      setRunning(payload.running);
      if (!payload.running && payload.exitCode !== null) {{
        appendEvent({{stream: "system", text: `[browser terminal server may close now]\\n`}});
        return;
      }}
    }} catch (error) {{
      setRunning(false);
      appendEvent({{stream: "system", text: `[disconnected from browser terminal server]\\n`}});
      return;
    }}
  }}
}}

form.addEventListener("submit", async (event) => {{
  event.preventDefault();
  if (!running) return;
  const text = input.value;
  input.value = "";
  await fetch(`/input?token=${{encodeURIComponent(TOKEN)}}`, {{
    method: "POST",
    headers: {{"Content-Type": "application/json"}},
    body: JSON.stringify({{text}})
  }});
}});

stopButton.addEventListener("click", async () => {{
  await fetch(`/stop?token=${{encodeURIComponent(TOKEN)}}`, {{method: "POST"}});
}});

closeButton.addEventListener("click", async () => {{
  await fetch(`/shutdown?token=${{encodeURIComponent(TOKEN)}}`, {{method: "POST"}});
}});

poll();
</script>
</body>
</html>
"""


def read_stream(pipe: Any, stream: str, state: BrowserTerminalState) -> None:
    try:
        while True:
            chunk = pipe.read(1)
            if chunk == "":
                break
            state.add_event(stream, chunk, prefix=True)
    except Exception as error:
        state.add_event("system", f"[failed reading {stream}: {error}]\n", log=False)


def wait_for_process(state: BrowserTerminalState) -> None:
    process = state.process
    if process is None:
        return

    exit_code = process.wait()
    state.exit_code = exit_code
    state.registry.remove(process.pid)
    state.add_event("system", f"\n[process exited with code {exit_code}]\n")
    if (exit_code == 0 and state.close_on_success) or (exit_code != 0 and state.close_on_failure):
        state.request_shutdown(2.0)


def start_process(
    *,
    state: BrowserTerminalState,
    script_path: str,
    python_exe: str,
    wdir_is_script_dir: bool,
) -> None:
    cwd = os.path.dirname(script_path) if wdir_is_script_dir else None
    encoding = locale.getpreferredencoding(False)
    creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    process = subprocess.Popen(  # noqa:S603
        [python_exe, "-u", script_path],
        cwd=cwd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding=encoding,
        errors="replace",
        bufsize=0,
        creationflags=creationflags,
    )
    state.process = process
    state.registry.add(process.pid)
    state.add_event("system", f"[started process {process.pid}]\n", log=False)

    threading.Thread(target=read_stream, args=(process.stdout, "stdout", state), daemon=True).start()
    threading.Thread(target=read_stream, args=(process.stderr, "stderr", state), daemon=True).start()
    threading.Thread(target=wait_for_process, args=(state,), daemon=True).start()


def main() -> None:
    if len(sys.argv) < 18:
        raise ValueError(
            "Usage: browser_terminal.py script_path python_exe title icon_path app_id wdir_is_script_dir "
            "close_on_crash close_on_failure close_on_success print_timestamp_format log_path "
            "log_timestamp_format overwrite_log log_file_date_append_format script_after_crash "
            "input_prepend process_id_file_path"
        )

    script_path = sys.argv[1]
    python_exe = sys.argv[2]
    title = sys.argv[3]
    wdir_is_script_dir = sys.argv[6] == "1"
    close_on_failure = sys.argv[8] == "1"
    close_on_success = sys.argv[9] == "1"
    print_timestamp_format = sys.argv[10]
    log_path = sys.argv[11]
    log_timestamp_format = sys.argv[12]
    overwrite_log = sys.argv[13] == "1"
    log_file_date_append_format = sys.argv[14]
    input_prepend = sys.argv[16]
    process_id_file_path = sys.argv[17]

    registry = ProcessIdRegistry(process_id_file_path)
    registry.add(os.getpid())
    atexit.register(registry.cleanup)

    logger = TerminalLogger(log_path, overwrite_log, log_file_date_append_format, log_timestamp_format)
    state = BrowserTerminalState(
        input_prepend=input_prepend,
        print_timestamp_format=print_timestamp_format,
        close_on_success=close_on_success,
        close_on_failure=close_on_failure,
        logger=logger,
        registry=registry,
    )

    token = secrets.token_urlsafe(24)
    server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(state, title, token))
    state.shutdown_server = server.shutdown
    url = f"http://127.0.0.1:{server.server_port}/?token={token}"

    start_process(
        state=state,
        script_path=script_path,
        python_exe=python_exe,
        wdir_is_script_dir=wdir_is_script_dir,
    )

    webbrowser.open(url)
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
