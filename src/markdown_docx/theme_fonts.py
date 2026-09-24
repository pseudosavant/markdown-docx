"""Map Markdown font roles using public python-docx theme and style APIs."""

from __future__ import annotations

from typing import Literal

from docx.document import Document as DocumentObject
from docx.enum.style import WD_STYLE_TYPE
from docx.styles.style import CharacterStyle

from markdown_docx.errors import TemplateError
from markdown_docx.models import DocumentOptions


def apply_theme_fonts(document: DocumentObject, options: DocumentOptions) -> None:
    """Set Latin theme fonts and references without formatting individual runs.

    Preserve the template's East Asian, complex script, and supplemental fonts.
    Monospace remains an explicit font because Word has no monospace theme slot.
    """
    code_style = document.styles[options.styles.code_block]
    code_style.font.theme_font = None

    if not (options.fonts.body or options.fonts.headings):
        return

    assignments: dict[str, tuple[CharacterStyle, Literal["major", "minor"]]] = {}

    def assign(style: CharacterStyle, role: Literal["major", "minor"]) -> None:
        style_id = style.style_id
        if style_id is None:
            raise TemplateError("template_style_invalid", "Font styles must have a style ID.")
        if style_id == code_style.style_id or (style_id in assignments and assignments[style_id][1] != role):
            raise TemplateError(
                "template_font_style_conflict",
                "Body, heading, and code font roles must use distinct styles.",
                details={"style_id": style_id},
            )
        assignments[style_id] = (style, role)

    body_names = {
        options.styles.paragraph,
        options.styles.blockquote,
        *options.styles.ordered_list,
        *options.styles.unordered_list,
    }
    if options.fonts.body:
        default_style = document.styles.default(WD_STYLE_TYPE.PARAGRAPH)
        if default_style is not None:
            body_names.add(default_style.name)
    roles: tuple[tuple[set[str], str | None, Literal["major", "minor"]], ...] = (
        (body_names, options.fonts.body, "minor"),
        (set(options.styles.headings.values()), options.fonts.headings, "major"),
    )
    for names, font, role in roles:
        if not font:
            continue
        for name in sorted(names):
            style = document.styles[name]
            assign(style, role)
            linked = style.linked_style
            if linked is not None and linked.type == WD_STYLE_TYPE.CHARACTER:
                assign(linked, role)

    try:
        fonts = document.theme_fonts
        if options.fonts.body:
            fonts.minor_latin = options.fonts.body
        if options.fonts.headings:
            fonts.major_latin = options.fonts.headings
        fonts.name = "markdown-docx"
    except ValueError as exc:
        raise TemplateError("template_theme_invalid", f"Cannot update template theme fonts: {exc}") from exc

    for style, role in assignments.values():
        style.font.theme_font = role
    if options.fonts.body:
        document.styles.default_font.theme_font = "minor"
