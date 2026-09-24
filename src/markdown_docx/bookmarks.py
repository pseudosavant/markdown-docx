"""Markdown heading slugs and internal-link resolution."""

from __future__ import annotations

import re
import unicodedata
from urllib.parse import unquote

from markdown_docx.errors import ParseError
from markdown_docx.models import Block, HeadingBlock, InlineFragment, ListParagraphBlock, ParagraphBlock, TableBlock


def resolve_heading_links(blocks: list[Block], *, input_path: str) -> None:
    used: set[str] = set()
    for block in blocks:
        if not isinstance(block, HeadingBlock):
            continue
        text = "".join(
            fragment.alt or "" if fragment.kind == "image" else " " if fragment.kind == "break" else fragment.text or ""
            for fragment in block.fragments
        )
        normalized = unicodedata.normalize("NFC", text).lower()
        base = re.sub(r"\s+", "-", re.sub(r"[^\w\s-]", "", normalized).strip()) or "section"
        slug = base
        suffix = 0
        while slug in used:
            suffix += 1
            slug = f"{base}-{suffix}"
        block.anchor = slug
        used.add(slug)
    for block in blocks:
        for fragments in _fragment_groups(block):
            for fragment in fragments:
                if fragment.kind != "link_open" or not (fragment.href or "").startswith("#"):
                    continue
                try:
                    target = unicodedata.normalize("NFC", unquote((fragment.href or "")[1:], errors="strict"))
                except UnicodeDecodeError as exc:
                    raise ParseError(
                        "internal_link_invalid",
                        "Internal link contains invalid UTF-8 encoding.",
                        line=block.line,
                        input_path=input_path,
                    ) from exc
                if target not in used:
                    raise ParseError(
                        "internal_link_unresolved",
                        f"No heading matches internal link {fragment.href!r}.",
                        line=block.line,
                        input_path=input_path,
                    )
                fragment.anchor = target


def _fragment_groups(block: Block) -> list[list[InlineFragment]]:
    if isinstance(block, (HeadingBlock, ParagraphBlock, ListParagraphBlock)):
        return [block.fragments]
    if isinstance(block, TableBlock):
        return [cell.fragments for row in [block.headers, *block.rows] for cell in row]
    return []
