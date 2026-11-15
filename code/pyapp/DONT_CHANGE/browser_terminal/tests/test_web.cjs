// Frontend regressions; run with: node --test browser_terminal/tests/test_web.cjs
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const { test } = require("node:test");

const source = fs.readFileSync(path.join(__dirname, "../web/terminal.js"), "utf8");

function selectionPage(texts, range, viewportY = 0) {
  const layer = { style: {} };
  const screen = { querySelector: () => layer, getBoundingClientRect: () => ({ width: 100, height: 80 }) };
  const lines = texts.map((text) => {
    const cells = typeof text === "string" ? [...text].map((chars) => ({ chars, width: 1 })) : text;
    return {
      length: 10,
      getCell: (column) => cells[column] && {
        getChars: () => cells[column].chars,
        getWidth: () => cells[column].width,
      },
    };
  });
  const active = { type: "normal", viewportY, getLine: (row) => lines[row] };
  let columnSelection = false;
  const term = {
    cols: 10, rows: 4, buffer: { active }, getSelectionPosition: () => range,
    element: { querySelector: () => screen, classList: { contains: () => columnSelection } },
    onSelectionChange() {}, onScroll() {}, onResize() {}, onRender() {},
  };
  const context = vm.createContext({ term });
  const start = source.indexOf("// ------------------------------------------------------------ text selection");
  const end = source.indexOf("const setColors =", start);
  vm.runInContext(source.slice(start, end) + "\nglobalThis.drawTextSelection = drawTextSelection;", context);
  return {
    draw: () => { context.drawTextSelection(); return layer.style.clipPath; },
    active,
    column: () => { columnSelection = true; },
  };
}

test("selection highlights text on each line, excluding blank rows and unused trailing cells", () => {
  const page = selectionPage(["abc", "", "x y", ""], { start: { x: 0, y: 0 }, end: { x: 7, y: 3 } });
  assert.equal(page.draw(), 'path("M0,0h30v20h-30Z M0,40h30v20h-30Z")');
});

test("selection entirely beyond the text has no visible highlight", () => {
  const page = selectionPage(["abc"], { start: { x: 4, y: 0 }, end: { x: 8, y: 0 } });
  assert.equal(page.draw(), "inset(100%)");
});

test("partial selections keep their endpoints and follow the scrolled viewport", () => {
  const page = selectionPage(["above", "abcde"], { start: { x: 1, y: 1 }, end: { x: 3, y: 1 } }, 1);
  assert.equal(page.draw(), 'path("M10,0h20v20h-20Z")');
});

test("double-width and combining characters are measured in cells rather than string length", () => {
  const cells = [{ chars: "e\u0301", width: 1 }, { chars: "界", width: 2 }, { chars: "", width: 0 }];
  const page = selectionPage([cells], { start: { x: 0, y: 0 }, end: { x: 10, y: 0 } });
  assert.equal(page.draw(), 'path("M0,0h30v20h-30Z")');
});

test("cleared, alternate-screen and column selections keep native behavior", () => {
  assert.equal(selectionPage(["abc"], undefined).draw(), "");
  const page = selectionPage(["abc"], { start: { x: 0, y: 0 }, end: { x: 10, y: 0 } });
  page.active.type = "alternate";
  assert.equal(page.draw(), "");
  page.active.type = "normal";
  page.column();
  assert.equal(page.draw(), "");
});

// Run the actual page handlers with controlled wheel events, animation frames, and writes.
// No browser or Windows console is needed to check event ordering and scrolling distances.
function scrolling() {
  const frames = [];
  const moves = [];
  let handler;
  const term = {
    rows: 20,
    modes: { mouseTrackingMode: "none" },
    buffer: { active: { type: "normal" } },
    element: { querySelector: () => ({ getBoundingClientRect: () => ({ height: 400 }) }) },
    attachCustomWheelEventHandler: (callback) => { handler = callback; },
    scrollLines: (rows) => moves.push(rows),
  };
  const context = vm.createContext({
    term, config: { scroll: 5 }, options: { fastScroll: 5 }, requestAnimationFrame: (callback) => frames.push(callback),
  });
  const start = source.indexOf("// ------------------------------------------------------------ touchpad scrolling");
  const end = source.indexOf("// New output:", start);
  assert.ok(start >= 0 && end > start, "Scrolling handlers are present");
  vm.runInContext(source.slice(start, end), context);
  return {
    term, frames, moves,
    wheel: (overrides = {}) => handler({ deltaY: 0.5, deltaMode: 0, preventDefault() {}, ...overrides }),
    flush: () => frames.splice(0).forEach((frame) => frame()),
  };
}

test("120 small touchpad events produce one update without losing their total distance", () => {
  const page = scrolling();
  for (let index = 0; index < 120; index++) assert.equal(page.wheel(), false);
  assert.equal(page.frames.length, 1);
  page.flush();
  assert.deepEqual(page.moves, [15]); // 120 * 0.5 px * 5 / 20 px per row
});

test("fractional rows survive separate frames and reverse direction", () => {
  const page = scrolling();
  for (let index = 0; index < 8; index++) { page.wheel(); page.flush(); }
  assert.deepEqual(page.moves, [1]);
  for (let index = 0; index < 8; index++) { page.wheel({ deltaY: -0.5 }); page.flush(); }
  assert.deepEqual(page.moves, [1, -1]);
});

test("line/page wheels and Alt acceleration keep their units", () => {
  const page = scrolling();
  page.wheel({ deltaY: 1, deltaMode: 1 }); page.flush();
  page.wheel({ deltaY: 1, deltaMode: 2 }); page.flush();
  page.wheel({ deltaY: 1, deltaMode: 1, altKey: true }); page.flush();
  assert.deepEqual(page.moves, [5, 100, 25]);
});

test("zoom bypasses scrolling; alternate screens and mouse reporting stay with xterm", () => {
  const page = scrolling();
  assert.equal(page.wheel({ ctrlKey: true }), false);
  assert.equal(page.wheel({ shiftKey: true }), true);
  page.term.buffer.active.type = "alternate";
  assert.equal(page.wheel(), true);
  page.term.buffer.active.type = "normal";
  page.term.modes.mouseTrackingMode = "vt200";
  assert.equal(page.wheel(), true);
  assert.equal(page.frames.length, 0);
});

function outputPage(viewportY, asynchronous = false) {
  const moves = [];
  const writes = [];
  const buffer = { baseY: 100, viewportY, cursorY: 0, cursorX: 0, type: "normal" };
  const context = vm.createContext({
    Date, scrollRevision: 0,
    optFollow: { checked: true }, optHighlight: { checked: false }, repainting: () => false,
    term: {
      buffer: { active: buffer },
      write: (data, done) => asynchronous ? writes.push(done) : done(),
      scrollToBottom: () => moves.push("bottom"),
      scrollToLine: (row) => moves.push(row),
    },
  });
  const start = source.indexOf("const ECHO_MS =");
  const end = source.indexOf("// ------------------------------------------------------------ connection", start);
  vm.runInContext(source.slice(start, end) + "\nglobalThis.writeOutput = writeOutput;", context);
  return { moves, writes, buffer, context, write: () => context.writeOutput(new Uint8Array(), false) };
}

test("incoming output does not pull a scrolled-up reader back to the bottom", () => {
  const page = outputPage(50);
  for (let index = 0; index < 120; index++) page.write();
  assert.deepEqual(page.moves, []);
  assert.equal(page.buffer.viewportY, 50);
});

test("output restores a reading position only when the write actually moved it", () => {
  const page = outputPage(50, true);
  page.write();
  page.buffer.viewportY = 60;
  page.writes[0]();
  assert.deepEqual(page.moves, [50]);
});

test("following resumes at the bottom", () => {
  const page = outputPage(100);
  page.write();
  assert.deepEqual(page.moves, ["bottom"]);
});

test("a touchpad movement during an asynchronous write overrides its saved viewport", () => {
  const page = outputPage(100, true);
  page.write();
  page.context.scrollRevision++;
  page.buffer.viewportY = 90;
  page.writes[0]();
  assert.deepEqual(page.moves, []);
});
