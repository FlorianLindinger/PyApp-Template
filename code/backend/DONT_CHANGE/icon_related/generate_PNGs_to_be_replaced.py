import os
import zlib

from PIL import Image, ImageDraw, ImageFont

OUT_DIR = os.path.dirname(os.path.abspath(__file__))

SIZE = 512
FONT_SIZE = 100
MIN_FONT_SIZE = 8

TEXT_COLOR = (210, 0, 0, 255)
BG_COLOR = (255, 255, 255, 255)
FONT = "C:/Windows/Fonts/arialbd.ttf"

items = {
    "icon.png": [
        "Replace to change",
        "base icon. Run",
        '"regenerate icons"',
        "afterwards",
    ],
    "settings.png": [
        "Replace to change",
        "settings sub-icon. Run",
        '"regenerate icons"',
        "afterwards",
    ],
    "stop.png": [
        "Replace to change",
        "stop sub-icon. Run",
        '"regenerate icons"',
        "afterwards",
    ],
    "log.png": [
        "Replace to change",
        "log sub-icon. Run",
        '"regenerate icons"',
        "afterwards",
    ],
}


def make_icon(filename, lines):
    img = Image.new("RGBA", (SIZE, SIZE), BG_COLOR)
    draw = ImageDraw.Draw(img)

    font_size = FONT_SIZE

    while font_size > MIN_FONT_SIZE:
        font = ImageFont.truetype(FONT, font_size)
        boxes = [draw.textbbox((0, 0), line, font=font) for line in lines]

        widths = [b[2] - b[0] for b in boxes]
        heights = [b[3] - b[1] for b in boxes]

        spacing = max(2, font_size // 4)
        total_h = sum(heights) + spacing * (len(lines) - 1)

        if max(widths) <= SIZE - 20 and total_h <= SIZE - 20:
            break

        font_size -= 2

    y = (SIZE - total_h) / 2

    for line, box in zip(lines, boxes):
        w = box[2] - box[0]
        h = box[3] - box[1]

        x = (SIZE - w) / 2
        draw.text((x, y - box[1]), line, font=font, fill=TEXT_COLOR)

        y += h + spacing

    img.save(os.path.join(OUT_DIR, filename))


def image_id(path):
    image = Image.open(path).convert("RGBA")
    crc = zlib.crc32(image.tobytes()) & 0xFFFFFFFF
    return f"{image.width}x{image.height}:{crc:08x}"


created_paths = []
for filename, lines in items.items():
    make_icon(filename, lines)
    created_paths.append(os.path.join(OUT_DIR, filename))

print("Created icon.png, settings.png, stop.png, log.png")
print("Image IDs:")
for path in created_paths:
    print(f"  {os.path.basename(path)}: {image_id(path)}")
