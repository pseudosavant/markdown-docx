from __future__ import annotations

import argparse
from pathlib import Path

from docx import Document
from docx.shared import Pt, RGBColor


def build_templates(source: Path, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    variants = [
        ("arial-navy.docx", "Arial", RGBColor(0x1F, 0x4D, 0x78), 11),
        ("georgia-burgundy.docx", "Georgia", RGBColor(0x78, 0x1F, 0x2F), 10.5),
    ]
    for filename, font_name, heading_color, body_size in variants:
        document = Document(str(source))
        document.styles["Normal"].font.name = font_name
        document.styles["Normal"].font.size = Pt(body_size)
        for level in range(1, 7):
            style = document.styles[f"Heading {level}"]
            style.font.name = font_name
            style.font.color.rgb = heading_color
        for name in ("List Bullet", "List Bullet 2", "List Bullet 3", "List Number", "List Number 2", "List Number 3"):
            document.styles[name].font.name = font_name
        document.save(output_dir / filename)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()
    build_templates(args.source, args.output_dir)


if __name__ == "__main__":
    main()
