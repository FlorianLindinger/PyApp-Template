# Browser terminal

A terminal emulator in the browser for Windows console programs. The program runs in a real
Windows pseudoconsole (ConPTY), so `input()`, Ctrl+C, colors, titles, cursor movement and
progress bars work as in the classic console. The page adds sharp text, zoom (Ctrl+wheel,
touchpad pinch, Ctrl+/-/0), clickable links, and copy and paste like Windows Terminal: Ctrl+C
copies a selection and otherwise interrupts, Ctrl+V pastes, and right-click copies or pastes.

This folder is self-contained: standard library only, Python 3.8+, Windows 10 1809 or newer,
and no imports from outside it. To use it in another project, copy the folder.

## Usage

```bat
python browser_terminal                                   :: the command prompt in a new browser tab
python browser_terminal -- python -i                      :: any console program
python browser_terminal --title "My tool" -- python my_tool.py
python browser_terminal --config settings.json --cwd C:\work -- cmd /k dir
python browser_terminal --host-name my-tool.localhost --port 8765 --key my-secret-key -- python my_tool.py
```

The page opens in a new tab of the default browser, which is brought to the front.
`--config` names a JSON file with any of the settings listed in `complete_config()` in `host.py`
(theme, font, icon, ...). The exit code is the program's exit code.

From Python: `from browser_terminal import host; host.run({"title": "My tool"}, ["python", "my_tool.py"])`.

Like a console window, closing the tab ends the program (after 5 seconds, so a reload does not),
and the tab closes when the program ends. The page is served on 127.0.0.1 only, behind a secret
key in the address, and only that page may connect.

By default the address is new for every run. With `--host-name`, `--port` and `--key` (or the
same settings in `--config`) it stays the same, so it can be bookmarked while the program runs:
`http://my-tool.localhost:8765/my-secret-key/`. Names ending in `.localhost` reach this PC in Edge,
Chrome and Firefox. When the port is taken (e.g. by a second instance), the next free one is used.
A faint ☆ in the page's top-right corner explains how to bookmark it, and offers a start link
(setting `start_link`, e.g. `my-tool://start`) if your program registers one.

Programs inside can change the page's icon and colors, which a pseudoconsole cannot pass on:

```python
from browser_terminal import ui

if ui.inside():
    ui.request(icon=r"C:\icons\done.ico", colors=ui.colors_from_code("2F"))
```

## Files

| File | Origin |
| --- | --- |
| `host.py`, `ui.py`, `__main__.py`, `web/index.html`, `web/terminal.js` | PyApp-Template launcher, MIT License (`LICENSE.txt`) |
| `web/xterm.js`, `web/xterm.css` | [xterm.js](https://github.com/xtermjs/xterm.js) 5.5.0 (`@xterm/xterm`), unchanged |
| `web/addon-fit.js` | `@xterm/addon-fit` 0.10.0, unchanged |
| `web/addon-web-links.js` | `@xterm/addon-web-links` 0.11.0, unchanged |

The xterm.js files are bundled so the terminal works offline and on locked-down PCs. They are
under the MIT License of the xterm.js authors (`web/LICENSE-xterm.js.txt`); keep that file when
you distribute them. To update them, replace them with the same files from newer npm packages
and try the page with a test program (colors, input, Ctrl+C, resizing, zoom).
