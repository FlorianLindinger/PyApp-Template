# icons

The images of your app: the window and taskbar icon, and the icons of the shortcuts Setup makes.
Every `.ico` here is built from one picture, `icon.png`.

**Change the icons:** replace `icon.png` with your picture (keep the name; best square and at
least 256 × 256 pixels; a picture that is not square keeps its proportions), double-click `regenerate icons.cmd`, then run Setup again
(`Setup - run first and after moving folder.cmd` in the project folder) so the shortcuts show
the new icons. Commit the `.ico` files together with `../generated/auto_generated_icons.json`.

| File | Where it is shown |
| --- | --- |
| `icon.png` | Not shown itself: the picture every `.ico` below is made from. Without it, or while it is still the template's picture, the template's own default image is used. |
| `icon.ico` | The app: its window, the taskbar, and the start, No-Terminal and Browser shortcuts. Your picture as it is. |
| `success.ico` | The window after the program ended normally. |
| `failure.ico` | The window after an error, a crash or Ctrl+C. |
| `settings.ico` | The Settings shortcut. |
| `stop.ico` | The STOP shortcut. |
| `log.ico` | The Logs shortcut. |
| `crash_log.ico` | The Crash-Logs shortcut. |
| `open_code.ico` | The Edit-Code shortcut. |
| `regenerate icons.cmd` | Builds the `.ico` files from `icon.png` again. |

## Overlays

Every icon but `icon.ico` is your picture with a small symbol on top (a gear, a stop sign, a
check mark, ...), so the shortcuts can be told apart. The symbols are part of the launcher
(`../DONT_CHANGE/data/icons`) and cannot be replaced by a PNG of yours. Their size and position
are in `SUB_ICONS` in `../DONT_CHANGE/backend_settings.py`, for example
`"settings": (0.35, "bottom right")`: the share of the icon's area the symbol covers (more than 0,
at most 1) and its position (`"bottom right"`, `"top"`, `"center"`, `"center left"`, ...).
`None` instead of the pair makes that icon without a symbol.

## Your own icon for one case

Replace that `.ico` with your own and keep its name. The generator remembers which icons it made
(in `../generated/auto_generated_icons.json`): those it updates without asking; before it
replaces an `.ico` you placed yourself, it asks, icon by icon. Answer no to keep yours; to go
back to the generated one, answer yes, or delete your `.ico` and regenerate.

## How the icons are made

Each `.ico` holds 256, 128, 64, 48, 32, 24 and 16 pixel images, the sizes Windows uses for
shortcuts, Explorer and the taskbar at the usual display scalings. They are scaled down from
`icon.png` by averaging; from 48 pixels down this happens in linear light, and 32 pixels and
below are sharpened a little, so small icons stay crisp. A simple picture with bold shapes and
strong contrast still looks best when small. The generator uses what Windows has built in; no
image library is installed.
