"""Tell the developer when a newer launcher (PyApp-Template release) exists; never updates anything.

Opt-in with check_for_launcher_updates in developer_settings.py, because it contacts GitHub. Runs
in Setup and when the developer menu opens, at most once a day:

1. DONT_CHANGE/tmp/update_check.json remembers the last check, its answer and the developer's
   choices ("skip this version", "don't check again"). The settings file is never written.
2. Less than a day since the last check: the remembered answer is used, nothing is downloaded.
3. Otherwise one small request to GitHub's "latest release" address, with a short timeout. No
   connection, a proxy or any other problem: nothing is shown, and the next day tries again.

Updating stays a deliberate step: replace code/pyapp/DONT_CHANGE with the new release (see the
README section "Updating the template").
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple

from pyapp.DONT_CHANGE import pyapp_settings as paths
from pyapp.DONT_CHANGE.scripts.diagnostics import note_ignored

STATE_PATH = Path(paths.TEMPORARY_DIR) / "update_check.json"
LATEST_RELEASE_URL = f"https://api.github.com/repos/{paths.TEMPLATE_REPOSITORY}/releases/latest"
CHECK_INTERVAL_SECONDS = 24 * 3600
TIMEOUT_SECONDS = 4


def version_key(text: str) -> Tuple[int, ...]:
    """(1, 2, 3) for "v1.2.3" or "1.2.3"; () when it is not a version number."""
    match = re.match(r"^v?(\d+(?:\.\d+)*)", (text or "").strip())
    return tuple(int(part) for part in match.group(1).split(".")) if match else ()


def read_state() -> Dict[str, Any]:
    try:
        state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        return state if isinstance(state, dict) else {}
    except (OSError, ValueError):
        return {}


def write_state(state: Dict[str, Any]) -> None:
    try:
        STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        STATE_PATH.write_text(json.dumps(state, indent=2), encoding="utf-8")
    except OSError:
        note_ignored("write the update check state")


def fetch_latest() -> Optional[Dict[str, str]]:
    """The newest release from GitHub as {"version", "date", "url"}; None on any problem."""
    import urllib.request

    request = urllib.request.Request(
        LATEST_RELEASE_URL,
        headers={"Accept": "application/vnd.github+json", "User-Agent": "PyApp-Template-update-check"},
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:  # noqa: S310
            data = json.loads(response.read().decode("utf-8"))
    except Exception:
        return None  # offline, blocked, rate-limited, no release yet: try again tomorrow
    version = str(data.get("tag_name") or "")
    if not version_key(version):
        return None
    return {
        "version": version.lstrip("v"),
        "date": str(data.get("published_at") or "")[:10],
        "url": str(data.get("html_url") or f"https://github.com/{paths.TEMPLATE_REPOSITORY}/releases"),
    }


def current_release_date() -> str:
    """The date of the installed launcher version from CHANGELOG.md ("## 1.2.3 - 2026-11-20"), else ""."""
    try:
        text = (Path(paths.DONT_CHANGE_DIR) / "CHANGELOG.md").read_text(encoding="utf-8")
    except OSError:
        return ""
    match = re.search(rf"(?m)^## {re.escape(paths.LAUNCHER_VERSION)} - (\d{{4}}-\d{{2}}-\d{{2}})", text)
    return match.group(1) if match else ""


def available_update(
    enabled: bool, now: Optional[float] = None, fetch: Callable[[], Optional[Dict[str, str]]] = fetch_latest
) -> Optional[Dict[str, str]]:
    """The newer release to tell about, or None. Downloads at most once per CHECK_INTERVAL_SECONDS."""
    if not enabled:
        return None
    state = read_state()
    if state.get("never"):
        return None
    now = time.time() if now is None else now
    latest = state.get("latest")
    checked = state.get("checked")
    if not isinstance(checked, (int, float)) or now - checked >= CHECK_INTERVAL_SECONDS:
        latest = fetch()
        # Stored even after a failed request: an offline PC does not wait for the timeout on every start.
        state.update(checked=now, latest=latest)
        write_state(state)
    if not isinstance(latest, dict) or not version_key(latest.get("version", "")):
        return None
    if version_key(latest["version"]) <= version_key(paths.LAUNCHER_VERSION):
        return None
    if state.get("skip_version") == latest["version"]:
        return None
    return latest


def remember_choice(answer: str, version: str) -> Optional[str]:
    """Store "s" (skip this version) or "n" (don't check again); returns what was stored, if anything."""
    state = read_state()
    if answer == "s":
        state["skip_version"] = version
    elif answer == "n":
        state["never"] = True
    else:
        return None
    write_state(state)
    return "skip_version" if answer == "s" else "never"


def tell_about_update(enabled: bool, interactive: bool = True) -> None:
    """Show a newer launcher release, if any, and ask what to do about the reminder. Never raises."""
    try:
        update = available_update(enabled)
        if update is None:
            return
        from pyapp.DONT_CHANGE.scripts.console_tools import ANSI_DIM, ask, print_heading, print_info, styled

        print_heading("Launcher update available")
        installed = paths.LAUNCHER_VERSION + (f" ({current_release_date()})" if current_release_date() else "")
        newest = update["version"] + (f" ({update['date']})" if update.get("date") else "")
        print(f"  Installed  {installed}")
        print(f"  Newest     {newest}")
        print(f"  Changes    {styled(update['url'], ANSI_DIM)}")
        print_info('To update, replace code/pyapp/DONT_CHANGE with the new release (README: "Updating the template").')
        if not interactive:
            return
        try:
            answer = ask("Enter = remind me later, s = skip this version, n = don't check again:").strip().lower()
        except (EOFError, KeyboardInterrupt):
            return
        stored = remember_choice(answer, update["version"])
        if stored == "skip_version":
            print_info(f"Version {update['version']} will not be shown again.")
        elif stored == "never":
            print_info("No more update checks. Delete DONT_CHANGE/tmp/update_check.json to undo.")
    except Exception:
        note_ignored("launcher update check")
