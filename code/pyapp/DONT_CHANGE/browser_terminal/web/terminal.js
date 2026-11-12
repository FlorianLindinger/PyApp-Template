// The browser terminal page: xterm.js connected to host.py over a WebSocket.
// Output arrives as binary messages (UTF-8 with VT sequences, decoded by xterm.js); everything
// else is small JSON messages {t: ...}. Keys follow Windows Terminal: Ctrl+C copies a selection
// (otherwise it interrupts), Ctrl+V pastes, right-click copies or pastes like the classic console.
(() => {
  "use strict";
  const config = JSON.parse(document.getElementById("config").textContent);
  const notice = document.getElementById("notice");
  const favicon = document.getElementById("favicon");
  const DEFAULT_FONT_SIZE = config.font.size;

  // The host finds this window by this title, then sends "ready"; only then the real one is shown.
  let windowFound = false;
  let title = config.title;
  document.title = config.marker;
  const showTitle = (text) => {
    title = text || config.title;
    if (windowFound) document.title = title;
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
    allowProposedApi: false,
    theme: config.theme,
    // Tells xterm.js that ConPTY owns line wrapping and repaints, which keeps reflow correct.
    windowsPty: { backend: "conpty", buildNumber: config.windowsBuild },
  });
  const fit = new FitAddon.FitAddon();
  term.loadAddon(fit);
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

  // ------------------------------------------------------------ connection

  let socket = null;
  let ended = false;
  const send = (message) => {
    if (socket && socket.readyState === WebSocket.OPEN) socket.send(JSON.stringify(message));
  };
  const sendSize = () => send({ t: "r", c: term.cols, r: term.rows });

  const handleControl = (message) => {
    switch (message.t) {
      case "hello":
        setColors(message.colors);
        if (message.iconVersion) favicon.href = "icon?v=" + message.iconVersion;
        if (message.ready) {
          windowFound = true;
          document.title = title;
        }
        break;
      case "ready":
        windowFound = true;
        document.title = title;
        break;
      case "icon":
        favicon.href = "icon?v=" + message.v;
        break;
      case "colors":
        setColors(message.colors);
        break;
      case "exit":
        ended = true;
        // Like a console window: it closes when its program has ended. A browser only lets a
        // page close a window or tab that holds nothing else, so the notice stays otherwise.
        window.close();
        setTimeout(() => showNotice("The program has ended. You can close this window."), 300);
        break;
    }
  };

  const connect = () => {
    socket = new WebSocket("ws://" + location.host + location.pathname.replace(/[^/]*$/, "") + "ws");
    socket.binaryType = "arraybuffer";
    socket.onopen = () => {
      showNotice("");
      fit.fit();
      sendSize();
    };
    socket.onmessage = (event) => {
      if (typeof event.data === "string") handleControl(JSON.parse(event.data));
      else term.write(new Uint8Array(event.data));
    };
    socket.onclose = () => {
      socket = null;
      if (!ended) showNotice("The connection to the program was lost.");
    };
  };

  term.onData((data) => send({ t: "i", d: data }));
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

  term.attachCustomKeyEventHandler((event) => {
    if (event.type !== "keydown" || !event.ctrlKey || event.altKey || event.metaKey) return true;
    const key = event.key.toLowerCase();
    if (key === "c" && (event.shiftKey || term.hasSelection())) {
      copySelection();
      event.preventDefault();
      return false;
    }
    if (key === "v") return false; // the browser's own paste event reaches xterm.js
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

  // ------------------------------------------------------------ bookmark hint
  //
  // Pages cannot create bookmarks, so a faint star in the corner opens a short explanation.
  // Ctrl+D inside the terminal is "end of input" for the program; the panel takes the focus, so
  // Ctrl+D pressed while it is open reaches the browser instead.

  const star = document.getElementById("bookmark");
  const panel = document.getElementById("bookmark-panel");
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
  const setPanel = (open) => {
    panel.hidden = !open;
    star.setAttribute("aria-expanded", String(open));
    if (open) panel.focus();
    else term.focus();
  };
  star.addEventListener("click", () => setPanel(panel.hidden));
  panel.addEventListener("keydown", (event) => {
    if (event.key === "Escape") setPanel(false);
  });
  document.addEventListener("mousedown", (event) => {
    if (!panel.hidden && !panel.contains(event.target) && event.target !== star) setPanel(false);
  });

  connect();
  term.focus();
})();
