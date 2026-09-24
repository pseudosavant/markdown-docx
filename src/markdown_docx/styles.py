from __future__ import annotations

from docx.document import Document as DocumentObject
from docx.enum.style import WD_STYLE_TYPE

from markdown_docx.errors import TemplateError
from markdown_docx.models import DocumentOptions
from markdown_docx.theme_fonts import apply_theme_fonts


def validate_styles(document: DocumentObject, options: DocumentOptions) -> None:
    paragraph_names = {
        options.styles.paragraph,
        options.styles.blockquote,
        options.styles.code_block,
        *options.styles.headings.values(),
        *options.styles.ordered_list,
        *options.styles.unordered_list,
    }
    for name in sorted(paragraph_names):
        _require_style(document, name, WD_STYLE_TYPE.PARAGRAPH)
    _require_style(document, options.styles.table, WD_STYLE_TYPE.TABLE)


def apply_font_overrides(document: DocumentObject, options: DocumentOptions) -> None:
    document.styles[options.styles.code_block].font.name = options.fonts.monospace
    apply_theme_fonts(document, options)


def _require_style(document: DocumentObject, name: str, expected_type: WD_STYLE_TYPE) -> None:
    try:
        style = document.styles[name]
    except KeyError as exc:
        raise TemplateError("template_style_missing", f"Template is missing required style: {name}") from exc
    if style.type != expected_type:
        raise TemplateError(
            "template_style_type_mismatch",
            f"Style '{name}' must be a {expected_type.name.lower()} style.",
        )
