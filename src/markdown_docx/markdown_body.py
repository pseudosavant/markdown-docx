from __future__ import annotations

import re

from markdown_it.token import Token

from markdown_docx.errors import UnsupportedFeatureError
from markdown_docx.models import InlineFragment

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
    strike = False
    superscript = False
    subscript = False
    children = token.children or []
    in_link = False
    reference_line = line
    for child in children:
        child_type = child.type
        if child_type == "text":
            _append_text(
                fragments,
                child.content,
                bold=bold,
                italic=italic,
                strike=strike,
                superscript=superscript,
                subscript=subscript,
            )
        elif child_type == "code_inline":
            fragments.append(
                InlineFragment(
                    kind="text",
                    text=child.content,
                    bold=bold,
                    italic=italic,
                    strike=strike,
                    superscript=superscript,
                    subscript=subscript,
                    code=True,
                )
            )
        elif child_type == "softbreak":
            reference_line += 1
            _append_text(
                fragments, " ", bold=bold, italic=italic, strike=strike, superscript=superscript, subscript=subscript
            )
        elif child_type == "hardbreak":
            reference_line += 1
            fragments.append(InlineFragment(kind="break", bold=bold, italic=italic))
        elif child_type == "strong_open":
            bold = True
        elif child_type == "strong_close":
            bold = False
        elif child_type == "em_open":
            italic = True
        elif child_type == "em_close":
            italic = False
        elif child_type == "s_open":
            strike = True
        elif child_type == "s_close":
            strike = False
        elif child_type == "sup_open":
            superscript = True
        elif child_type == "sup_close":
            superscript = False
        elif child_type == "sub_open":
            subscript = True
        elif child_type == "sub_close":
            subscript = False
        elif child_type == "image":
            if _contains_note(child):
                raise UnsupportedFeatureError(
                    "Footnote references in image labels are unsupported.",
                    code="footnote_reference_unsupported",
                    line=reference_line,
                    input_path=input_path,
                )
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
                    strike=strike,
                    superscript=superscript,
                    subscript=subscript,
                )
            )
        elif child_type == "link_open":
            in_link = True
            raw_href = child.attrGet("href")
            href = raw_href if isinstance(raw_href, str) else ""
            if not href:
                raise UnsupportedFeatureError(
                    "Links require a non-empty destination.",
                    line=line,
                    input_path=input_path,
                )
            raw_title = child.attrGet("title")
            title = raw_title if isinstance(raw_title, str) else None
            fragments.append(InlineFragment(kind="link_open", href=href, title=title))
        elif child_type == "link_close":
            in_link = False
            fragments.append(InlineFragment(kind="link_close"))
        elif child_type == "footnote_ref":
            if in_link:
                raise UnsupportedFeatureError(
                    "Footnote references inside link labels are unsupported.",
                    code="footnote_reference_unsupported",
                    line=reference_line,
                    input_path=input_path,
                )
            fragments.append(
                InlineFragment(kind="footnote", footnote_label=child.meta["label"], reference_line=reference_line)
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


def consume_task_marker(fragments: list[InlineFragment]) -> bool | None:
    """Remove a leading task marker and return its checked state, if present."""
    for fragment in fragments:
        if fragment.kind == "text" and fragment.text:
            match = TASK_PATTERN.match(fragment.text)
            if match is None:
                return None
            checked = fragment.text[1].lower() == "x"
            fragment.text = fragment.text[match.end() :]
            if not fragment.text:
                fragments.remove(fragment)
            return checked
        if fragment.kind != "break":
            return None
    return None


def _contains_note(token: Token) -> bool:
    return token.type == "footnote_ref" or any(_contains_note(child) for child in token.children or [])


def _append_text(
    fragments: list[InlineFragment],
    text: str,
    *,
    bold: bool,
    italic: bool,
    strike: bool,
    superscript: bool,
    subscript: bool,
) -> None:
    if not text:
        return
    if (
        fragments
        and fragments[-1].kind == "text"
        and fragments[-1].bold == bold
        and fragments[-1].italic == italic
        and fragments[-1].strike == strike
        and fragments[-1].superscript == superscript
        and fragments[-1].subscript == subscript
        and not fragments[-1].code
    ):
        fragments[-1].text = (fragments[-1].text or "") + text
        return
    fragments.append(
        InlineFragment(
            kind="text",
            text=text,
            bold=bold,
            italic=italic,
            strike=strike,
            superscript=superscript,
            subscript=subscript,
        )
    )
