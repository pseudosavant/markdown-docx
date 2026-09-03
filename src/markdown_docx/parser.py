from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, NoReturn, cast

from markdown_it import MarkdownIt
from markdown_it.token import Token

from markdown_docx.errors import ParseError, UnsupportedFeatureError
from markdown_docx.markdown_body import is_standalone_image, is_task_item, parse_inline
from markdown_docx.metadata import (
    default_document_options,
    parse_document_options,
    parse_image_options,
    parse_section_options,
    parse_table_options,
    parse_yaml_payload,
)
from markdown_docx.models import (
    Alignment,
    Block,
    CodeBlock,
    DocumentModel,
    DocumentOptions,
    HeadingBlock,
    ImageBlock,
    ImageOptions,
    ListKind,
    ListParagraphBlock,
    PageBreakBlock,
    ParagraphBlock,
    SectionBreakBlock,
    TableBlock,
    TableCell,
    TableOptions,
)

COMMENT_PATTERN = re.compile(r"^<!--\s*markdown-docx(?P<body>.*?)-->\s*$", re.DOTALL)


@dataclass(slots=True)
class Directive:
    kind: str
    value: Any
    line: int
    end_line_index: int


def parse_document(
    source: str,
    *,
    input_path: Path | None,
    source_name: str,
) -> DocumentModel:
    markdown = MarkdownIt("commonmark", {"html": True}).enable("table")
    try:
        tokens = markdown.parse(source)
    except Exception as exc:
        raise ParseError(
            "markdown_parse_error",
            f"Markdown parsing failed: {exc}",
            input_path=str(input_path) if input_path else source_name,
        ) from exc

    input_label = str(input_path) if input_path else source_name
    source_lines = source.splitlines()
    options = default_document_options()
    blocks: list[Block] = []
    document_seen = False
    visible_seen = False
    pending: Directive | None = None
    index = 0

    while index < len(tokens):
        token = tokens[index]
        if token.type == "html_block":
            directive = _parse_directive(token, input_path=input_label)
            if directive is None:
                _unsupported("Raw HTML and non-reserved HTML comments are not supported.", token, input_label)
            if pending is not None:
                raise ParseError(
                    "metadata_placement_error",
                    "More than one metadata block cannot attach to the same content block.",
                    line=directive.line,
                    input_path=input_label,
                    metadata_kind=directive.kind,
                )
            if directive.kind == "document":
                if visible_seen or document_seen or blocks:
                    raise ParseError(
                        "metadata_placement_error",
                        "Document metadata must be the first non-whitespace content and may appear only once.",
                        line=directive.line,
                        input_path=input_label,
                        metadata_kind="document",
                    )
                options = parse_document_options(directive.value, line=directive.line, input_path=input_label)
                document_seen = True
            else:
                pending = directive
            index += 1
            continue

        visible_seen = True
        line = _token_line(token)
        table_options: TableOptions | None = None
        image_options: ImageOptions | None = None
        if pending is not None:
            _validate_adjacency(pending, token, source_lines, input_label)
            if pending.kind == "page-break":
                blocks.append(PageBreakBlock(line=pending.line))
            elif pending.kind == "section":
                settings = parse_section_options(
                    pending.value,
                    defaults=options.section,
                    line=pending.line,
                    input_path=input_label,
                )
                blocks.append(SectionBreakBlock(line=pending.line, settings=settings))
            elif pending.kind == "table":
                if token.type != "table_open":
                    _attachment_error("table", pending.line, input_label)
                table_options = parse_table_options(pending.value, line=pending.line, input_path=input_label)
            elif pending.kind == "image":
                if token.type != "paragraph_open":
                    _attachment_error("image", pending.line, input_label)
                image_options = parse_image_options(pending.value, line=pending.line, input_path=input_label)
            else:
                raise AssertionError(f"Unhandled directive: {pending.kind}")
            pending = None

        token_type = token.type
        if token_type == "paragraph_open":
            paragraph, index = _consume_paragraph(tokens, index, input_label)
            if is_standalone_image(paragraph.fragments):
                image = next(fragment for fragment in paragraph.fragments if fragment.kind == "image")
                blocks.append(
                    ImageBlock(
                        line=paragraph.line,
                        src=image.src or "",
                        alt=image.alt or "",
                        options=image_options or ImageOptions(),
                    )
                )
            elif image_options is not None:
                _attachment_error("image", line, input_label)
            else:
                blocks.append(paragraph)
        elif token_type == "heading_open":
            if image_options is not None:
                _attachment_error("image", line, input_label)
            heading, index = _consume_heading(tokens, index, input_label)
            blocks.append(heading)
        elif token_type == "fence":
            blocks.append(CodeBlock(line=line, text=token.content))
            index += 1
        elif token_type == "code_block":
            _unsupported("Indented code blocks are not supported. Use a fenced code block.", token, input_label)
        elif token_type == "blockquote_open":
            quote_blocks, index = _consume_blockquote(tokens, index, input_label)
            blocks.extend(quote_blocks)
        elif token_type in {"bullet_list_open", "ordered_list_open"}:
            list_blocks, index = _consume_list(tokens, index, depth=0, options=options, input_path=input_label)
            blocks.extend(list_blocks)
        elif token_type == "table_open":
            table, index = _consume_table(tokens, index, table_options or TableOptions(), input_label)
            blocks.append(table)
        elif token_type == "hr":
            _unsupported("Horizontal rules are not supported.", token, input_label)
        elif token_type == "html_inline":
            _unsupported("Raw inline HTML is not supported.", token, input_label)
        else:
            _unsupported(f"Markdown token '{token_type}' is not supported.", token, input_label)

    if pending is not None:
        raise ParseError(
            "metadata_placement_error",
            f"{pending.kind} metadata must be followed by a content block.",
            line=pending.line,
            input_path=input_label,
            metadata_kind=pending.kind,
        )
    return DocumentModel(input_path=input_path, source_name=source_name, options=options, blocks=blocks)


def _parse_directive(token: Token, *, input_path: str) -> Directive | None:
    match = COMMENT_PATTERN.fullmatch(token.content)
    if match is None:
        return None
    line = _token_line(token)
    body = match.group("body").strip()
    end_line_index = token.map[1] if token.map else line
    if body.startswith(":"):
        compact = body[1:].strip()
        if compact != "page-break":
            raise ParseError(
                "unknown_metadata_key",
                f"Unknown compact markdown-docx directive: {compact or '<empty>'}",
                line=line,
                input_path=input_path,
            )
        return Directive("page-break", None, line, end_line_index)
    if not body:
        raise ParseError(
            "metadata_parse_error",
            "A markdown-docx metadata comment requires a YAML payload.",
            line=line,
            input_path=input_path,
        )
    payload = parse_yaml_payload(body, line=line, input_path=input_path, metadata_kind="markdown-docx")
    if not isinstance(payload, dict) or len(payload) != 1 or any(not isinstance(key, str) for key in payload):
        raise ParseError(
            "metadata_parse_error",
            "A metadata comment must contain exactly one of document, section, table, or image.",
            line=line,
            input_path=input_path,
        )
    kind, value = next(iter(payload.items()))
    if kind not in {"document", "section", "table", "image"}:
        raise ParseError(
            "unknown_metadata_key",
            f"Unknown metadata directive: {kind}",
            line=line,
            input_path=input_path,
            details={"key": kind},
        )
    return Directive(kind, value, line, end_line_index)


def _validate_adjacency(directive: Directive, token: Token, lines: list[str], input_path: str) -> None:
    if directive.kind not in {"table", "image"} or token.map is None:
        return
    next_start = token.map[0]
    if any(line.strip() for line in lines[directive.end_line_index : next_start]):
        _attachment_error(directive.kind, directive.line, input_path)


def _consume_paragraph(tokens: list[Token], index: int, input_path: str) -> tuple[ParagraphBlock, int]:
    opening = tokens[index]
    if index + 2 >= len(tokens) or tokens[index + 1].type != "inline" or tokens[index + 2].type != "paragraph_close":
        _unsupported("This paragraph structure is not supported.", opening, input_path)
    line = _token_line(opening)
    fragments = parse_inline(tokens[index + 1], line=line, input_path=input_path)
    return ParagraphBlock(line=line, fragments=fragments), index + 3


def _consume_heading(tokens: list[Token], index: int, input_path: str) -> tuple[HeadingBlock, int]:
    opening = tokens[index]
    if not opening.markup or set(opening.markup) != {"#"}:
        _unsupported("Setext headings are not supported. Use ATX headings beginning with #.", opening, input_path)
    if index + 2 >= len(tokens) or tokens[index + 1].type != "inline" or tokens[index + 2].type != "heading_close":
        _unsupported("This heading structure is not supported.", opening, input_path)
    level = int(opening.tag[1:])
    line = _token_line(opening)
    fragments = parse_inline(tokens[index + 1], line=line, input_path=input_path)
    return HeadingBlock(line=line, level=level, fragments=fragments), index + 3


def _consume_blockquote(tokens: list[Token], index: int, input_path: str) -> tuple[list[ParagraphBlock], int]:
    opening = tokens[index]
    blocks: list[ParagraphBlock] = []
    index += 1
    while index < len(tokens) and tokens[index].type != "blockquote_close":
        if tokens[index].type != "paragraph_open":
            _unsupported("Blockquotes may contain paragraphs only in 0.2.0.", tokens[index], input_path)
        paragraph, index = _consume_paragraph(tokens, index, input_path)
        if any(fragment.kind == "image" for fragment in paragraph.fragments):
            _unsupported("Images nested in blockquotes are not supported.", opening, input_path)
        paragraph.role = "blockquote"
        blocks.append(paragraph)
    if index >= len(tokens):
        _structure_error(opening, input_path)
    return blocks, index + 1


def _consume_list(
    tokens: list[Token],
    index: int,
    *,
    depth: int,
    options: DocumentOptions,
    input_path: str,
) -> tuple[list[ListParagraphBlock], int]:
    opening = tokens[index]
    ordered = opening.type == "ordered_list_open"
    kind: ListKind = "ordered" if ordered else "unordered"
    configured_styles = options.styles.ordered_list if ordered else options.styles.unordered_list
    if depth >= len(configured_styles):
        raise ParseError(
            "list_depth_unsupported",
            f"{kind} list depth {depth + 1} exceeds the {len(configured_styles)} configured styles.",
            line=_token_line(opening),
            input_path=input_path,
        )
    if ordered:
        start = opening.attrGet("start")
        if start is not None and int(start) != 1:
            raise ParseError(
                "ordered_list_start_unsupported",
                "Ordered lists must begin with 1 in 0.2.0.",
                line=_token_line(opening),
                input_path=input_path,
            )
    closing_type = "ordered_list_close" if ordered else "bullet_list_close"
    blocks: list[ListParagraphBlock] = []
    index += 1
    while index < len(tokens) and tokens[index].type != closing_type:
        item_open = tokens[index]
        if item_open.type != "list_item_open":
            _structure_error(item_open, input_path)
        index += 1
        paragraph_seen = False
        while index < len(tokens) and tokens[index].type != "list_item_close":
            token = tokens[index]
            if token.type == "paragraph_open":
                if paragraph_seen:
                    _unsupported(
                        "Multi-paragraph list items are not supported by the public list-style API.", token, input_path
                    )
                paragraph, index = _consume_paragraph(tokens, index, input_path)
                if is_task_item(paragraph.fragments):
                    _unsupported("Task list syntax is not supported.", token, input_path)
                if any(fragment.kind == "image" for fragment in paragraph.fragments):
                    _unsupported("Images nested in list items are not supported.", token, input_path)
                blocks.append(
                    ListParagraphBlock(
                        line=paragraph.line,
                        fragments=paragraph.fragments,
                        list_kind=kind,
                        depth=depth,
                    )
                )
                paragraph_seen = True
            elif token.type in {"bullet_list_open", "ordered_list_open"}:
                nested, index = _consume_list(tokens, index, depth=depth + 1, options=options, input_path=input_path)
                blocks.extend(nested)
            else:
                _unsupported("This content type is not supported inside list items.", token, input_path)
        if index >= len(tokens) or not paragraph_seen:
            _structure_error(item_open, input_path)
        index += 1
    if index >= len(tokens):
        _structure_error(opening, input_path)
    return blocks, index + 1


def _consume_table(
    tokens: list[Token],
    index: int,
    options: TableOptions,
    input_path: str,
) -> tuple[TableBlock, int]:
    opening = tokens[index]
    line = _token_line(opening)
    rows: list[list[TableCell]] = []
    current_row: list[TableCell] | None = None
    in_header = False
    header_row_count = 0
    index += 1
    while index < len(tokens) and tokens[index].type != "table_close":
        token = tokens[index]
        if token.type == "thead_open":
            in_header = True
            index += 1
        elif token.type == "thead_close":
            in_header = False
            index += 1
        elif token.type in {"tbody_open", "tbody_close"}:
            index += 1
        elif token.type == "tr_open":
            current_row = []
            index += 1
        elif token.type == "tr_close":
            if current_row is None:
                _structure_error(token, input_path)
            rows.append(current_row)
            if in_header:
                header_row_count += 1
            current_row = None
            index += 1
        elif token.type in {"th_open", "td_open"}:
            if current_row is None or index + 2 >= len(tokens) or tokens[index + 1].type != "inline":
                _structure_error(token, input_path)
            raw_style = token.attrGet("style")
            style = raw_style if isinstance(raw_style, str) else "text-align:left"
            alignment = style.removeprefix("text-align:")
            if alignment not in {"left", "center", "right"}:
                alignment = "left"
            fragments = parse_inline(tokens[index + 1], line=line, input_path=input_path)
            if any(fragment.kind == "image" for fragment in fragments):
                _unsupported("Images inside table cells are not supported.", token, input_path)
            current_row.append(TableCell(fragments=fragments, alignment=cast(Alignment, alignment)))
            expected_close = "th_close" if token.type == "th_open" else "td_close"
            if tokens[index + 2].type != expected_close:
                _structure_error(token, input_path)
            index += 3
        else:
            _structure_error(token, input_path)
    if index >= len(tokens) or not rows or header_row_count != 1:
        raise ParseError(
            "table_shape_invalid",
            "A pipe table requires one header row and at least one row.",
            line=line,
            input_path=input_path,
        )
    column_count = len(rows[0])
    if column_count == 0 or any(len(row) != column_count for row in rows):
        raise ParseError(
            "table_shape_invalid",
            "Every table row must have the same number of cells.",
            line=line,
            input_path=input_path,
        )
    if options.column_widths is not None and len(options.column_widths) != column_count:
        raise ParseError(
            "table_shape_invalid",
            "The number of column_widths entries must match the table column count.",
            line=line,
            input_path=input_path,
            metadata_kind="table",
        )
    return TableBlock(line=line, headers=rows[0], rows=rows[1:], options=options), index + 1


def _token_line(token: Token) -> int:
    return token.map[0] + 1 if token.map else 1


def _attachment_error(kind: str, line: int, input_path: str) -> NoReturn:
    raise ParseError(
        "metadata_placement_error",
        f"{kind} metadata must be immediately before a standalone {kind}.",
        line=line,
        input_path=input_path,
        metadata_kind=kind,
    )


def _unsupported(message: str, token: Token, input_path: str) -> NoReturn:
    raise UnsupportedFeatureError(
        message,
        line=_token_line(token),
        input_path=input_path,
        code="unsupported_markdown",
    )


def _structure_error(token: Token, input_path: str) -> NoReturn:
    raise ParseError(
        "markdown_parse_error",
        "The parsed Markdown structure is not supported.",
        line=_token_line(token),
        input_path=input_path,
    )
