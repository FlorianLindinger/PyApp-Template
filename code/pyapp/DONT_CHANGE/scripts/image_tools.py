"""PNG and ICO generation through Windows WPF."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple  # typing: annotations stay evaluable on Python 3.8

# Small icon sizes get a finishing step, {size: sharpening amount}: Windows renders them at
# SUPERSAMPLE times the size, then the last step is averaged in linear light (thin light lines
# stay light instead of turning grey, as plain averaging of sRGB values does) and sharpened
# mildly (edges stay crisp after averaging). Larger sizes look the same either way.
FINISHED_SIZES = {16: 0.6, 24: 0.45, 32: 0.3, 48: 0.0}
SUPERSAMPLE = 4


def _run_wpf_powershell(script: str, **extra_env: str) -> str:
    """Run one WPF/PowerShell image operation and return its standard output.

    ``extra_env`` supplies the operation inputs without interpolating them into
    the PowerShell source. Raises ``RuntimeError`` when PowerShell reports an
    error. This helper is Windows-only by design.
    """
    import os
    import subprocess

    from pyapp.DONT_CHANGE.backend_settings import POWERSHELL_EXE

    environment = os.environ.copy()
    environment.update(extra_env)
    # PowerShell source is bundled; image inputs are passed through environment variables.
    completed = subprocess.run(  # noqa: S603
        # PowerShell source is bundled; image inputs are passed through environment variables.
        [POWERSHELL_EXE, "-NoProfile", "-NonInteractive", "-STA", "-Command", script],
        capture_output=True,
        text=True,
        check=False,
        env=environment,
    )
    if completed.returncode:
        raise RuntimeError(completed.stderr.strip() or completed.stdout.strip() or "WPF image operation failed.")
    return completed.stdout.strip()


def get_png_image_id(path: str) -> str:
    """Return a stable ``widthxheight:crc32`` ID for decoded PNG pixels.

    The ID is based on the decoded RGBA pixel data rather than PNG file bytes,
    so metadata or encoding differences do not change it. Raises
    ``FileNotFoundError`` when ``path`` is absent.
    """
    import base64
    import json
    import zlib

    if not Path(path).is_file():
        raise FileNotFoundError(f'PNG does not exist: "{os.path.normpath(str(Path(path).absolute()))}"')
    script = r"""
Add-Type -AssemblyName PresentationCore
$bitmap = [System.Windows.Media.Imaging.BitmapImage]::new()
$bitmap.BeginInit(); $bitmap.UriSource = [Uri]$env:IMAGE_URI
$bitmap.CacheOption = 'OnLoad'; $bitmap.EndInit()
$image = [System.Windows.Media.Imaging.FormatConvertedBitmap]::new($bitmap, [System.Windows.Media.PixelFormats]::Bgra32, $null, 0)
$bytes = [byte[]]::new($image.PixelWidth * $image.PixelHeight * 4)
$image.CopyPixels($bytes, $image.PixelWidth * 4, 0)
[pscustomobject]@{ width=$image.PixelWidth; height=$image.PixelHeight; pixels=[Convert]::ToBase64String($bytes) } | ConvertTo-Json -Compress
"""
    payload = json.loads(_run_wpf_powershell(script, IMAGE_URI=Path(path).resolve().as_uri()))
    bgra = base64.b64decode(payload["pixels"])
    rgba = bytearray(bgra)
    rgba[0::4], rgba[2::4] = bgra[2::4], bgra[0::4]
    return f"{payload['width']}x{payload['height']}:{zlib.crc32(rgba) & 0xFFFFFFFF:08x}"


def generate_ico_from_png(
    output_path: str,
    base_png_path: str,
    sub_png_path: Optional[str] = None,
    sub_icon_area_scale_factor: float = 0.35,
    sub_icon_alignment: str = "bottom right",
    override: bool = True,
    icon_sizes: Iterable[int] = (256, 128, 64, 48, 32, 24, 16),
) -> str:
    """Create a multi-resolution ICO from a base PNG and optional overlay.

    Each requested icon size is rendered with built-in Windows WPF and stored
    as a PNG layer in the ICO. The overlay's area is controlled by
    ``sub_icon_area_scale_factor`` and its compass-style position by
    ``sub_icon_alignment``. Set ``override`` to ``False`` to preserve an
    existing output. Returns the absolute ICO path.
    """
    import base64
    import json
    import struct

    output_path, base_png_path = (
        os.path.normpath(str(Path(output_path).absolute())),
        os.path.normpath(str(Path(base_png_path).absolute())),
    )
    sub_png_path = os.path.normpath(str(Path(sub_png_path).absolute())) if sub_png_path else None
    sizes = tuple(icon_sizes)
    if not Path(base_png_path).is_file():
        raise FileNotFoundError(f'Base PNG does not exist: "{base_png_path}"')
    if sub_png_path and not Path(sub_png_path).is_file():
        raise FileNotFoundError(f'Sub PNG does not exist: "{sub_png_path}"')
    if not 0 < sub_icon_area_scale_factor <= 1:
        raise ValueError("sub_icon_area_scale_factor must be greater than 0 and at most 1.")
    if not sizes or any(not 0 < size <= 256 for size in sizes):
        raise ValueError("icon_sizes must contain sizes from 1 through 256.")
    aliases = {"up": "top", "down": "bottom", "middle": "center", "centre": "center"}
    tokens = [
        aliases.get(token, token) for token in sub_icon_alignment.lower().replace("_", " ").replace("-", " ").split()
    ]
    if not tokens or any(token not in {"top", "bottom", "left", "right", "center"} for token in tokens):
        raise ValueError(f"Unsupported sub_icon_alignment: {sub_icon_alignment!r}")
    vertical = next((token for token in tokens if token in {"top", "bottom"}), "center")
    horizontal = next((token for token in tokens if token in {"left", "right"}), "center")
    if Path(output_path).exists() and not override:
        return output_path
    output_folder = str(Path(output_path).parent)
    if output_folder:
        Path(output_folder).mkdir(parents=True, exist_ok=True)

    script = r"""
Add-Type -AssemblyName PresentationCore
# Each image is decoded straight to the pixel size it gets in the icon: Windows' decoder then
# averages all source pixels (Fant). Drawing a large image small would sample only a few of them,
# which makes small icons jagged and noisy. Everything is then placed pixel for pixel.
function Load($path, $width, $height) {
  $image = [System.Windows.Media.Imaging.BitmapImage]::new()
  $image.BeginInit(); $image.UriSource = [Uri]$path; $image.CacheOption = 'OnLoad'
  if ($width) { $image.DecodePixelWidth = $width; $image.DecodePixelHeight = $height }
  $image.EndInit()
  return $image
}
$base = Load $env:ICO_BASE_URI
$overlay = if ($env:ICO_OVERLAY_URI) { Load $env:ICO_OVERLAY_URI } else { $null }
function Render($iconSize) {
  # The base image fills the square, centered; a non-square one keeps its proportions.
  $scale = $iconSize / [double][Math]::Max($base.PixelWidth, $base.PixelHeight)
  $width = [Math]::Max(1, [int][Math]::Round($base.PixelWidth * $scale)); $height = [Math]::Max(1, [int][Math]::Round($base.PixelHeight * $scale))
  $left = [int][Math]::Floor(($iconSize - $width) / 2); $top = [int][Math]::Floor(($iconSize - $height) / 2)
  $visual = [System.Windows.Media.DrawingVisual]::new(); $context = $visual.RenderOpen()
  $context.DrawImage((Load $env:ICO_BASE_URI $width $height), [Windows.Rect]::new($left, $top, $width, $height))
  if ($overlay) {
    # The overlay covers ICO_OVERLAY_SCALE of the base image's area, at the configured edge.
    $factor = [Math]::Sqrt((($width * $height) / ($overlay.PixelWidth * $overlay.PixelHeight)) * [double]$env:ICO_OVERLAY_SCALE)
    $ow = [Math]::Max(1, [int][Math]::Round($overlay.PixelWidth * $factor)); $oh = [Math]::Max(1, [int][Math]::Round($overlay.PixelHeight * $factor))
    $x = if ($env:ICO_HORIZONTAL -eq 'left') { $left } elseif ($env:ICO_HORIZONTAL -eq 'right') { $left + $width - $ow } else { $left + [int][Math]::Floor(($width - $ow) / 2) }
    $y = if ($env:ICO_VERTICAL -eq 'top') { $top } elseif ($env:ICO_VERTICAL -eq 'bottom') { $top + $height - $oh } else { $top + [int][Math]::Floor(($height - $oh) / 2) }
    $context.DrawImage((Load $env:ICO_OVERLAY_URI $ow $oh), [Windows.Rect]::new($x, $y, $ow, $oh))
  }
  $context.Close()
  $result = [System.Windows.Media.Imaging.RenderTargetBitmap]::new($iconSize, $iconSize, 96, 96, [System.Windows.Media.PixelFormats]::Pbgra32); $result.Render($visual)
  return $result
}
function Png($bitmap) {
  $encoder = [System.Windows.Media.Imaging.PngBitmapEncoder]::new(); $encoder.Frames.Add([System.Windows.Media.Imaging.BitmapFrame]::Create($bitmap))
  $stream = [IO.MemoryStream]::new(); try { $encoder.Save($stream); return [Convert]::ToBase64String($stream.ToArray()) } finally { $stream.Dispose() }
}
function Raw($bitmap) {
  $bytes = [byte[]]::new($bitmap.PixelWidth * $bitmap.PixelHeight * 4); $bitmap.CopyPixels($bytes, $bitmap.PixelWidth * 4, 0)
  return [Convert]::ToBase64String($bytes)
}
# Sizes in ICO_FINISHED come back as raw premultiplied BGRA pixels at ICO_SUPERSAMPLE times the
# size, for the finishing step in Python; all others as finished PNGs.
$finished = @($env:ICO_FINISHED -split ',' | Where-Object { $_ })
@($env:ICO_SIZES -split ',' | ForEach-Object {
  $size = [int]$_
  if ($finished -contains $_) { [pscustomobject]@{ size=$size; raw=(Raw (Render ($size * [int]$env:ICO_SUPERSAMPLE))) } }
  else { [pscustomobject]@{ size=$size; png=(Png (Render $size)) } }
}) | ConvertTo-Json -Compress
"""

    def render(base: str, layer_sizes: List[int]) -> Dict[int, bytes]:
        """{size: PNG} of base (with the overlay) at the given sizes."""
        if not layer_sizes:
            return {}
        payload = json.loads(
            _run_wpf_powershell(
                script,
                ICO_BASE_URI=Path(base).resolve().as_uri(),
                ICO_OVERLAY_URI=Path(sub_png_path).resolve().as_uri() if sub_png_path else "",
                ICO_OVERLAY_SCALE=str(sub_icon_area_scale_factor),
                ICO_VERTICAL=vertical,
                ICO_HORIZONTAL=horizontal,
                ICO_SIZES=",".join(map(str, layer_sizes)),
                ICO_FINISHED=",".join(str(size) for size in layer_sizes if size in FINISHED_SIZES),
                ICO_SUPERSAMPLE=str(SUPERSAMPLE),
            )
        )
        if isinstance(payload, dict):
            payload = [payload]
        frames: Dict[int, bytes] = {}
        for entry in payload:
            size = int(entry["size"])
            if "raw" in entry:
                pixels = _shrink_in_linear_light(base64.b64decode(entry["raw"]), size, SUPERSAMPLE)
                frames[size] = _png_rgba(size, _sharpen(pixels, size, FINISHED_SIZES[size]))
            else:
                frames[size] = base64.b64decode(entry["png"])
        return frames

    rendered = render(base_png_path, list(sizes))
    layers = [(size, rendered[size]) for size in sizes]
    offset = 6 + 16 * len(layers)
    entries: List[bytes] = []
    data = bytearray()
    for size, png in layers:
        entries.append(
            struct.pack(
                "<BBBBHHII",
                0 if size == 256 else size,
                0 if size == 256 else size,
                0,
                0,
                1,
                32,
                len(png),
                offset,
            )
        )
        data.extend(png)
        offset += len(png)
    with Path(output_path).open("wb") as file:
        file.write(struct.pack("<HHH", 0, 1, len(layers)) + b"".join(entries) + data)
    return output_path


# ------------------------------------------------------------ finishing small icon sizes
#
# Pure Python on small images (at most 192 x 192 source pixels), so no image library is needed.
# Pixels are lists of (red, green, blue, alpha), colors as sRGB values 0..1, alpha 0..1.

Pixel = Tuple[float, float, float, float]

_SRGB_TO_LINEAR = [
    (value / 255) / 12.92 if value / 255 <= 0.04045 else ((value / 255 + 0.055) / 1.055) ** 2.4 for value in range(256)
]


def _linear_to_srgb(value: float) -> float:
    value = min(max(value, 0.0), 1.0)
    return value * 12.92 if value <= 0.0031308 else 1.055 * value ** (1 / 2.4) - 0.055


def _shrink_in_linear_light(pbgra: bytes, size: int, factor: int) -> List[Pixel]:
    """Average each factor x factor block of premultiplied BGRA pixels in linear light, weighted by alpha."""
    big = size * factor
    pixels: List[Pixel] = []
    for row in range(size):
        for column in range(size):
            red = green = blue = alpha = 0.0
            for y in range(row * factor, row * factor + factor):
                index = (y * big + column * factor) * 4
                for _ in range(factor):
                    a = pbgra[index + 3]
                    if a:
                        weight = a / 255
                        # Premultiplied in WPF: undo it before converting to linear light.
                        blue += _SRGB_TO_LINEAR[min(255, round(pbgra[index] * 255 / a))] * weight
                        green += _SRGB_TO_LINEAR[min(255, round(pbgra[index + 1] * 255 / a))] * weight
                        red += _SRGB_TO_LINEAR[min(255, round(pbgra[index + 2] * 255 / a))] * weight
                        alpha += weight
                    index += 4
            if alpha:
                pixels.append(
                    (
                        _linear_to_srgb(red / alpha),
                        _linear_to_srgb(green / alpha),
                        _linear_to_srgb(blue / alpha),
                        alpha / factor**2,
                    )
                )
            else:
                pixels.append((0.0, 0.0, 0.0, 0.0))
    return pixels


def _sharpen(pixels: List[Pixel], size: int, amount: float) -> List[Pixel]:
    """Unsharp mask with a 3 x 3 blur; transparent neighbors do not count, so edges get no dark halo."""
    if not amount:
        return pixels
    weights = ((1, 2, 1), (2, 4, 2), (1, 2, 1))
    result: List[Pixel] = []
    for row in range(size):
        for column in range(size):
            red, green, blue, alpha = pixels[row * size + column]
            if not alpha:
                result.append(pixels[row * size + column])
                continue
            total = blurred_red = blurred_green = blurred_blue = 0.0
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    y, x = row + dy, column + dx
                    if 0 <= y < size and 0 <= x < size:
                        r, g, b, a = pixels[y * size + x]
                        weight = weights[dy + 1][dx + 1] * a
                        blurred_red += r * weight
                        blurred_green += g * weight
                        blurred_blue += b * weight
                        total += weight
            sharp = [
                min(max(value + amount * (value - blurred / total), 0.0), 1.0)
                for value, blurred in ((red, blurred_red), (green, blurred_green), (blue, blurred_blue))
            ]
            result.append((sharp[0], sharp[1], sharp[2], alpha))
    return result


def _png_rgba(size: int, pixels: List[Pixel]) -> bytes:
    """An 8-bit RGBA PNG of size x size pixels."""
    import struct
    import zlib

    rows = bytearray()
    for row in range(size):
        rows.append(0)  # filter type: none
        for red, green, blue, alpha in pixels[row * size : (row + 1) * size]:
            rows.extend(round(channel * 255) for channel in (red, green, blue, alpha))

    def chunk(kind: bytes, body: bytes) -> bytes:
        return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body) & 0xFFFFFFFF)

    header = struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0)  # 8 bits per channel, RGBA
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", header)
        + chunk(b"IDAT", zlib.compress(bytes(rows), 9))
        + chunk(b"IEND", b"")
    )
