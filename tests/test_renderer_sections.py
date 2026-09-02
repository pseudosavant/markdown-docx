from __future__ import annotations

from pathlib import Path
from zipfile import ZipFile

import pytest
from docx import Document

from markdown_docx.parser import parse_document
from markdown_docx.renderer import render_docx


def test_sections_change_geometry_and_page_break_does_not_add_section(tmp_path: Path) -> None:
    source = """# Portrait

<!-- markdown-docx: page-break -->

Still portrait.

<!-- markdown-docx
section:
  page_size: letter
  orientation: landscape
  margins:
    left: 0.75in
    right: 0.75in
-->

# Landscape

<!-- markdown-docx
section: default
-->

# Portrait again
"""
    model = parse_document(source, input_path=tmp_path / "input.md", source_name="input.md")
    output = tmp_path / "sections.docx"
    render_docx(model, output, template_path=None, base_dir=tmp_path, allow_remote_images=False)
    document = Document(output)
    assert len(document.sections) == 3
    assert document.sections[0].page_width.inches == pytest.approx(8.5, abs=0.01)
    assert document.sections[1].page_width.inches == pytest.approx(11, abs=0.01)
    assert document.sections[1].page_height.inches == pytest.approx(8.5, abs=0.01)
    assert document.sections[1].left_margin.inches == pytest.approx(0.75, abs=0.01)
    assert document.sections[2].page_width.inches == pytest.approx(8.5, abs=0.01)
    with ZipFile(output) as archive:
        xml = archive.read("word/document.xml").decode("utf-8")
    assert 'w:type="page"' in xml
