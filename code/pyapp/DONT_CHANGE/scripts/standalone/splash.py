"""A start-up splash: a dark card with the app's icon and name in a color gradient, one message,
a loading bar and a turning neon glow with smooth, truly transparent edges.

Standalone: copy this file anywhere. Standard library only (tkinter; ctypes for the glow on
Windows, which falls back to the card alone elsewhere or if it fails). Run it as its own process,
so it keeps animating while the app starts and Tk never meets the app's GUI toolkit::

    python splash.py "My App" icon.png "Loading ..." 0.5    # closes when its stdin closes
    python splash.py "My App" icon.png "Loading ..." 3 preview   # closes after 3 s, a click or Escape

The minimum seconds keep it visible at least that long after its stdin closed.
"""

from __future__ import annotations

import contextlib
import os
import sys
import threading
from typing import Any, List, Literal, Sequence, Tuple

_Color = Tuple[float, float, float]

_GLOW_COLORS = ("#ff8fd8", "#a17dff", "#4f8dff", "#4fe3e0", "#a17dff", "#ff8fd8")  # turning around the frame
_TITLE_COLORS = ("#ff8fd8", "#a17dff", "#4fe3e0")  # blended across the app name
_CARD_COLOR = "#06070a"
_GLOW_REACH, _GLOW_PEAK = 40, 0.78  # px past the card edge; opacity at the edge
_CARD_W, _CARD_H, _RADIUS = 560, 300, 26
_LUT = 1024  # glow colors precomputed around the frame; also the rotation resolution
_TURN_SECONDS = 9.0


def _rgb(color: str) -> _Color:
    return (int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16))


def _hex(value: _Color) -> str:
    return "#" + "".join(f"{max(0, min(255, round(v))):02x}" for v in value)


def _mix(a: _Color, b: _Color, t: float) -> _Color:
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t)


def _gradient(colors: Sequence[str], fraction: float) -> _Color:
    """Evenly spaced stops blended in HLS (the short way round), so hues stay vivid between stops."""
    import colorsys

    if len(colors) == 1:
        return _rgb(colors[0])
    position = fraction * (len(colors) - 1)
    i = min(int(position), len(colors) - 2)
    t = position - i
    a = colorsys.rgb_to_hls(*(v / 255 for v in _rgb(colors[i])))
    b = colorsys.rgb_to_hls(*(v / 255 for v in _rgb(colors[i + 1])))
    hue = (a[0] + t * ((b[0] - a[0] + 0.5) % 1.0 - 0.5)) % 1.0
    red, green, blue = colorsys.hls_to_rgb(hue, a[1] + t * (b[1] - a[1]), a[2] + t * (b[2] - a[2]))
    return (red * 255, green * 255, blue * 255)


class _Glow:
    """Neon edge and soft glow in a per-pixel-alpha layered window on top of the card (Windows,
    ctypes only). It draws the card's edge, so the rounded corners are smooth (anti-aliased): the
    card window's own clipping region is jagged, but lies under the opaque edge line.

    Every pixel stores its opacity (from the signed distance to the card edge: glow outside, a
    bright line on the edge, a faint inner glow inside) and its position around the frame (one byte). A frame's colors come from three 256-entry tables via ``bytes.translate``,
    so turning the glow costs a few milliseconds without NumPy or Pillow. GDI+ premultiplies.
    """

    def __init__(
        self,
        window: Any,  # the Tk window to turn into the glow; tkinter is imported only when shown
        size: Tuple[int, int],
        card: Tuple[int, int, int, int],
        radius: float,
        reach: float,
        peak: float,
        scale: float,
    ) -> None:
        import ctypes
        import math
        from ctypes import wintypes

        self.width, self.height = size
        user, gdi, gdiplus = ctypes.windll.user32, ctypes.windll.gdi32, ctypes.windll.gdiplus
        self.user, self.gdi, self.gdiplus = user, gdi, gdiplus
        user.GetParent.argtypes = [wintypes.HWND]
        user.GetParent.restype = wintypes.HWND
        user.GetDC.restype = wintypes.HDC
        user.GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
        user.SetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_long]
        user.UpdateLayeredWindow.argtypes = (
            [wintypes.HWND, wintypes.HDC]
            + [ctypes.c_void_p] * 2
            + [wintypes.HDC, ctypes.c_void_p, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD]
        )
        gdi.CreateCompatibleDC.argtypes = [wintypes.HDC]
        gdi.CreateCompatibleDC.restype = wintypes.HDC
        gdi.SelectObject.argtypes = [wintypes.HDC, wintypes.HGDIOBJ]
        gdi.SelectObject.restype = wintypes.HGDIOBJ
        gdi.DeleteObject.argtypes = [wintypes.HGDIOBJ]
        gdi.DeleteDC.argtypes = [wintypes.HDC]

        class StartupInput(ctypes.Structure):
            _fields_ = [
                ("version", ctypes.c_uint32),
                ("callback", ctypes.c_void_p),
                ("no_thread", wintypes.BOOL),
                ("no_codecs", wintypes.BOOL),
            ]

        self.token = ctypes.c_size_t()
        if gdiplus.GdiplusStartup(ctypes.byref(self.token), ctypes.byref(StartupInput(1, None, False, False)), None):
            raise OSError("GDI+ unavailable")
        window.update_idletasks()
        self.hwnd = user.GetParent(window.winfo_id()) or window.winfo_id()
        # layered + click-through + no taskbar button + never takes focus
        user.SetWindowLongW(self.hwnd, -20, user.GetWindowLongW(self.hwnd, -20) | 0x80000 | 0x20 | 0x80 | 0x08000000)
        self.screen = user.GetDC(None)
        self.memory = gdi.CreateCompatibleDC(self.screen)
        self.bitmap: Any = None  # the current HBITMAP, selected into self.memory
        self.ctypes = ctypes

        # Opacity and frame position per pixel. Straight sides are filled row-wise; only the
        # four corner squares need per-pixel maths, which keeps start-up fast.
        left, top, card_w, card_h = card
        right, bottom = left + card_w, top + card_h
        arc = 0.5 * math.pi * radius
        side_w, side_h = card_w - 2 * radius, card_h - 2 * radius
        perimeter = 2 * (side_w + side_h) + 4 * arc
        unit = 256 / perimeter
        starts = [
            0.0,
            arc,
            arc + side_w,
            2 * arc + side_w,
            2 * arc + side_w + side_h,
            3 * arc + side_w + side_h,
            3 * arc + 2 * side_w + side_h,
            4 * arc + 2 * side_w + side_h,
        ]  # arc, top, arc, right, ...

        line, inner = 1.6 * scale, 14 * scale  # edge line width; depth of the inner glow

        def opacity(distance: float) -> int:
            """Signed distance in px (positive outside). Every step is a ramp of about one pixel,
            which is what makes the curves smooth."""
            if distance > 0:  # the edge line fades into the glow (bright core, long tail)
                t = distance / reach
                glow = 0.0 if t >= 1 else peak * (0.5 * (1 - t) ** 4 + 0.5 * (1 - t) ** 1.6)
                return round(255 * (glow + (1 - glow) * max(0.0, 1 - distance)))
            depth = -distance - line
            if depth <= 0:
                return 255
            haze = 0.4 * math.exp(-depth / (3 * scale)) if depth < inner else 0.0
            return round(255 * (haze + (1 - haze) * max(0.0, 1 - depth)))

        def position(s: float) -> int:
            return int(s * unit) % 256

        corners = (  # center x, center y, start angle, arc start
            (left + radius, top + radius, math.pi, starts[0]),
            (right - radius, top + radius, 1.5 * math.pi, starts[2]),
            (right - radius, bottom - radius, 0.0, starts[4]),
            (left + radius, bottom - radius, 0.5 * math.pi, starts[6]),
        )
        x_in, x_out = math.ceil(left + radius - 0.5), math.ceil(right - radius - 0.5)  # straight top/bottom columns
        top_positions = bytes(position(starts[1] + x + 0.5 - left - radius) for x in range(x_in, x_out))
        bottom_positions = bytes(position(starts[5] + right - radius - x - 0.5) for x in range(x_in, x_out))
        left_fade = bytes(opacity(left - x - 0.5) for x in range(left))
        right_fade = bytes(opacity(x + 0.5 - right) for x in range(right, self.width))
        band = min(math.ceil(inner + line) + 2, card_w // 2)  # inner-glow columns at the left/right sides
        inner_left = bytes(opacity(-x - 0.5) for x in range(band))
        alpha, place = bytearray(), bytearray()

        def corner_pixels(xs: range, cx: float, cy: float, start: float, s0: float, y: float) -> None:
            for x in xs:
                dx, dy = x + 0.5 - cx, y - cy
                alpha.append(opacity(math.hypot(dx, dy) - radius))
                place.append(position(s0 + ((math.atan2(dy, dx) - start) % (2 * math.pi)) * radius))

        for row in range(self.height):
            y = row + 0.5
            if top + radius <= y <= bottom - radius:
                alpha += left_fade + inner_left + bytes(card_w - 2 * band) + inner_left[::-1] + right_fade
                place += bytes([position(starts[7] + bottom - radius - y)]) * (left + band) + bytes(card_w - 2 * band)
                place += bytes([position(starts[3] + y - top - radius)]) * (self.width - right + band)
                continue
            upper = y < top + radius
            first, second = (corners[0], corners[1]) if upper else (corners[3], corners[2])
            corner_pixels(range(x_in), *first, y)
            alpha += bytes([opacity(top - y if upper else y - bottom)]) * (x_out - x_in)
            place += top_positions if upper else bottom_positions
            corner_pixels(range(x_out, self.width), *second, y)
        self.place = bytes(place)
        self.pixels = bytearray(self.width * self.height * 4)
        self.pixels[3::4] = alpha
        self.buffer = (ctypes.c_char * len(self.pixels)).from_buffer(self.pixels)

    def render(self, colors: List[_Color], rotation: int) -> None:
        """Color the glow; ``colors`` has ``_LUT`` entries around the frame, shifted by ``rotation``."""
        ctypes = self.ctypes
        step = _LUT // 256
        table = [colors[(j * step + rotation) % _LUT] for j in range(256)]
        for channel in range(3):  # BGRA order
            self.pixels[channel::4] = self.place.translate(bytes(round(c[2 - channel]) for c in table))
        image, bitmap = ctypes.c_void_p(), ctypes.c_void_p()
        if self.gdiplus.GdipCreateBitmapFromScan0(
            self.width, self.height, self.width * 4, 0x26200A, self.buffer, ctypes.byref(image)
        ):
            return
        self.gdiplus.GdipCreateHBITMAPFromBitmap(image, ctypes.byref(bitmap), 0)
        self.gdiplus.GdipDisposeImage(image)
        if bitmap.value:
            self.gdi.SelectObject(self.memory, bitmap)
            if self.bitmap:
                self.gdi.DeleteObject(self.bitmap)
            self.bitmap = bitmap

    def present(self, x: int, y: int, opacity: int = 255) -> None:
        ctypes = self.ctypes
        from ctypes import wintypes

        position, size, source = wintypes.POINT(x, y), wintypes.SIZE(self.width, self.height), wintypes.POINT(0, 0)
        blend = ctypes.c_uint32(((opacity & 0xFF) << 16) | (1 << 24))  # AC_SRC_OVER, AC_SRC_ALPHA
        self.user.UpdateLayeredWindow(
            self.hwnd,
            self.screen,
            ctypes.byref(position),
            ctypes.byref(size),
            self.memory,
            ctypes.byref(source),
            0,
            ctypes.byref(blend),
            2,
        )


def show(title: str, icon: str, minimum_seconds: float = 0.0, preview: bool = False, message: str = "") -> None:
    """Dark card with a turning neon glow. All Tk calls stay on this process's main thread."""
    import math
    import time
    import tkinter as tk
    from tkinter import font

    if os.name == "nt":
        import ctypes

        with contextlib.suppress(Exception):
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
    root = tk.Tk()  # the glow window; the card is an owned window on top of it
    root.withdraw()
    root.overrideredirect(True)
    root.title(title)
    scale = max(1.0, root.winfo_fpixels("1i") / 96)
    margin = round((_GLOW_REACH + 4) * scale)
    card_w, card_h = round(_CARD_W * scale), round(_CARD_H * scale)
    width, height = card_w + 2 * margin, card_h + 2 * margin
    left = (root.winfo_screenwidth() - width) // 2
    top = (root.winfo_screenheight() - height) // 2
    root.geometry(f"{width}x{height}+{left}+{top}")
    card_color = _rgb(_CARD_COLOR)
    colors = [_gradient(_GLOW_COLORS, k / _LUT) for k in range(_LUT)]
    rotation_offset = int(time.time() * 1000) % _LUT  # a different start color each time

    window = tk.Toplevel(root)
    window.withdraw()
    window.overrideredirect(True)
    window.title(title)
    window.geometry(f"{card_w}x{card_h}+{left + margin}+{top + margin}")
    canvas = tk.Canvas(window, width=card_w, height=card_h, bg=_CARD_COLOR, highlightthickness=0)
    canvas.pack()

    glow = None
    if os.name == "nt":
        with contextlib.suppress(Exception):
            glow = _Glow(
                root,
                (width, height),
                (margin, margin, card_w, card_h),
                _RADIUS * scale,
                _GLOW_REACH * scale,
                _GLOW_PEAK,
                scale,
            )
            glow.render(colors, rotation_offset)
            glow.present(left, top)

    def xy(x: float, y: float) -> Tuple[float, float]:
        return x * scale, y * scale

    def text(
        x: float,
        y: float,
        value: str,
        size: float,
        color: str,
        weight: str = "normal",
        anchor: Literal["w", "e", "center"] = "w",
    ) -> int:
        left_px, top_px = xy(x, y)
        return canvas.create_text(
            left_px, top_px, text=value, anchor=anchor, fill=color, font=("Segoe UI", -round(size * scale), weight)
        )

    icon_xy = (140, _CARD_H / 2)
    image = None  # Tk drops an image without a Python reference
    try:
        image = tk.PhotoImage(file=icon)
        image = image.subsample(max(1, math.ceil(max(image.width(), image.height()) / (168 * scale))))
        canvas.create_image(*xy(*icon_xy), image=image)
    except (tk.TclError, OSError):  # no icon, or a format Tk cannot read (PNG and GIF work)
        text(*icon_xy, "\u25c8", 64, "#e8ecf8", anchor="center")

    def fit(value: str, measure_font: font.Font, room: float) -> str:
        """Shorten ``value`` with an ellipsis until it fits ``room`` pixels."""
        value = " ".join(value.split())
        while value and measure_font.measure(value) > room:
            value = value[:-2].rstrip() + "\u2026" if len(value) > 2 else ""
        return value

    # Title: one color per letter, blended across the name (a gradient without images). Long names
    # get a smaller font (down to 30 px), then two lines split at a space, then an ellipsis.
    room = 266 * scale
    name = " ".join(title.split()) or "\u2026"
    title_font = font.Font(family="Segoe UI", size=-round(42 * scale), weight="bold")
    for size in range(40, 29, -2):
        if title_font.measure(name) <= room:
            break
        title_font = font.Font(family="Segoe UI", size=-round(size * scale), weight="bold")
    lines = [name]
    if title_font.measure(name) > room and " " in name:
        words = name.split(" ")
        first = next(  # the longest first line that fits; the rest goes to the second line
            (
                " ".join(words[:n])
                for n in range(len(words) - 1, 0, -1)
                if title_font.measure(" ".join(words[:n])) <= room
            ),
            words[0],
        )
        lines = [first, name[len(first) :].strip()]
    lines = [fit(line, title_font, room) or "\u2026" for line in lines]
    total = max(1, sum(title_font.measure(line) for line in lines))
    line_height = title_font.metrics("linespace")
    done = 0.0
    for row, line in enumerate(lines):
        x = 266 * scale
        y = 116 * scale + (row - (len(lines) - 1) / 2) * line_height - (10 * scale if len(lines) > 1 else 0)
        for letter in line:
            width = title_font.measure(letter)
            color = _gradient(_TITLE_COLORS, min(1.0, (done + width / 2) / total))
            canvas.create_text(x, y, text=letter, anchor="w", font=title_font, fill=_hex(color))
            x += width
            done += width

    message_xy, bar = (268, 166), (268, 520, 202)
    message_color = _mix(_gradient(_TITLE_COLORS, 0.5), (255, 255, 255), 0.45)
    message_font = font.Font(family="Segoe UI", size=-round(13 * scale))
    text(*message_xy, fit(message, message_font, 252 * scale), 13, _hex(message_color))

    # Loading bar: a short gradient comet gliding along a dim track.
    bar_left, bar_right, bar_y = bar
    track = _mix(card_color, (255, 255, 255), 0.09)
    canvas.create_line(*xy(bar_left, bar_y), *xy(bar_right, bar_y), fill=_hex(track), width=2 * scale, capstyle="round")
    comet_length, pieces = 96, 24
    comet = []
    for i in range(pieces):
        f = i / (pieces - 1)
        color = _mix(track, _gradient(_TITLE_COLORS, f), math.sin(math.pi * f) ** 0.8)
        comet.append(canvas.create_line(0, 0, 1, 1, fill=_hex(color), width=3 * scale, capstyle="round"))

    if preview:  # looks exactly like a start; only closes on Escape or a click
        window.bind("<Escape>", lambda _event: root.destroy())
        window.bind("<Button-1>", lambda _event: root.destroy())
    closed = threading.Event()

    def watch_parent() -> None:
        try:
            if sys.stdin is not None:
                sys.stdin.buffer.read()
        finally:
            closed.set()

    if not preview:
        threading.Thread(target=watch_parent, daemon=True).start()

    state = {"rotation": -1, "glow_at": 0.0}
    started = time.monotonic()

    def animate() -> None:
        now = time.monotonic()
        if closed.is_set() and now - started >= minimum_seconds:
            root.destroy()
            return
        age = now - started
        rotation = (rotation_offset + int(age / _TURN_SECONDS * _LUT)) % _LUT
        if rotation != state["rotation"] and glow is not None and now - state["glow_at"] >= 0.04:
            state["rotation"] = rotation
            state["glow_at"] = now
            glow.render(colors, rotation)
            glow.present(left, top)
        travel = (bar_right - bar_left - comet_length) * (0.5 - 0.5 * math.cos(age * 1.6))
        segment = comet_length / pieces
        for i, item in enumerate(comet):
            x0 = bar_left + travel + i * segment
            canvas.coords(item, *xy(x0, bar_y), *xy(x0 + segment, bar_y))
        root.after(16, animate)

    if closed.is_set() and not minimum_seconds:
        root.destroy()
        return
    window.deiconify()
    window.update_idletasks()
    if os.name == "nt":
        # Rounded card, inset 1 px so its jagged clipping edge stays under the glow window's
        # opaque edge line; the owner link keeps the glow window above the card.
        from ctypes import wintypes

        with contextlib.suppress(Exception):
            user, gdi = ctypes.windll.user32, ctypes.windll.gdi32
            user.GetParent.argtypes = [wintypes.HWND]
            user.GetParent.restype = wintypes.HWND
            user.SetWindowRgn.argtypes = [wintypes.HWND, wintypes.HRGN, wintypes.BOOL]
            gdi.CreateRoundRectRgn.restype = wintypes.HRGN
            gdi.DeleteObject.argtypes = [wintypes.HANDLE]
            hwnd = user.GetParent(window.winfo_id()) or window.winfo_id()
            if glow is not None:
                user.SetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_void_p]
                user.SetWindowLongPtrW(glow.hwnd, -8, hwnd)
            diameter = round(2 * _RADIUS * scale) - 2
            region = gdi.CreateRoundRectRgn(1, 1, card_w, card_h, diameter, diameter)
            if region and not user.SetWindowRgn(hwnd, region, True):
                gdi.DeleteObject(region)  # success transfers ownership to Windows
    if glow is not None:
        root.deiconify()
    if preview:
        window.focus_force()
    started = time.monotonic()  # count actual visibility, independently of app startup
    if preview and minimum_seconds:
        root.after(max(1, int(minimum_seconds * 1000)), root.destroy)
    animate()
    root.mainloop()


if __name__ == "__main__":
    with contextlib.suppress(Exception):  # a cosmetic helper must never show an error dialog
        # title, icon (PNG/GIF path or ""), message, minimum seconds, optional "preview"
        show(sys.argv[1], sys.argv[2], float(sys.argv[4]), preview=sys.argv[5:] == ["preview"], message=sys.argv[3])
