from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest
from docx import Document
from docx.oxml.ns import qn
from docx.shared import Inches

from markdown_docx.errors import RenderError
from markdown_docx.models import CodeBlock, ImageBlock, ListContentBlock, ParagraphBlock, TableBlock
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


def test_rich_list_item_keeps_native_numbering_and_nested_block_order(tmp_path: Path, png_file: Path) -> None:
    source = """1. Item

   ```text
   code line
   ```

   > Quoted detail

   | A | B |
   | --- | --- |
   | x | y |

   ![Chart](image.png)

   Continued detail

2. Next item
"""
    model = parse_document(source, input_path=tmp_path / "input.md", source_name="input.md")
    nested = [block for block in model.blocks if isinstance(block, ListContentBlock)]
    assert [type(block.content) for block in nested] == [CodeBlock, ParagraphBlock, TableBlock, ImageBlock]
    output = tmp_path / "lists.docx"
    render_docx(model, output, template_path=None, base_dir=tmp_path, allow_remote_images=False)
    document = Document(output)
    assert [paragraph.text for paragraph in document.paragraphs] == [
        "Item",
        "code line",
        "Quoted detail",
        "",
        "Continued detail",
        "Next item",
    ]
    assert [paragraph.style.name for paragraph in document.paragraphs[1:3]] == ["Code Block", "Quote"]
    assert [paragraph._p.pPr.numPr.numId.val for paragraph in document.paragraphs] == [
        document.paragraphs[0]._p.pPr.numPr.numId.val,
        0,
        0,
        0,
        0,
        document.paragraphs[0]._p.pPr.numPr.numId.val,
    ]
    assert document.tables[0].left_indent == Inches(0.25)
    assert document.tables[0].cell(1, 0).text == "x"
    assert document.inline_shapes[0].description == "Chart"


def test_list_item_can_start_with_a_table_and_link_to_its_nested_heading(tmp_path: Path) -> None:
    source = """[Jump](#nested-heading)

- | Name | Value |
  | --- | --- |
  | a | b |

  ## Nested heading

  After the heading
"""
    model = parse_document(source, input_path=tmp_path / "input.md", source_name="input.md")
    output = tmp_path / "nested.docx"
    render_docx(model, output, template_path=None, base_dir=tmp_path, allow_remote_images=False)
    document = Document(output)
    assert document.paragraphs[1].text == ""
    assert document.tables[0].cell(1, 0).text == "a"
    assert document.paragraphs[2].style.name == "Heading 2"
    assert document.paragraphs[2].paragraph_format.left_indent == Inches(0.25)
    assert document.paragraphs[0].hyperlinks[0].fragment


def test_task_list_uses_clickable_word_checkboxes(tmp_path: Path) -> None:
    source = "- [ ] Buy **milk**\n- [x] Pay bill\n- Plain item\n\n1. [X] Numbered task\n"
    model = parse_document(source, input_path=tmp_path / "input.md", source_name="input.md")
    output = tmp_path / "tasks.docx"
    render_docx(model, output, template_path=None, base_dir=tmp_path, allow_remote_images=False)
    paragraphs = Document(output).paragraphs
    assert [paragraph.text for paragraph in paragraphs] == [
        " Buy milk",
        " Pay bill",
        "Plain item",
        " Numbered task",
    ]
    assert [len(paragraph.checkboxes) for paragraph in paragraphs] == [1, 1, 0, 1]
    assert [paragraph.checkboxes[0].checked for paragraph in (paragraphs[0], paragraphs[1], paragraphs[3])] == [
        False,
        True,
        True,
    ]
    assert paragraphs[0]._p.pPr.numPr.numId.val == 0
    assert paragraphs[1]._p.pPr.numPr.numId.val == 0
    assert paragraphs[2]._p.pPr.numPr.numId.val != 0
    assert paragraphs[3]._p.pPr.numPr.numId.val != 0
    assert any(run.bold for run in paragraphs[0].runs if run.text == "milk")


@pytest.mark.parametrize("marker", ["-", "1."])
def test_default_template_uses_native_nine_level_lists(tmp_path: Path, marker: str) -> None:
    source = "".join(f"{'   ' * depth}{marker} Level {depth + 1}\n" for depth in range(9))
    model = parse_document(source, input_path=tmp_path / "input.md", source_name="input.md")
    output = tmp_path / "nine-levels.docx"
    render_docx(model, output, template_path=None, base_dir=tmp_path, allow_remote_images=False)
    document = Document(output)
    numbering = document.part.numbering_part.element
    paragraphs = document.paragraphs
    assert [paragraph._p.pPr.numPr.ilvl.val for paragraph in paragraphs] == list(range(9))
    assert [paragraph.style.name for paragraph in paragraphs] == [
        ("List Bullet" if marker == "-" else "List Number") + (f" {depth + 1}" if depth else "") for depth in range(9)
    ]
    assert len({paragraph._p.pPr.numPr.numId.val for paragraph in paragraphs}) == 1
    for paragraph in paragraphs:
        num = numbering.num_having_numId(paragraph._p.pPr.numPr.numId.val)
        abstract_id = num.abstractNumId.val
        abstract = numbering.xpath(f'./w:abstractNum[@w:abstractNumId="{abstract_id}"]')[0]
        assert len(abstract.findall(qn("w:lvl"))) == 9
        assert abstract.find(qn("w:multiLevelType")).get(qn("w:val")) == "multilevel"


def test_mixed_nested_lists_use_separate_native_sequences(tmp_path: Path) -> None:
    source = "1. Ordered\n   - Bullet\n      1. Number again\n"
    model = parse_document(source, input_path=tmp_path / "input.md", source_name="input.md")
    output = tmp_path / "mixed.docx"
    render_docx(model, output, template_path=None, base_dir=tmp_path, allow_remote_images=False)
    paragraphs = Document(output).paragraphs
    assert len({paragraph._p.pPr.numPr.numId.val for paragraph in paragraphs}) == 3


def test_custom_template_keeps_its_existing_list_definitions(
    tmp_path: Path, blank_template_factory: Callable[[str], Path]
) -> None:
    template = blank_template_factory("custom.docx")
    model = parse_document("1. Parent\n   1. Child\n", input_path=tmp_path / "input.md", source_name="input.md")
    output = tmp_path / "custom-lists.docx"
    render_docx(model, output, template_path=template, base_dir=tmp_path, allow_remote_images=False)
    paragraphs = Document(output).paragraphs
    assert paragraphs[0]._p.pPr.numPr.numId.val != paragraphs[1]._p.pPr.numPr.numId.val


def test_empty_image_placeholder_remains_on_list_item(tmp_path: Path) -> None:
    model = parse_document("- ![Network diagram]()\n", input_path=tmp_path / "input.md", source_name="input.md")
    output = tmp_path / "placeholder-list.docx"
    render_docx(model, output, template_path=None, base_dir=tmp_path, allow_remote_images=False)
    paragraphs = Document(output).paragraphs
    assert len(paragraphs) == 1
    assert paragraphs[0].text == "[Image: Network diagram]"
    assert paragraphs[0]._p.pPr.numPr.numId.val != 0
