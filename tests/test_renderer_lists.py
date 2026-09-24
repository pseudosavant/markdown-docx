from __future__ import annotations

from pathlib import Path

import pytest
from docx import Document
from docx.oxml.ns import qn
from docx.shared import Inches

from markdown_docx.errors import RenderError
from markdown_docx.parser import parse_document
from markdown_docx.renderer import render_docx


def test_ordered_unordered_nested_and_mixed_lists_use_real_styles(tmp_path: Path) -> None:
    source = """- Bullet
  1. Nested number
     - Deep bullet
- Second bullet

1. Number
   - Nested bullet
"""
    model = parse_document(source, input_path=tmp_path / "input.md", source_name="input.md")
    output = tmp_path / "lists.docx"
    render_docx(model, output, template_path=None, base_dir=tmp_path, allow_remote_images=False)
    document = Document(output)
    assert [paragraph.style.name for paragraph in document.paragraphs] == [
        "List Bullet",
        "List Number 2",
        "List Bullet 3",
        "List Bullet",
        "List Number",
        "List Bullet 2",
    ]
    assert [paragraph.text for paragraph in document.paragraphs] == [
        "Bullet",
        "Nested number",
        "Deep bullet",
        "Second bullet",
        "Number",
        "Nested bullet",
    ]


def test_starts_restarts_and_continuations_use_native_numbering(tmp_path: Path) -> None:
    model = parse_document(
        "3. Third\n\n   More third\n\n   - Child\n\n   After child\n\n9. Fourth\n\nParagraph\n\n1. New first\n",
        input_path=tmp_path / "input.md",
        source_name="input.md",
    )
    output = tmp_path / "lists.docx"
    render_docx(model, output, template_path=None, base_dir=tmp_path, allow_remote_images=False)
    document = Document(output)
    paragraphs = document.paragraphs
    ids = [p._p.pPr.numPr.numId.val for p in paragraphs if p._p.pPr.numPr is not None]
    assert ids[0] == ids[4]
    assert ids[1] == ids[3] == 0
    assert len({ids[0], ids[2], ids[5]}) == 3
    numbering = document.part.numbering_part.element
    first = numbering.num_having_numId(ids[0])
    last = numbering.num_having_numId(ids[5])
    assert first.lvlOverride_lst[0].startOverride.val == 3
    assert last.lvlOverride_lst[0].startOverride.val == 1
    assert paragraphs[1].paragraph_format.first_line_indent == 0
    assert paragraphs[1].paragraph_format.left_indent == Inches(0.25)
    assert paragraphs[4].text == "Fourth"
    assert paragraphs[1]._p.xpath("./w:pPr/w:ind/@w:hanging") == []
    assert first.find(qn("w:abstractNumId")) is not None


def test_list_style_without_numbering_has_line_aware_error(tmp_path: Path) -> None:
    source = "<!-- markdown-docx\ndocument:\n  styles:\n    ordered_list: [Normal]\n-->\n\n1. Item\n"
    model = parse_document(source, input_path=tmp_path / "input.md", source_name="input.md")
    with pytest.raises(RenderError) as error:
        render_docx(model, tmp_path / "out.docx", template_path=None, base_dir=tmp_path, allow_remote_images=False)
    assert error.value.context.code == "list_numbering_invalid"
    assert error.value.context.line == 7
