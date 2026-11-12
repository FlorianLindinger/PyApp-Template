// The browser terminal page: xterm.js connected to host.py over a WebSocket.
// Output arrives as binary messages (UTF-8 with VT sequences, decoded by xterm.js); everything
// else is small JSON messages {t: ...}. Keys follow Windows Terminal: Ctrl+C copies a selection
// (otherwise it interrupts), Ctrl+V pastes, right-click copies or pastes like the classic console.
// Ctrl+F searches, Ctrl+S saves the output; file paths with a line number open in the editor.
(() => {
  "use strict";
  const config = JSON.parse(document.getElementById("config").textContent);
  const notice = document.getElementById("notice");
  const favicon = document.getElementById("favicon");
  const DEFAULT_FONT_SIZE = config.font.size;

  // The host finds this window by this title, then sends "ready"; only then the real one is shown.
  // "attention" puts a dot in front while something happened that the user has not seen yet.
  let windowFound = false;
  let title = config.title;
  let attention = false;
  document.title = config.marker;
  const applyTitle = () => {
    if (windowFound) document.title = (attention ? "\u25CF " : "") + title;
  };
  const showTitle = (text) => {
    title = text || config.title;
    applyTitle();
  };

  const term = new Terminal({
    scrollback: 9001, // the classic console's default history
    fontFamily: config.font.family,
    fontSize: DEFAULT_FONT_SIZE,
    cursorBlink: true,
    // xterm.js scrolls 1x by default, which feels much slower than a console window; Alt+wheel scrolls faster still.
    scrollSensitivity: config.scroll,
    fastScrollSensitivity: config.scroll * 5,
    fastScrollModifier: "alt",
    // The search add-on highlights all matches with decorations, a "proposed" xterm.js API.
    allowProposedApi: true,
    theme: config.theme,
    // Tells xterm.js that ConPTY owns line wrapping and repaints, which keeps reflow correct.
    windowsPty: { backend: "conpty", buildNumber: config.windowsBuild },
  });
  const fit = new FitAddon.FitAddon();
  const search = new SearchAddon.SearchAddon();
  term.loadAddon(fit);
  term.loadAddon(search);
  term.loadAddon(new WebLinksAddon.WebLinksAddon());
  term.open(document.getElementById("terminal"));

  const setColors = (colors) => {
    const theme = Object.assign({}, config.theme, colors || {});
    term.options.theme = theme;
    document.documentElement.style.setProperty("--bg", theme.background);
    document.documentElement.style.setProperty("--fg", theme.foreground);
  };
  setColors({});

  const showNotice = (text) => {
    notice.textContent = text;
    notice.hidden = !text;
  };

  // ------------------------------------------------------------ notifications
  //
  // Only while the user looks elsewhere (another tab, window or program): a desktop notification
  // if the browser allows it, and always a dot in the tab title until the tab is in front again.

  const NOTIFY_END = "browser-terminal-notify-end";
  const notifyEnd = document.getElementById("notify-end");
  const notifyNext = document.getElementById("notify-next");
  const notifyEvery = document.getElementById("notify-every");
  const notifyButton = document.getElementById("notify-button");
  try {
    notifyEnd.checked = localStorage.getItem(NOTIFY_END) === "1";
  } catch (error) {
    // Storage blocked (private window): the switch starts off.
  }
  const away = () => document.hidden || !document.hasFocus();
  // After a new size reaches the pseudoconsole (window resized, zoom settled), the console redraws
  // the screen: output too, but nothing the program printed. It does not light up or notify.
  const REPAINT_MS = 700; // the host waits 150 ms for the size to settle, then the redraw follows
  let resizedAt = 0;
  const repainting = () => Date.now() - resizedAt < REPAINT_MS;
  // renotify: a notification replacing one still on screen alerts again (sound, popup) instead of
  // updating silently; wanted for each output when notifying on every output.
  const notify = (text, renotify = false) => {
    if (!away()) return;
    attention = true;
    applyTitle();
    if (window.Notification && Notification.permission === "granted") {
      const shown = new Notification(title, { body: text, icon: favicon.href, tag: "browser-terminal", renotify });
      shown.onclick = () => {
        window.focus();
        shown.close();
      };
    }
  };
  const seen = () => {
    if (!attention) return;
    attention = false;
    applyTitle();
  };
  window.addEventListener("focus", seen);
  document.addEventListener("visibilitychange", () => !document.hidden && document.hasFocus() && seen());
  const askPermission = () => {
    if (!window.Notification || Notification.permission !== "default") return;
    Notification.requestPermission().then(() => {
      document.getElementById("notify-blocked").hidden = Notification.permission !== "denied";
    });
  };
  const showArmed = () =>
    notifyButton.classList.toggle("armed", notifyEnd.checked || notifyNext.checked || notifyEvery.checked);
  notifyEnd.addEventListener("change", () => {
    try {
      localStorage.setItem(NOTIFY_END, notifyEnd.checked ? "1" : "0");
    } catch (error) {
      // Not remembered, but on for this page.
    }
    if (notifyEnd.checked) askPermission();
    showArmed();
  });
  let armedAt = 0;
  notifyNext.addEventListener("change", () => {
    armedAt = Date.now();
    if (notifyNext.checked) askPermission();
    showArmed();
  });
  // Every output: deliberately not remembered, so a later start does not begin with a stream of
  // notifications nobody asked for this time.
  const EVERY_COOLDOWN_MS = 1000;
  let lastEveryAt = 0;
  let everyTimer = 0;
  const notifyEveryNow = () => {
    everyTimer = 0;
    lastEveryAt = Date.now();
    notify("New output.", true);
  };
  notifyEvery.addEventListener("change", () => {
    armedAt = Date.now();
    clearTimeout(everyTimer);
    everyTimer = 0;
    if (notifyEvery.checked) askPermission();
    showArmed();
  });
  document.getElementById("notify-blocked").hidden = !(window.Notification && Notification.permission === "denied");
  showArmed();
  let endAnnounced = false;
  const onOutput = () => {
    // The echo of what was just typed while switching it on is not "the next output".
    if (Date.now() - armedAt <= 500 || repainting()) return;
    if (notifyNext.checked) {
      notifyNext.checked = false;
      showArmed();
      notify("New output.");
      lastEveryAt = Date.now(); // this one counts for the cooldown too: no second popup right after
      return;
    }
    // At most one notification per cooldown. Output during the cooldown is announced once when it
    // ends (not dropped), so the last burst of a run is never missed; further output in the same
    // cooldown joins that pending notification.
    if (notifyEvery.checked && !everyTimer) {
      const wait = lastEveryAt + EVERY_COOLDOWN_MS - Date.now();
      if (wait <= 0) notifyEveryNow();
      else everyTimer = setTimeout(notifyEveryNow, wait);
    }
  };

  // ------------------------------------------------------------ view options (remembered)

  const VIEW = "browser-terminal-view";
  const optHighlight = document.getElementById("opt-highlight");
  const optFollow = document.getElementById("opt-follow");
  const optFront = document.getElementById("opt-front");
  try {
    const saved = JSON.parse(localStorage.getItem(VIEW) || "{}");
    if (typeof saved.highlight === "boolean") optHighlight.checked = saved.highlight;
    if (typeof saved.follow === "boolean") optFollow.checked = saved.follow;
    if (typeof saved.front === "boolean") optFront.checked = saved.front;
  } catch (error) {
    // Defaults.
  }
  // The host brings the browser window to the front (a page cannot); it needs to know.
  const sendPreferences = () => send({ t: "p", frontOnInput: optFront.checked });
  for (const option of [optHighlight, optFollow, optFront]) {
    option.addEventListener("change", () => {
      try {
        localStorage.setItem(
          VIEW,
          JSON.stringify({ highlight: optHighlight.checked, follow: optFollow.checked, front: optFront.checked }),
        );
      } catch (error) {
        // Not remembered, but on for this page.
      }
      sendPreferences();
    });
  }

  // New output: light up the lines it touched for a moment (a decoration that fades out), and
  // either follow it to the bottom or keep the view where the user is reading.
  const MAX_FRESH = 60; // with output pouring in, older highlights simply end early
  const fresh = [];
  const highlight = (from, to) => {
    const buffer = term.buffer.active;
    const marker = term.registerMarker(from - (buffer.baseY + buffer.cursorY));
    if (!marker) return;
    const decoration = term.registerDecoration({ marker, width: term.cols, height: to - from + 1, layer: "bottom" });
    if (!decoration) return marker.dispose();
    decoration.onRender((element) => element.classList.add("fresh"));
    const entry = { marker, decoration };
    fresh.push(entry);
    while (fresh.length > MAX_FRESH) {
      const old = fresh.shift();
      old.decoration.dispose();
      old.marker.dispose();
    }
    setTimeout(() => {
      const index = fresh.indexOf(entry);
      if (index >= 0) fresh.splice(index, 1);
      decoration.dispose();
      marker.dispose();
    }, 1500);
  };
  // What the user types comes back as output too (the console echoes it). Only what the program
  // prints lights up: shortly after a key press, the line typed on is left out (the echo, and the
  // line break of Enter); other lines the output reaches, such as the program's answer, light up.
  const ECHO_MS = 250;
  let keyAt = 0;
  let typedRow = -1;
  const writeOutput = (data, isHistory) => {
    const buffer = term.buffer.active;
    const viewTop = buffer.viewportY;
    const from = buffer.baseY + buffer.cursorY;
    const typed = Date.now() - keyAt < ECHO_MS;
    const repaint = repainting();
    term.write(data, () => {
      const after = term.buffer.active;
      let to = after.baseY + after.cursorY;
      if (after.cursorX === 0 && to > from) to -= 1; // the line break alone does not count
      let first = Math.min(from, to);
      const last = Math.max(from, to);
      if (typed && first === typedRow) first += 1;
      if (!isHistory && !repaint && optHighlight.checked && after.type === "normal" && first <= last) {
        highlight(first, last);
      }
      if (optFollow.checked) term.scrollToBottom();
      else if (!isHistory) term.scrollToLine(viewTop);
    });
  };

  // ------------------------------------------------------------ connection

  let socket = null;
  let ended = false;
  const send = (message) => {
    if (socket && socket.readyState === WebSocket.OPEN) socket.send(JSON.stringify(message));
  };
  const sendSize = () => {
    resizedAt = Date.now();
    send({ t: "r", c: term.cols, r: term.rows });
  };

  const handleControl = (message) => {
    switch (message.t) {
      case "hello":
        setColors(message.colors);
        if (message.iconVersion) favicon.href = "icon?v=" + message.iconVersion;
        if (message.ready) {
          windowFound = true;
          applyTitle();
        }
        break;
      case "ready":
        windowFound = true;
        applyTitle();
        break;
      case "icon":
        favicon.href = "icon?v=" + message.v;
        break;
      case "colors":
        setColors(message.colors);
        break;
      case "input":
        // The program waits for input; the host brings the window forward if wanted.
        if (away()) {
          attention = true;
          applyTitle();
        }
        break;
      case "notify":
        // The program's own report of how it ended (sent by the launcher, see ui.py).
        endAnnounced = true;
        if (notifyEnd.checked) notify(message.text);
        break;
      case "exit":
        ended = true;
        if (notifyEnd.checked && !endAnnounced) notify("The program has ended.");
        // Like a console window: it closes when its program has ended. A browser only lets a
        // page close a window or tab that holds nothing else, so the notice stays otherwise.
        window.close();
        setTimeout(() => showNotice("The program has ended. You can close this window."), 300);
        break;
    }
  };

  let history = true; // the first output after connecting is the replay of what was printed before
  const connect = () => {
    socket = new WebSocket("ws://" + location.host + location.pathname.replace(/[^/]*$/, "") + "ws");
    socket.binaryType = "arraybuffer";
    socket.onopen = () => {
      showNotice("");
      fit.fit();
      sendSize();
      sendPreferences();
      setTimeout(() => (history = false), 1000);
    };
    socket.onmessage = (event) => {
      if (typeof event.data === "string") {
        handleControl(JSON.parse(event.data));
      } else {
        writeOutput(new Uint8Array(event.data), history);
        if (!history) onOutput();
      }
    };
    socket.onclose = () => {
      socket = null;
      if (!ended) showNotice("The connection to the program was lost.");
    };
  };

  term.onData((data) => {
    keyAt = Date.now();
    typedRow = term.buffer.active.baseY + term.buffer.active.cursorY;
    send({ t: "i", d: data });
  });
  term.onBinary((data) => send({ t: "b", d: data }));
  term.onResize(sendSize);
  term.onTitleChange(showTitle);

  // ------------------------------------------------------------ size and zoom

  // The new size reaches xterm.js and the pseudoconsole only once zooming or dragging the window
  // edge has paused. Both rewrap the lines on every size change, ConPTY by repainting the screen;
  // a burst of sizes (a touchpad pinch sends dozens a second) makes those repaints land on
  // a different size than they were made for, which duplicates or garbles printed lines.
  const SETTLE_MS = 150;
  let fitTimer = 0;
  const scheduleFit = () => {
    clearTimeout(fitTimer);
    fitTimer = setTimeout(() => fit.fit(), SETTLE_MS);
  };
  new ResizeObserver(scheduleFit).observe(document.getElementById("terminal"));

  // Zoom changes the font, not the page, so the terminal stays sharp and gets more columns.
  // The font follows at once; the columns follow when the zoom settles.
  const zoom = (size) => {
    term.options.fontSize = Math.max(6, Math.min(72, size));
    scheduleFit();
  };
  // A mouse wheel notch is one step (deltaY about 100); a touchpad pinch sends many small
  // deltas, which are added up so a pinch zooms smoothly instead of racing.
  const WHEEL_STEP = 50;
  let wheelTotal = 0;
  document.addEventListener(
    "wheel",
    (event) => {
      if (!event.ctrlKey) return;
      event.preventDefault();
      wheelTotal = Math.abs(event.deltaY) >= WHEEL_STEP ? Math.sign(event.deltaY) * WHEEL_STEP : wheelTotal + event.deltaY;
      if (Math.abs(wheelTotal) < WHEEL_STEP) return;
      zoom(term.options.fontSize + (wheelTotal < 0 ? 1 : -1));
      wheelTotal = 0;
    },
    { passive: false },
  );

  // ------------------------------------------------------------ clipboard

  const copySelection = () => {
    const text = term.getSelection();
    if (!text) return false;
    navigator.clipboard.writeText(text).catch(() => showNotice("Copying to the clipboard was blocked."));
    term.clearSelection();
    return true;
  };
  const pasteClipboard = () => {
    navigator.clipboard
      .readText()
      .then((text) => text && term.paste(text))
      .catch(() => showNotice("Reading the clipboard was blocked; use Ctrl+V."));
  };

  // ------------------------------------------------------------ search (Ctrl+F)

  const searchBar = document.getElementById("search");
  const searchInput = document.getElementById("search-input");
  const searchCount = document.getElementById("search-count");
  const searchCase = document.getElementById("search-case");
  const DECORATIONS = {
    matchBackground: "#c19c0088",
    matchOverviewRuler: "#c19c00",
    activeMatchBackground: "#f9a825",
    activeMatchColorOverviewRuler: "#f9a825",
  };
  const searchOptions = () => ({
    caseSensitive: searchCase.getAttribute("aria-pressed") === "true",
    decorations: DECORATIONS,
  });
  const find = (backwards) => {
    const text = searchInput.value;
    if (!text) {
      search.clearDecorations();
      searchCount.textContent = "";
      return;
    }
    const found = backwards ? search.findPrevious(text, searchOptions()) : search.findNext(text, searchOptions());
    if (!found) searchCount.textContent = "none";
  };
  search.onDidChangeResults(({ resultIndex, resultCount }) => {
    if (!searchInput.value) return;
    searchCount.textContent = resultCount ? `${resultIndex + 1} / ${resultCount}` : "none";
  });
  const openSearch = () => {
    closePanels();
    searchBar.hidden = false;
    const selected = term.getSelection();
    if (selected && !selected.includes("\n")) searchInput.value = selected;
    searchInput.select();
    searchInput.focus();
    if (searchInput.value) find(false);
  };
  const closeSearch = () => {
    searchBar.hidden = true;
    search.clearDecorations();
    term.clearSelection();
    term.focus();
  };
  // Typing searches from where the last match was, so the highlight follows the text as it grows.
  searchInput.addEventListener("input", () => {
    term.clearSelection();
    find(false);
  });
  searchInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter" || event.key === "F3") {
      event.preventDefault();
      find(event.shiftKey);
    } else if (event.key === "Escape") {
      closeSearch();
    }
  });
  searchCase.addEventListener("click", () => {
    searchCase.setAttribute("aria-pressed", String(searchCase.getAttribute("aria-pressed") !== "true"));
    term.clearSelection();
    find(false);
    searchInput.focus();
  });
  document.getElementById("search-next").addEventListener("click", () => find(false));
  document.getElementById("search-previous").addEventListener("click", () => find(true));
  document.getElementById("search-close").addEventListener("click", closeSearch);
  document.getElementById("search-button").addEventListener("click", () => (searchBar.hidden ? openSearch() : closeSearch()));

  // ------------------------------------------------------------ save (Ctrl+S)

  // The whole output with its scrollback as plain text; lines the terminal wrapped become one again.
  const saveOutput = () => {
    const buffer = term.buffer.normal;
    const lines = [];
    for (let index = 0; index < buffer.length; index++) {
      const line = buffer.getLine(index);
      if (!line) continue;
      const text = line.translateToString(true);
      if (line.isWrapped && lines.length) lines[lines.length - 1] += text;
      else lines.push(text);
    }
    while (lines.length && !lines[lines.length - 1]) lines.pop();
    const stamp = new Date().toISOString().slice(0, 19).replace("T", " ").replace(/:/g, "-");
    const name = `${title.replace(/[\\/:*?"<>|\u25CF]+/g, " ").trim() || "output"} ${stamp}.txt`;
    const link = document.createElement("a");
    link.href = URL.createObjectURL(new Blob([lines.join("\r\n") + "\r\n"], { type: "text/plain;charset=utf-8" }));
    link.download = name;
    link.click();
    setTimeout(() => URL.revokeObjectURL(link.href), 10000);
  };
  document.getElementById("save-button").addEventListener("click", saveOutput);

  // ------------------------------------------------------------ file paths

  // "C:\folder\file.py:9" (the launcher's reports) and 'File "C:\folder\file.py", line 9' (Python)
  // become links; a click opens the file in the editor at that line (host.py: open_in_editor).
  const PATH_PATTERNS = [
    /File "((?:[A-Za-z]:|\\\\)[^"]+)", line (\d+)/g,
    /((?:[A-Za-z]:|\\\\)\\[^\s"'<>|*?:]*[^\s"'<>|*?:.,;)\]]):(\d+)/g,
  ];
  term.registerLinkProvider({
    provideLinks(lineNumber, callback) {
      // A long path wraps onto the next rows: search the whole line the row belongs to.
      const buffer = term.buffer.active;
      let first = lineNumber - 1;
      if (!buffer.getLine(first)) return callback(undefined);
      while (first > 0 && buffer.getLine(first).isWrapped) first--;
      let last = first;
      while (buffer.getLine(last + 1) && buffer.getLine(last + 1).isWrapped) last++;
      let text = "";
      for (let row = first; row <= last; row++) text += buffer.getLine(row).translateToString(row === last);
      const at = (index) => ({ x: (index % term.cols) + 1, y: first + Math.floor(index / term.cols) + 1 });
      const links = [];
      const taken = [];
      for (const pattern of PATH_PATTERNS) {
        pattern.lastIndex = 0;
        for (const match of text.matchAll(pattern)) {
          const start = match.index;
          const end = start + match[0].length;
          if (taken.some(([from, to]) => start < to && end > from)) continue;
          taken.push([start, end]);
          const range = { start: at(start), end: at(end - 1) };
          if (range.start.y > lineNumber || range.end.y < lineNumber) continue; // on other rows
          const path = match[1];
          const number = Number(match[2]);
          links.push({
            range,
            text: match[0],
            decorations: { underline: true, pointerCursor: true },
            activate: () => send({ t: "o", path, line: number }),
          });
        }
      }
      callback(links.length ? links : undefined);
    },
  });

  // ------------------------------------------------------------ keys

  term.attachCustomKeyEventHandler((event) => {
    if (event.type !== "keydown") return true;
    if (event.key === "F3") {
      event.preventDefault();
      if (searchBar.hidden) openSearch();
      else find(event.shiftKey);
      return false;
    }
    if (!event.ctrlKey || event.altKey || event.metaKey) return true;
    const key = event.key.toLowerCase();
    if (key === "c" && (event.shiftKey || term.hasSelection())) {
      copySelection();
      event.preventDefault();
      return false;
    }
    if (key === "v") return false; // the browser's own paste event reaches xterm.js
    if (key === "f") {
      event.preventDefault();
      openSearch();
      return false;
    }
    if (key === "s") {
      event.preventDefault();
      saveOutput();
      return false;
    }
    if (key === "=" || key === "+" || key === "-" || key === "0") {
      event.preventDefault();
      zoom(key === "0" ? DEFAULT_FONT_SIZE : term.options.fontSize + (key === "-" ? -1 : 1));
      return false;
    }
    return true;
  });
  document.getElementById("terminal").addEventListener("contextmenu", (event) => {
    event.preventDefault();
    if (!copySelection()) pasteClipboard();
  });
  // Ctrl+F and Ctrl+S also while the focus is outside the terminal (e.g. in a panel).
  document.addEventListener("keydown", (event) => {
    if (!event.ctrlKey || event.altKey || event.target === searchInput) return;
    const key = event.key.toLowerCase();
    if (key === "f" && !term.textarea.contains(event.target)) {
      event.preventDefault();
      openSearch();
    } else if (key === "s" && !term.textarea.contains(event.target)) {
      event.preventDefault();
      saveOutput();
    }
  });

  // ------------------------------------------------------------ panels (notifications, bookmark)
  //
  // Pages cannot create bookmarks, so the star opens a short explanation. Ctrl+D inside the
  // terminal is "end of input" for the program; the panel takes the focus, so Ctrl+D pressed
  // while it is open reaches the browser instead.

  if (config.startLink) {
    document.getElementById("start-link-text").textContent = config.startLink;
    document.getElementById("start-link").hidden = false;
    document.getElementById("start-link-copy").addEventListener("click", (event) => {
      const button = event.currentTarget;
      navigator.clipboard.writeText(config.startLink).then(
        () => (button.textContent = "Copied"),
        () => (button.textContent = "Select and copy it"),
      );
    });
  }
  const panels = [
    [document.getElementById("view-button"), document.getElementById("view-panel")],
    [document.getElementById("notify-button"), document.getElementById("notify-panel")],
    [document.getElementById("bookmark"), document.getElementById("bookmark-panel")],
  ];
  const closePanels = () => {
    for (const [button, panel] of panels) {
      panel.hidden = true;
      button.setAttribute("aria-expanded", "false");
    }
  };
  for (const [button, panel] of panels) {
    button.addEventListener("click", () => {
      const open = panel.hidden;
      closePanels();
      if (open) {
        searchBar.hidden = true;
        panel.hidden = false;
        button.setAttribute("aria-expanded", "true");
        panel.focus();
      } else {
        term.focus();
      }
    });
    panel.addEventListener("keydown", (event) => {
      if (event.key === "Escape") {
        closePanels();
        term.focus();
      }
    });
  }
  document.addEventListener("mousedown", (event) => {
    for (const [button, panel] of panels) {
      if (!panel.hidden && !panel.contains(event.target) && !button.contains(event.target)) {
        panel.hidden = true;
        button.setAttribute("aria-expanded", "false");
      }
    }
  });

  connect();
  term.focus();
})();
