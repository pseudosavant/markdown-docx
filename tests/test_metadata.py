from __future__ import annotations

from pathlib import Path

import pytest

from markdown_docx.errors import ParseError
from markdown_docx.metadata import EMU_PER_INCH, EMU_PER_MM
from markdown_docx.models import SectionBreakBlock
from markdown_docx.parser import parse_document


def parse(source: str):
    return parse_document(source, input_path=Path("input.md"), source_name="input.md")


def test_defaults_are_letter_portrait_with_one_inch_margins() -> None:
    model = parse("# Title\n")
    section = model.options.section
    assert section.page_size.name == "letter"
    assert section.orientation == "portrait"
    assert section.margins.top == EMU_PER_INCH
    assert section.usable_width == int(6.5 * EMU_PER_INCH)


def test_document_metadata_parses_geometry_styles_and_fonts() -> None:
    model = parse(
        """<!-- markdown-docx
document:
  page_size: a4
  orientation: landscape
  margins:
    top: 20mm
    right: 15mm
    bottom: 20mm
    left: 15mm
  styles:
    paragraph: Body
    headings:
      1: Display
    ordered_list: [Numbered]
  fonts:
    body: Arial
    headings: Arial
    monospace: Cascadia Mono
-->

# Title
"""
    )
    assert model.options.section.page_size.name == "a4"
    assert model.options.section.orientation == "landscape"
    assert model.options.section.margins.right == 15 * EMU_PER_MM
    assert model.options.styles.paragraph == "Body"
    assert model.options.styles.headings[1] == "Display"
    assert model.options.styles.headings[2] == "Heading 2"
    assert model.options.styles.ordered_list == ["Numbered"]
    assert model.options.fonts.monospace == "Cascadia Mono"


def test_duplicate_yaml_key_is_rejected_with_line() -> None:
    with pytest.raises(ParseError) as excinfo:
        parse("<!-- markdown-docx\ndocument:\n  page_size: letter\n  page_size: a4\n-->\n")
    assert excinfo.value.context.code == "metadata_parse_error"
    assert excinfo.value.context.line == 4


def test_unknown_metadata_key_is_rejected() -> None:
    with pytest.raises(ParseError) as excinfo:
        parse("<!-- markdown-docx\ndocument:\n  paper: letter\n-->\n")
    assert excinfo.value.context.code == "unknown_metadata_key"
    assert excinfo.value.context.details == {"key": "paper"}


@pytest.mark.parametrize("value", ["1", "1inch", "12px", "0in"])
def test_invalid_lengths_are_rejected(value: str) -> None:
    with pytest.raises(ParseError) as excinfo:
        parse(f"<!-- markdown-docx\ndocument:\n  margins:\n    top: {value}\n-->\n")
    assert excinfo.value.context.code == "metadata_parse_error"


def test_margins_must_leave_positive_page_area() -> None:
    with pytest.raises(ParseError) as excinfo:
        parse("<!-- markdown-docx\ndocument:\n  margins:\n    left: 5in\n    right: 5in\n-->\n")
    assert excinfo.value.context.code == "invalid_page_geometry"


def test_custom_page_size_uses_nominal_portrait_dimensions() -> None:
    model = parse(
        "<!-- markdown-docx\ndocument:\n  page_size:\n    width: 7in\n    height: 10in\n  orientation: landscape\n-->\n"
    )
    section = model.options.section
    assert section.effective_width == 10 * EMU_PER_INCH
    assert section.effective_height == 7 * EMU_PER_INCH


def test_custom_page_width_cannot_exceed_height() -> None:
    with pytest.raises(ParseError):
        parse("<!-- markdown-docx\ndocument:\n  page_size:\n    width: 10in\n    height: 7in\n-->\n")


def test_document_metadata_must_be_first() -> None:
    with pytest.raises(ParseError) as excinfo:
        parse("# Before\n\n<!-- markdown-docx\ndocument:\n  page_size: a4\n-->\n")
    assert excinfo.value.context.code == "metadata_placement_error"


def test_section_starts_from_document_defaults() -> None:
    model = parse(
        """<!-- markdown-docx
document:
  page_size: a4
  margins:
    left: 20mm
-->

# First

<!-- markdown-docx
section:
  orientation: landscape
  margins:
    left: 10mm
-->

# Second

<!-- markdown-docx
section:
  page_size: legal
-->

# Third
"""
    )
    sections = [block.settings for block in model.blocks if isinstance(block, SectionBreakBlock)]
    assert sections[0].orientation == "landscape"
    assert sections[0].margins.left == 10 * EMU_PER_MM
    assert sections[1].orientation == "portrait"
    assert sections[1].margins.left == 20 * EMU_PER_MM


def test_section_default_resets_document_geometry() -> None:
    model = parse("# One\n\n<!-- markdown-docx\nsection: default\n-->\n\n# Two\n")
    section = next(block for block in model.blocks if isinstance(block, SectionBreakBlock))
    assert section.settings == model.options.section


def test_attached_metadata_cannot_stack() -> None:
    with pytest.raises(ParseError) as excinfo:
        parse("<!-- markdown-docx: page-break -->\n<!-- markdown-docx\nsection: default\n-->\n\n# Heading\n")
    assert excinfo.value.context.code == "metadata_placement_error"
