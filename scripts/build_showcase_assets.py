from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def build_image(output: Path) -> None:
    image = Image.new("RGB", (1200, 420), "#F2F4F7")
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default(size=26)
    small = ImageFont.load_default(size=20)
    boxes = [
        (70, 120, 330, 300, "Readable Markdown", "Strict source"),
        (470, 120, 730, 300, "markdown-docx", "Public APIs"),
        (870, 120, 1130, 300, "Editable Word", "Real styles"),
    ]
    colors = ["#E8EEF5", "#2E74B5", "#E8EEF5"]
    for index, (left, top, right, bottom, title, subtitle) in enumerate(boxes):
        draw.rounded_rectangle((left, top, right, bottom), radius=24, fill=colors[index], outline="#1F4D78", width=4)
        title_color = "white" if index == 1 else "#0B2545"
        subtitle_color = "#E8EEF5" if index == 1 else "#555555"
        draw.text(((left + right) / 2, top + 62), title, fill=title_color, font=font, anchor="mm")
        draw.text(((left + right) / 2, top + 118), subtitle, fill=subtitle_color, font=small, anchor="mm")
    for x in (380, 780):
        draw.line((x, 210, x + 40, 210), fill="#2E74B5", width=8)
        draw.polygon(((x + 40, 198), (x + 60, 210), (x + 40, 222)), fill="#2E74B5")
    output.parent.mkdir(parents=True, exist_ok=True)
    image.save(output, dpi=(150, 150))


def build_icon(output: Path) -> None:
    image = Image.new("RGBA", (210, 70), (255, 255, 255, 0))
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default(size=22)
    draw.rounded_rectangle(
        (2, 2, 207, 67),
        radius=14,
        fill="#2E74B5",
        outline="#1F4D78",
        width=3,
    )
    draw.text((105, 35), "DOCX", fill="white", font=font, anchor="mm")
    output.parent.mkdir(parents=True, exist_ok=True)
    image.save(output, dpi=(150, 150))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    parser.add_argument("--icon-output", type=Path)
    args = parser.parse_args()
    build_image(args.output)
    if args.icon_output is not None:
        build_icon(args.icon_output)


if __name__ == "__main__":
    main()
