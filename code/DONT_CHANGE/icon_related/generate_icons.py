import base64
import json
import os
import struct
import subprocess
import sys
import time
import zlib
from urllib.parse import quote

root_dir = os.path.normpath(os.path.dirname(os.path.abspath(__file__)) + "\\..\\..")
sys.path.insert(0, root_dir)

from DONT_CHANGE.specific_scripts.common_code import terminate_parent_console_launcher_if_safe

# settings
user_png_folder_path = "../../icons/"
fallback_png_folder_path = "./"
output_path = "../../icons/"
fallback_base_png_id = "200x200:82f0d3c0"
fallback_settings_png_id = "200x200:71db6cbb"
fallback_stop_png_id = "200x200:83248fd0"
ICON_DELETE_TIMEOUT_SECONDS = 5.0
ICON_RETRY_DELAY_SECONDS = 0.1
GENERATED_ICON_FILENAMES = ("icon.ico", "settings.ico", "stop.ico")

file_path = os.path.dirname(os.path.abspath(__file__))
os.chdir(file_path)

_POWERSHELL_SCRIPT = r"""
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName PresentationCore
Add-Type -AssemblyName WindowsBase

function Get-BgraBitmap([string]$uriText) {
    $bitmap = [System.Windows.Media.Imaging.BitmapImage]::new()
    $bitmap.BeginInit()
    $bitmap.UriSource = [System.Uri]::new($uriText)
    $bitmap.CacheOption = [System.Windows.Media.Imaging.BitmapCacheOption]::OnLoad
    $bitmap.CreateOptions = [System.Windows.Media.Imaging.BitmapCreateOptions]::PreservePixelFormat
    $bitmap.EndInit()

    return [System.Windows.Media.Imaging.FormatConvertedBitmap]::new(
        $bitmap,
        [System.Windows.Media.PixelFormats]::Bgra32,
        $null,
        0
    )
}

function Copy-BgraBytes([System.Windows.Media.Imaging.BitmapSource]$bitmap) {
    $stride = $bitmap.PixelWidth * 4
    $bytes = New-Object byte[] ($stride * $bitmap.PixelHeight)
    $bitmap.CopyPixels($bytes, $stride, 0)
    return $bytes
}

function Encode-PngBase64([System.Windows.Media.Imaging.BitmapSource]$bitmap) {
    $encoder = [System.Windows.Media.Imaging.PngBitmapEncoder]::new()
    $encoder.Frames.Add([System.Windows.Media.Imaging.BitmapFrame]::Create($bitmap))
    $stream = [System.IO.MemoryStream]::new()
    try {
        $encoder.Save($stream)
        return [Convert]::ToBase64String($stream.ToArray())
    }
    finally {
        $stream.Dispose()
    }
}

function Render-SquareIcon([System.Windows.Media.Imaging.BitmapSource]$bitmap, [int]$size) {
    $scale = $size / [double][Math]::Max($bitmap.PixelWidth, $bitmap.PixelHeight)
    $newWidth = [Math]::Max(1, [int][Math]::Round($bitmap.PixelWidth * $scale))
    $newHeight = [Math]::Max(1, [int][Math]::Round($bitmap.PixelHeight * $scale))
    $offsetX = [int](($size - $newWidth) / 2)
    $offsetY = [int](($size - $newHeight) / 2)

    $visual = [System.Windows.Media.DrawingVisual]::new()
    [System.Windows.Media.RenderOptions]::SetBitmapScalingMode(
        $visual,
        [System.Windows.Media.BitmapScalingMode]::HighQuality
    )

    $context = $visual.RenderOpen()
    $context.DrawImage(
        $bitmap,
        [System.Windows.Rect]::new($offsetX, $offsetY, $newWidth, $newHeight)
    )
    $context.Close()

    $rendered = [System.Windows.Media.Imaging.RenderTargetBitmap]::new(
        $size,
        $size,
        96,
        96,
        [System.Windows.Media.PixelFormats]::Pbgra32
    )
    $rendered.Render($visual)

    return [System.Windows.Media.Imaging.FormatConvertedBitmap]::new(
        $rendered,
        [System.Windows.Media.PixelFormats]::Bgra32,
        $null,
        0
    )
}

function Compose-Overlay(
    [System.Windows.Media.Imaging.BitmapSource]$baseBitmap,
    [System.Windows.Media.Imaging.BitmapSource]$overlayBitmap,
    [double]$overlayScaleFactor
) {
    $baseMax = [double][Math]::Max($baseBitmap.PixelWidth, $baseBitmap.PixelHeight)
    $overlayMax = [double][Math]::Max($overlayBitmap.PixelWidth, $overlayBitmap.PixelHeight)
    $scale = ($baseMax / $overlayMax) * $overlayScaleFactor
    $overlayWidth = [Math]::Max(1, [int][Math]::Round($overlayBitmap.PixelWidth * $scale))
    $overlayHeight = [Math]::Max(1, [int][Math]::Round($overlayBitmap.PixelHeight * $scale))
    $posX = $baseBitmap.PixelWidth - $overlayWidth
    $posY = $baseBitmap.PixelHeight - $overlayHeight

    $visual = [System.Windows.Media.DrawingVisual]::new()
    [System.Windows.Media.RenderOptions]::SetBitmapScalingMode(
        $visual,
        [System.Windows.Media.BitmapScalingMode]::HighQuality
    )

    $context = $visual.RenderOpen()
    $context.DrawImage(
        $baseBitmap,
        [System.Windows.Rect]::new(0, 0, $baseBitmap.PixelWidth, $baseBitmap.PixelHeight)
    )
    $context.DrawImage(
        $overlayBitmap,
        [System.Windows.Rect]::new($posX, $posY, $overlayWidth, $overlayHeight)
    )
    $context.Close()

    $rendered = [System.Windows.Media.Imaging.RenderTargetBitmap]::new(
        $baseBitmap.PixelWidth,
        $baseBitmap.PixelHeight,
        96,
        96,
        [System.Windows.Media.PixelFormats]::Pbgra32
    )
    $rendered.Render($visual)

    return [System.Windows.Media.Imaging.FormatConvertedBitmap]::new(
        $rendered,
        [System.Windows.Media.PixelFormats]::Bgra32,
        $null,
        0
    )
}

$operation = $env:ICON_OPERATION
switch ($operation) {
    'image-id' {
        $bitmap = Get-BgraBitmap $env:ICON_BASE_URI
        [pscustomobject]@{
            width = $bitmap.PixelWidth
            height = $bitmap.PixelHeight
            bgra_base64 = [Convert]::ToBase64String((Copy-BgraBytes $bitmap))
        } | ConvertTo-Json -Compress
        break
    }
    'render-icon' {
        $bitmap = Get-BgraBitmap $env:ICON_BASE_URI
        if ($env:ICON_OVERLAY_URI) {
            $overlayBitmap = Get-BgraBitmap $env:ICON_OVERLAY_URI
            $bitmap = Compose-Overlay $bitmap $overlayBitmap ([double]$env:ICON_OVERLAY_SCALE_FACTOR)
        }

        $sizes = $env:ICON_SIZES -split ',' | ForEach-Object { [int]$_ }
        $entries = foreach ($size in $sizes) {
            $iconBitmap = Render-SquareIcon $bitmap $size
            [pscustomobject]@{
                size = $size
                png_base64 = Encode-PngBase64 $iconBitmap
            }
        }

        @($entries) | ConvertTo-Json -Compress
        break
    }
    default {
        throw "Unsupported ICON_OPERATION: $operation"
    }
}
"""


def _run_powershell(**extra_env: str) -> str:
    env = os.environ.copy()
    env.update(extra_env)

    try:
        completed = subprocess.run(  # noqa:S603
            [
                "powershell.exe",
                "-NoProfile",
                "-NonInteractive",
                "-STA",
                "-Command",
                _POWERSHELL_SCRIPT,
            ],
            capture_output=True,
            text=True,
            check=False,
            env=env,
        )
    except FileNotFoundError as exc:
        raise RuntimeError("powershell.exe was not found. This script requires Windows PowerShell.") from exc

    if completed.returncode != 0:
        stderr = completed.stderr.strip() or completed.stdout.strip() or "Unknown PowerShell error."
        raise RuntimeError(stderr)

    return completed.stdout.strip()


def _path_to_uri(path: str) -> str:
    absolute_path = os.path.abspath(path)
    uri_path = quote(absolute_path.replace("\\", "/"), safe="/:")
    if absolute_path.startswith("\\\\"):
        return f"file:{uri_path}"
    return f"file:///{uri_path}"


def _bgra_to_rgba(bgra_bytes: bytes) -> bytes:
    rgba = bytearray(len(bgra_bytes))
    rgba[0::4] = bgra_bytes[2::4]
    rgba[1::4] = bgra_bytes[1::4]
    rgba[2::4] = bgra_bytes[0::4]
    rgba[3::4] = bgra_bytes[3::4]
    return bytes(rgba)


def _load_image_data(path: str) -> tuple[int, int, bytes]:
    payload = json.loads(
        _run_powershell(
            ICON_OPERATION="image-id",
            ICON_BASE_URI=_path_to_uri(path),
        )
    )

    return (
        int(payload["width"]),
        int(payload["height"]),
        base64.b64decode(payload["bgra_base64"]),
    )


def _render_png_layers(
    base_path: str,
    icon_sizes: tuple[int, ...],
    overlay_path: str | None = None,
    overlay_scale_factor: float = 0.6,
) -> list[tuple[int, bytes]]:
    raw_payload = _run_powershell(
        ICON_OPERATION="render-icon",
        ICON_BASE_URI=_path_to_uri(base_path),
        ICON_OVERLAY_URI=_path_to_uri(overlay_path) if overlay_path else "",
        ICON_OVERLAY_SCALE_FACTOR=str(overlay_scale_factor),
        ICON_SIZES=",".join(str(size) for size in icon_sizes),
    )

    payload = json.loads(raw_payload)
    if isinstance(payload, dict):
        payload = [payload]

    return [(int(entry["size"]), base64.b64decode(entry["png_base64"])) for entry in payload]


def _build_ico(layers: list[tuple[int, bytes]]) -> bytes:
    icon_dir = struct.pack("<HHH", 0, 1, len(layers))
    directory_entries = []
    image_data = bytearray()
    offset = 6 + (16 * len(layers))

    for size, png_bytes in layers:
        directory_entries.append(
            struct.pack(
                "<BBBBHHII",
                0 if size >= 256 else size,
                0 if size >= 256 else size,
                0,
                0,
                1,
                32,
                len(png_bytes),
                offset,
            )
        )
        image_data.extend(png_bytes)
        offset += len(png_bytes)

    return icon_dir + b"".join(directory_entries) + bytes(image_data)


def create_icon(
    image_path,
    output_path,
    icon_sizes=(256, 128, 64, 48, 32, 16),
    background_color=(0, 0, 0, 0),  # transparent
):
    """
    Convert an image into a multi-resolution .ico file with padding
    to preserve aspect ratio (no distortion).

    background_color=(0, 0, 0, 0) means transparent background.
    The parameter is kept for API compatibility with generate_icons.py.
    """

    _ = background_color
    layers = _render_png_layers(image_path, tuple(icon_sizes))
    with open(output_path, "wb") as output_file:
        output_file.write(_build_ico(layers))


def create_composite_icon(
    base_path,
    overlay_path,
    output_path,
    overlay_scale_factor=0.6,
    icon_sizes=(256, 128, 64, 48, 32, 16),
    background_color=(0, 0, 0, 0),  # transparent padding
):
    """
    Create a composite icon:
    - Place overlay on the bottom-right of base.
    - Preserve aspect ratio.
    - Pad to square for each icon size (no distortion).

    background_color=(0, 0, 0, 0) means transparent background.
    The parameter is kept for API compatibility with generate_icons.py.
    """

    _ = background_color
    layers = _render_png_layers(
        base_path,
        tuple(icon_sizes),
        overlay_path=overlay_path,
        overlay_scale_factor=overlay_scale_factor,
    )
    with open(output_path, "wb") as output_file:
        output_file.write(_build_ico(layers))


def image_id(path: str) -> str:
    width, height, bgra_bytes = _load_image_data(path)
    rgba_bytes = _bgra_to_rgba(bgra_bytes)
    crc = zlib.crc32(rgba_bytes) & 0xFFFFFFFF
    return f"{width}x{height}:{crc:08x}"


def _pick_icon_path(user_path: str, fallback_path: str, fallback_image_id: str, label: str) -> str:
    if os.path.exists(user_path):
        if image_id(user_path) == fallback_image_id:
            print(f"Using fallback {label} icon.")
            return fallback_path
        return user_path

    print(f"Using fallback {label} icon because {os.path.basename(user_path)} is missing.")
    return fallback_path


def _pause_before_exit() -> None:
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        return

    print()
    input("Press enter to exit.")
    terminate_parent_console_launcher_if_safe()


def _delete_existing_icon(path: str) -> None:
    if not os.path.exists(path):
        return

    deadline = time.monotonic() + ICON_DELETE_TIMEOUT_SECONDS
    last_error = None

    while os.path.exists(path):
        try:
            os.remove(path)
        except FileNotFoundError:
            return
        except OSError as error:
            last_error = error

        if not os.path.exists(path):
            return

        if time.monotonic() >= deadline:
            detail = f" Last Windows error: {last_error}" if last_error else ""
            raise RuntimeError(
                f'Failed to delete existing icon within {ICON_DELETE_TIMEOUT_SECONDS:.1f} seconds: "{path}". '
                f"Close any program using the file and try again.{detail}"
            )

        time.sleep(ICON_RETRY_DELAY_SECONDS)


def delete_existing_generated_icons() -> None:
    for filename in GENERATED_ICON_FILENAMES:
        path = os.path.join(output_path, filename)
        _delete_existing_icon(path)
        if os.path.exists(path):
            raise RuntimeError(f'Icon still exists after deletion attempt: "{path}"')


if __name__ == "__main__":
    if len(sys.argv) > 1:
        overlay_scale_factor = float(sys.argv[1])
    else:
        overlay_scale_factor = 0.6

    try:
        delete_existing_generated_icons()
    except Exception as e:
        print(f"Error deleting old icon files: {e}")
        _pause_before_exit()
        sys.exit(1)

    base_icon_path = _pick_icon_path(
        user_png_folder_path + "icon.png",
        fallback_png_folder_path + "default_icon.png",
        fallback_base_png_id,
        "base",
    )
    settings_icon_path = _pick_icon_path(
        user_png_folder_path + "settings.png",
        fallback_png_folder_path + "default_settings.png",
        fallback_settings_png_id,
        "settings",
    )
    stop_icon_path = _pick_icon_path(
        user_png_folder_path + "stop.png",
        fallback_png_folder_path + "default_stop.png",
        fallback_stop_png_id,
        "stop",
    )

    try:
        create_icon(base_icon_path, output_path + "icon.ico")
        print("Generated: icon.ico")
    except Exception as e:
        print(f"Error creating icon.ico: {e}")

    try:
        create_composite_icon(base_icon_path, settings_icon_path, output_path + "settings.ico", overlay_scale_factor)
        print("Generated: settings.ico")
    except Exception as e:
        print(f"Error creating settings.ico: {e}")

    try:
        create_composite_icon(base_icon_path, stop_icon_path, output_path + "stop.ico", overlay_scale_factor)
        print("Generated: stop.ico")
    except Exception as e:
        print(f"Error creating stop.ico: {e}")

    _pause_before_exit()
