"""PNG and ICO generation through Windows WPF."""

import os
from collections.abc import Iterable, Sequence
from pathlib import Path


def _run_wpf_powershell(script: str, **extra_env: str) -> str:
    """Run one WPF/PowerShell image operation and return its standard output.

    ``extra_env`` supplies the operation inputs without interpolating them into
    the PowerShell source. Raises ``RuntimeError`` when PowerShell reports an
    error. This helper is Windows-only by design.
    """
    import os
    import subprocess

    environment = os.environ.copy()
    environment.update(extra_env)
    completed = subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-STA", "-Command", script],
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

    if not os.path.isfile(path):
        raise FileNotFoundError(f'PNG does not exist: "{os.path.abspath(path)}"')
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


def generate_png_with_text(
    output_path: str,
    lines: Sequence[str],
    *,
    width: int = 512,
    height: int = 512,
    font_family: str = "Arial",
    font_size: int = 100,
    min_font_size: int = 8,
    bold: bool = True,
    text_color: tuple[int, int, int, int] = (0, 0, 0, 255),
    background_color: tuple[int, int, int, int] = (255, 255, 255, 255),
    padding: int = 20,
) -> str:
    """Create a PNG with centered, automatically fitted text using Windows WPF.

    The output is ``width`` by ``height`` pixels. Lines are centered as a
    group and the font size is reduced in two-pixel steps until every line
    fits within ``padding``. ``text_color`` and ``background_color`` are RGBA
    tuples. Set ``bold`` to use a bold font face. No third-party Python image
    package is required.

    Returns the absolute output path.
    """
    import json

    if width <= 0 or height <= 0 or min_font_size <= 0 or font_size < min_font_size or padding < 0:
        raise ValueError("Invalid PNG text dimensions or font sizes.")
    if not lines or any(not isinstance(line, str) for line in lines):
        raise ValueError("lines must contain one or more strings.")
    for color in (text_color, background_color):
        if len(color) != 4 or any(not 0 <= channel <= 255 for channel in color):
            raise ValueError("Colors must be RGBA tuples with channels from 0 to 255.")

    output_path = os.path.abspath(output_path)
    output_folder = os.path.dirname(output_path)
    if output_folder:
        os.makedirs(output_folder, exist_ok=True)
    script = r"""
Add-Type -AssemblyName PresentationCore
$settings = $env:PNG_TEXT_SETTINGS | ConvertFrom-Json
function Brush($rgba) { [System.Windows.Media.SolidColorBrush]::new([System.Windows.Media.Color]::FromArgb($rgba[3], $rgba[0], $rgba[1], $rgba[2])) }
$weight = if ($settings.bold) { [System.Windows.FontWeights]::Bold } else { [System.Windows.FontWeights]::Normal }
$typeface = [System.Windows.Media.Typeface]::new(
    $settings.font_family,
    [System.Windows.FontStyles]::Normal,
    $weight,
    [System.Windows.FontStretches]::Normal
)
$dpi = 96.0
for ($fontSize = $settings.font_size; $fontSize -ge $settings.min_font_size; $fontSize -= 2) {
    $text = @($settings.lines | ForEach-Object { [System.Windows.Media.FormattedText]::new($_, [Globalization.CultureInfo]::InvariantCulture, 'LeftToRight', $typeface, $fontSize, (Brush $settings.text_color), $dpi) })
    $spacing = [Math]::Max(2, [int]($fontSize / 4))
    $textWidth = ($text | Measure-Object -Property Width -Maximum).Maximum
    $textHeight = ($text | Measure-Object -Property Height -Sum).Sum + $spacing * ($text.Count - 1)
    if ($textWidth -le $settings.width - 2 * $settings.padding -and $textHeight -le $settings.height - 2 * $settings.padding) { break }
}
if ($fontSize -lt $settings.min_font_size) { throw 'Text does not fit at the minimum font size.' }
$visual = [System.Windows.Media.DrawingVisual]::new(); $context = $visual.RenderOpen()
$context.DrawRectangle((Brush $settings.background_color), $null, [Windows.Rect]::new(0, 0, $settings.width, $settings.height))
$y = ($settings.height - $textHeight) / 2
foreach ($line in $text) { $context.DrawText($line, [Windows.Point]::new(($settings.width - $line.Width) / 2, $y)); $y += $line.Height + $spacing }
$context.Close()
$bitmap = [System.Windows.Media.Imaging.RenderTargetBitmap]::new($settings.width, $settings.height, $dpi, $dpi, [System.Windows.Media.PixelFormats]::Pbgra32); $bitmap.Render($visual)
$encoder = [System.Windows.Media.Imaging.PngBitmapEncoder]::new(); $encoder.Frames.Add([System.Windows.Media.Imaging.BitmapFrame]::Create($bitmap))
$stream = [IO.File]::Open($env:PNG_OUTPUT_PATH, 'Create'); try { $encoder.Save($stream) } finally { $stream.Dispose() }
"""
    _run_wpf_powershell(
        script,
        PNG_OUTPUT_PATH=output_path,
        PNG_TEXT_SETTINGS=json.dumps(
            {
                "lines": list(lines),
                "width": width,
                "height": height,
                "font_family": font_family,
                "font_size": font_size,
                "min_font_size": min_font_size,
                "bold": bold,
                "text_color": text_color,
                "background_color": background_color,
                "padding": padding,
            }
        ),
    )
    return output_path


def generate_ico_from_png(
    output_path: str,
    base_png_path: str,
    sub_png_path: str | None = None,
    sub_icon_area_scale_factor: float = 0.35,
    sub_icon_alignment: str = "bottom right",
    override: bool = True,
    icon_sizes: Iterable[int] = (256, 128, 64, 48, 32, 16),
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
        os.path.abspath(output_path),
        os.path.abspath(base_png_path),
    )
    sub_png_path = os.path.abspath(sub_png_path) if sub_png_path else None
    sizes = tuple(icon_sizes)
    if not os.path.isfile(base_png_path):
        raise FileNotFoundError(f'Base PNG does not exist: "{base_png_path}"')
    if sub_png_path and not os.path.isfile(sub_png_path):
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
    if os.path.exists(output_path) and not override:
        return output_path
    output_folder = os.path.dirname(output_path)
    if output_folder:
        os.makedirs(output_folder, exist_ok=True)

    script = r"""
Add-Type -AssemblyName PresentationCore
function Load($path) {
  $image = [System.Windows.Media.Imaging.BitmapImage]::new()
  $image.BeginInit(); $image.UriSource = [Uri]$path; $image.CacheOption = 'OnLoad'; $image.EndInit()
  return $image
}
function Square($image, $iconSize) {
  $scale = $iconSize / [double][Math]::Max($image.PixelWidth, $image.PixelHeight)
  $width = [int][Math]::Round($image.PixelWidth * $scale); $height = [int][Math]::Round($image.PixelHeight * $scale)
  $visual = [System.Windows.Media.DrawingVisual]::new(); $context = $visual.RenderOpen()
  $context.DrawImage($image, [Windows.Rect]::new(($iconSize-$width)/2, ($iconSize-$height)/2, $width, $height)); $context.Close()
  $result = [System.Windows.Media.Imaging.RenderTargetBitmap]::new($iconSize, $iconSize, 96, 96, [System.Windows.Media.PixelFormats]::Pbgra32); $result.Render($visual)
  $encoder = [System.Windows.Media.Imaging.PngBitmapEncoder]::new(); $encoder.Frames.Add([System.Windows.Media.Imaging.BitmapFrame]::Create($result))
  $stream = [IO.MemoryStream]::new(); try { $encoder.Save($stream); return [Convert]::ToBase64String($stream.ToArray()) } finally { $stream.Dispose() }
}
$base = Load $env:ICO_BASE_URI
if ($env:ICO_OVERLAY_URI) {
  $overlay = Load $env:ICO_OVERLAY_URI

  $scale = [Math]::Sqrt((($base.PixelWidth * $base.PixelHeight) / ($overlay.PixelWidth * $overlay.PixelHeight)) * [double]$env:ICO_OVERLAY_SCALE)
  $width = [int][Math]::Round($overlay.PixelWidth * $scale); $height = [int][Math]::Round($overlay.PixelHeight * $scale)
  $x = if ($env:ICO_HORIZONTAL -eq 'left') { 0 } elseif ($env:ICO_HORIZONTAL -eq 'right') { $base.PixelWidth - $width } else { ($base.PixelWidth - $width)/2 }
  $y = if ($env:ICO_VERTICAL -eq 'top') { 0 } elseif ($env:ICO_VERTICAL -eq 'bottom') { $base.PixelHeight - $height } else { ($base.PixelHeight - $height)/2 }
  $visual = [System.Windows.Media.DrawingVisual]::new(); $context = $visual.RenderOpen()
  $context.DrawImage($base, [Windows.Rect]::new(0, 0, $base.PixelWidth, $base.PixelHeight)); $context.DrawImage($overlay, [Windows.Rect]::new($x, $y, $width, $height)); $context.Close()
  $base = [System.Windows.Media.Imaging.RenderTargetBitmap]::new($base.PixelWidth, $base.PixelHeight, 96, 96, [System.Windows.Media.PixelFormats]::Pbgra32); $base.Render($visual)
}
@($env:ICO_SIZES -split ',' | ForEach-Object { [pscustomobject]@{ size=[int]$_; png=(Square $base ([int]$_)) } }) | ConvertTo-Json -Compress
"""

    payload = json.loads(
        _run_wpf_powershell(
            script,
            ICO_BASE_URI=Path(base_png_path).resolve().as_uri(),
            ICO_OVERLAY_URI=Path(sub_png_path).resolve().as_uri() if sub_png_path else "",
            ICO_OVERLAY_SCALE=str(sub_icon_area_scale_factor),
            ICO_VERTICAL=vertical,
            ICO_HORIZONTAL=horizontal,
            ICO_SIZES=",".join(map(str, sizes)),
        )
    )
    if isinstance(payload, dict):
        payload = [payload]
    layers = [(int(entry["size"]), base64.b64decode(entry["png"])) for entry in payload]
    offset = 6 + 16 * len(layers)
    entries: list[bytes] = []
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
    with open(output_path, "wb") as file:
        file.write(struct.pack("<HHH", 0, 1, len(layers)) + b"".join(entries) + data)
    return output_path
