from __future__ import annotations

from pathlib import Path

import pytest

from markdown_docx.errors import ParseError, UnsupportedFeatureError
from markdown_docx.models import (
    CodeBlock,
    HeadingBlock,
    ImageBlock,
    ListParagraphBlock,
    PageBreakBlock,
    ParagraphBlock,
    SectionBreakBlock,
    TableBlock,
)
from markdown_docx.parser import parse_document


def parse(source: str):
    return parse_document(source, input_path=Path("input.md"), source_name="input.md")


def test_parse_supported_block_types_in_order() -> None:
    model = parse(
        """# Heading

Paragraph with **bold**, *italic*, and `code`.

> Quote one.
>
> Quote two.

```text
code block
```

1. Ordered
   - Nested bullet

| A | B |
| :--- | ---: |
| x | y |

![Image](image.png)
"""
    )
    assert [type(block) for block in model.blocks] == [
        HeadingBlock,
        ParagraphBlock,
        ParagraphBlock,
        ParagraphBlock,
        CodeBlock,
        ListParagraphBlock,
        ListParagraphBlock,
        TableBlock,
        ImageBlock,
    ]
    paragraph = model.blocks[1]
    assert isinstance(paragraph, ParagraphBlock)
    assert [(f.text, f.bold, f.italic, f.code) for f in paragraph.fragments if f.kind == "text"] == [
        ("Paragraph with ", False, False, False),
        ("bold", True, False, False),
        (", ", False, False, False),
        ("italic", False, True, False),
        (", and ", False, False, False),
        ("code", False, False, True),
        (".", False, False, False),
    ]


def test_hard_break_becomes_break_fragment_and_soft_break_becomes_space() -> None:
    paragraph = parse("first  \nsecond\nthird\n").blocks[0]
    assert isinstance(paragraph, ParagraphBlock)
    assert [fragment.kind for fragment in paragraph.fragments] == ["text", "break", "text"]
    assert paragraph.fragments[-1].text == "second third"


def test_page_break_and_section_are_explicit_blocks() -> None:
    model = parse(
        "# One\n\n<!-- markdown-docx: page-break -->\n\nText\n\n<!-- markdown-docx\nsection: default\n-->\n\n# Two\n"
    )
    assert any(isinstance(block, PageBreakBlock) for block in model.blocks)
    assert any(isinstance(block, SectionBreakBlock) for block in model.blocks)


def test_table_metadata_attaches_and_parses_alignment() -> None:
    model = parse(
        """<!-- markdown-docx
table:
  style: Table Grid
  alignment: center
  width: page
  column_widths: [3, 1]
-->

| Item | Count |
| :--- | ---: |
| Widget | 2 |
"""
    )
    table = model.blocks[0]
    assert isinstance(table, TableBlock)
    assert table.options.alignment == "center"
    assert table.options.column_widths == (3.0, 1.0)
    assert [cell.alignment for cell in table.headers] == ["left", "right"]


def test_table_metadata_requires_matching_width_count() -> None:
    with pytest.raises(ParseError) as excinfo:
        parse("<!-- markdown-docx\ntable:\n  column_widths: [1]\n-->\n\n| A | B |\n| --- | --- |\n| x | y |\n")
    assert excinfo.value.context.code == "table_shape_invalid"


def test_image_metadata_requires_standalone_image() -> None:
    with pytest.raises(ParseError) as excinfo:
        parse("<!-- markdown-docx\nimage:\n  width: 40%\n-->\n\nText ![image](x.png)\n")
    assert excinfo.value.context.code == "metadata_placement_error"


def test_image_metadata_parses_width_and_alignment() -> None:
    image = parse("<!-- markdown-docx\nimage:\n  width: 40%\n  alignment: right\n-->\n\n![image](x.png)\n").blocks[0]
    assert isinstance(image, ImageBlock)
    assert image.options.width == 40
    assert image.options.width_is_percent is True
    assert image.options.alignment == "right"


@pytest.mark.parametrize(
    ("source", "code"),
    [
        ("[link](https://example.com)\n", "unsupported_feature"),
        ("<span>raw</span>\n", "unsupported_markdown"),
        ("Title\n=====\n", "unsupported_markdown"),
        ("---\n", "unsupported_markdown"),
        ("    indented\n", "unsupported_markdown"),
        ("- [ ] task\n", "unsupported_markdown"),
        ("Text[^1]\n\n[^1]: Note\n", "unsupported_markdown"),
    ],
)
def test_unsupported_markdown_is_rejected(source: str, code: str) -> None:
    with pytest.raises(UnsupportedFeatureError) as excinfo:
        parse(source)
    assert excinfo.value.context.code == code


def test_footnote_like_text_inside_code_is_allowed() -> None:
    model = parse("`[^1]` is literal.\n")
    assert isinstance(model.blocks[0], ParagraphBlock)


def test_non_reserved_html_comment_is_rejected() -> None:
    with pytest.raises(UnsupportedFeatureError):
        parse("<!-- ordinary comment -->\n")


def test_unknown_compact_directive_is_rejected() -> None:
    with pytest.raises(ParseError) as excinfo:
        parse("<!-- markdown-docx: column-break -->\n")
    assert excinfo.value.context.code == "unknown_metadata_key"


def test_list_depth_uses_configured_style_count() -> None:
    source = "1. one\n   1. two\n      1. three\n         1. four\n"
    with pytest.raises(ParseError) as excinfo:
        parse(source)
    assert excinfo.value.context.code == "list_depth_unsupported"


def test_ordered_list_must_begin_with_one() -> None:
    with pytest.raises(ParseError) as excinfo:
        parse("3. three\n")
    assert excinfo.value.context.code == "ordered_list_start_unsupported"


def test_multi_paragraph_list_item_is_rejected() -> None:
    with pytest.raises(UnsupportedFeatureError):
        parse("- first\n\n  second paragraph\n")
