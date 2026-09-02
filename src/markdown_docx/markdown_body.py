from __future__ import annotations

import re

from markdown_it.token import Token

from markdown_docx.errors import UnsupportedFeatureError
from markdown_docx.models import InlineFragment

FOOTNOTE_PATTERN = re.compile(r"\[\^[^\]]+\]")
TASK_PATTERN = re.compile(r"^\[[ xX]\]\s")


def parse_inline(token: Token, *, line: int, input_path: str | None) -> list[InlineFragment]:
    fragments: list[InlineFragment] = []
    bold = False
    italic = False
    children = token.children or []
    if FOOTNOTE_PATTERN.search(token.content) and any(child.type == "link_open" for child in children):
        raise UnsupportedFeatureError(
            "Footnote syntax is not supported.",
            line=line,
            input_path=input_path,
            code="unsupported_markdown",
        )
    for child in children:
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
            fragments.append(
                InlineFragment(
                    kind="image",
                    src=raw_source if isinstance(raw_source, str) else "",
                    alt=child.content,
                    bold=bold,
                    italic=italic,
                )
            )
        elif child_type in {"link_open", "link_close"}:
            raise UnsupportedFeatureError(
                "Links require a public python-docx hyperlink creation API and are not supported in 0.1.0.",
                line=line,
                input_path=input_path,
            )
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
