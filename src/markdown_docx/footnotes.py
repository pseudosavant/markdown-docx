"""Resolve named Markdown footnotes before creating Word content."""

from __future__ import annotations

from markdown_it.token import Token

from markdown_docx.errors import ParseError
from markdown_docx.markdown_body import parse_inline
from markdown_docx.models import (
    Block,
    FootnoteDefinition,
    HeadingBlock,
    ListContentBlock,
    ListParagraphBlock,
    ParagraphBlock,
    TableBlock,
)


def consume_footnote(tokens: list[Token], index: int, *, input_path: str) -> tuple[FootnoteDefinition, int]:
    opening = tokens[index]
    line = opening.map[0] + 1 if opening.map else 1
    note = FootnoteDefinition(label=opening.meta["label"], line=line, paragraphs=[])
    index += 1
    while index < len(tokens) and tokens[index].type != "footnote_reference_close":
        token = tokens[index]
        content_line = token.map[0] + 1 if token.map else line
        if (
            token.type != "paragraph_open"
            or index + 2 >= len(tokens)
            or tokens[index + 1].type != "inline"
            or tokens[index + 2].type != "paragraph_close"
        ):
            raise ParseError(
                "footnote_content_unsupported",
                "Footnotes support text paragraphs, inline formatting, and links.",
                line=content_line,
                input_path=input_path,
            )
        fragments = parse_inline(tokens[index + 1], line=content_line, input_path=input_path)
        if any(fragment.kind in {"footnote", "image"} for fragment in fragments):
            raise ParseError(
                "footnote_content_unsupported",
                "Images and nested footnote references are unsupported inside footnotes.",
                line=content_line,
                input_path=input_path,
            )
        note.paragraphs.append(ParagraphBlock(line=content_line, fragments=fragments))
        index += 3
    if not note.paragraphs:
        note.paragraphs.append(ParagraphBlock(line=line, fragments=[]))
    return note, index + 1


def validate_footnotes(blocks: list[Block], notes: dict[str, FootnoteDefinition], *, input_path: str) -> None:
    used: set[str] = set()
    for block in blocks:
        if isinstance(block, ListContentBlock):
            block = block.content
        if isinstance(block, (ParagraphBlock, HeadingBlock, ListParagraphBlock)):
            groups = [block.fragments]
        elif isinstance(block, TableBlock):
            groups = [cell.fragments for row in [block.headers, *block.rows] for cell in row]
        else:
            continue
        for fragments in groups:
            for fragment in fragments:
                if fragment.kind != "footnote":
                    continue
                label = fragment.footnote_label or ""
                line = fragment.reference_line or block.line
                if label not in notes:
                    raise ParseError(
                        "footnote_undefined", f"Footnote {label!r} has no definition.", line=line, input_path=input_path
                    )
                if label in used:
                    raise ParseError(
                        "footnote_repeated_reference",
                        f"Footnote {label!r} is referenced more than once. Native reference reuse is unsupported.",
                        line=line,
                        input_path=input_path,
                    )
                used.add(label)
    for label, note in notes.items():
        if label not in used:
            raise ParseError(
                "footnote_unused", f"Footnote {label!r} is never referenced.", line=note.line, input_path=input_path
            )
