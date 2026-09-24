from __future__ import annotations

import re

from markdown_it.token import Token

from markdown_docx.errors import UnsupportedFeatureError
from markdown_docx.models import InlineFragment

FOOTNOTE_PATTERN = re.compile(r"\[\^[^\]]+\]")
TASK_PATTERN = re.compile(r"^\[[ xX]\]\s")


def _image_alt_text(tokens: list[Token]) -> str:
    """Read image descriptions as plain text, preserving code and nested image labels."""
    parts = []
    for token in tokens:
        if token.type in {"text", "text_special", "code_inline"}:
            parts.append(token.content)
        elif token.type in {"softbreak", "hardbreak"}:
            parts.append("\n")
        elif token.type == "image":
            parts.append(_image_alt_text(token.children or []))
    return "".join(parts)


def parse_inline(token: Token, *, line: int, input_path: str | None) -> list[InlineFragment]:
    fragments: list[InlineFragment] = []
    bold = False
    italic = False
    children = token.children or []
    for index, child in enumerate(children):
        child_type = child.type
        if child_type == "text":
            _reject_footnote_text(child.content, line=line, input_path=input_path)
            _append_text(fragments, child.content, bold=bold, italic=italic)
        elif child_type == "code_inline":
            fragments.append(InlineFragment(kind="text", text=child.content, bold=bold, italic=italic, code=True))
        elif child_type == "softbreak":
            _append_text(fragments, " ", bold=bold, italic=italic)
        elif child_type == "hardbreak":
            fragments.append(InlineFragment(kind="break", bold=bold, italic=italic))
        elif child_type == "strong_open":
            bold = True
        elif child_type == "strong_close":
            bold = False
        elif child_type == "em_open":
            italic = True
        elif child_type == "em_close":
            italic = False
        elif child_type == "image":
            raw_source = child.attrGet("src")
            raw_title = child.attrGet("title")
            fragments.append(
                InlineFragment(
                    kind="image",
                    src=raw_source if isinstance(raw_source, str) else "",
                    alt=_image_alt_text(child.children or []),
                    title=raw_title if isinstance(raw_title, str) else None,
                    bold=bold,
                    italic=italic,
                )
            )
        elif child_type == "link_open":
            if (
                index + 1 < len(children)
                and children[index + 1].content.startswith("^")
                and FOOTNOTE_PATTERN.search(token.content)
            ):
                raise UnsupportedFeatureError(
                    "Footnote syntax is not supported.",
                    line=line,
                    input_path=input_path,
                    code="unsupported_markdown",
                )
            raw_href = child.attrGet("href")
            href = raw_href if isinstance(raw_href, str) else ""
            if not href or href.startswith("#"):
                raise UnsupportedFeatureError(
                    "Links require a non-empty external destination. Document bookmark links are not supported.",
                    line=line,
                    input_path=input_path,
                )
            raw_title = child.attrGet("title")
            title = raw_title if isinstance(raw_title, str) else None
            fragments.append(InlineFragment(kind="link_open", href=href, title=title))
        elif child_type == "link_close":
            fragments.append(InlineFragment(kind="link_close"))
        elif child_type == "html_inline":
            raise UnsupportedFeatureError(
                "Raw inline HTML is not supported.",
                line=line,
                input_path=input_path,
                code="unsupported_markdown",
            )
        else:
            raise UnsupportedFeatureError(
                f"Inline Markdown token '{child_type}' is not supported.",
                line=line,
                input_path=input_path,
                code="unsupported_markdown",
            )
    return fragments


def is_standalone_image(fragments: list[InlineFragment]) -> bool:
    meaningful = [fragment for fragment in fragments if fragment.kind != "text" or (fragment.text or "").strip()]
    return len(meaningful) == 1 and meaningful[0].kind == "image"


def is_task_item(fragments: list[InlineFragment]) -> bool:
    for fragment in fragments:
        if fragment.kind == "text" and fragment.text:
            return TASK_PATTERN.match(fragment.text) is not None
        if fragment.kind != "break":
            return False
    return False


def _reject_footnote_text(text: str, *, line: int, input_path: str | None) -> None:
    if FOOTNOTE_PATTERN.search(text):
        raise UnsupportedFeatureError(
            "Footnote syntax is not supported.",
            line=line,
            input_path=input_path,
            code="unsupported_markdown",
        )


def _append_text(
    fragments: list[InlineFragment],
    text: str,
    *,
    bold: bool,
    italic: bool,
) -> None:
    if not text:
        return
    if (
        fragments
        and fragments[-1].kind == "text"
        and fragments[-1].bold == bold
        and fragments[-1].italic == italic
        and not fragments[-1].code
    ):
        fragments[-1].text = (fragments[-1].text or "") + text
        return
    fragments.append(InlineFragment(kind="text", text=text, bold=bold, italic=italic))
