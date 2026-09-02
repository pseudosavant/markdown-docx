from __future__ import annotations

import base64
from collections.abc import Callable
from pathlib import Path

import pytest
from docx import Document
from docx.enum.style import WD_STYLE_TYPE

PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


@pytest.fixture
def png_file(tmp_path: Path) -> Path:
    path = tmp_path / "image.png"
    path.write_bytes(PNG_1X1)
    return path


@pytest.fixture
def blank_template_factory(tmp_path: Path) -> Callable[[str], Path]:
    def create(name: str = "template.docx") -> Path:
        document = Document()
        if "Code Block" not in document.styles:
            document.styles.add_style("Code Block", WD_STYLE_TYPE.PARAGRAPH)
        path = tmp_path / name
        document.save(path)
        return path

    return create
