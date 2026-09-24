"""Apply Markdown hyperlink styling through public document APIs."""

from __future__ import annotations

from docx.enum.dml import MSO_THEME_COLOR_INDEX
from docx.enum.style import WD_STYLE_TYPE
from docx.styles.styles import Styles
from docx.text.paragraph import Paragraph
from docx.text.run import Run

from markdown_docx.errors import TemplateError


class HyperlinkWriter:
    """Create one native hyperlink with runs formatted through public APIs."""

    def __init__(
        self, paragraph: Paragraph, address: str, title: str | None = None, *, styles: Styles, anchor: str | None = None
    ) -> None:
        if "Hyperlink" not in styles:
            style = styles.add_style("Hyperlink", WD_STYLE_TYPE.CHARACTER)  # type: ignore[no-untyped-call]
            style.font.color.theme_color = MSO_THEME_COLOR_INDEX.HYPERLINK
            style.font.underline = True
        if styles["Hyperlink"].type != WD_STYLE_TYPE.CHARACTER:
            raise TemplateError("template_style_type_mismatch", "Style 'Hyperlink' must be a character style.")
        self.hyperlink = (
            paragraph.add_hyperlink(anchor=anchor, tooltip=title)
            if anchor is not None
            else paragraph.add_hyperlink(address=address, tooltip=title)
        )

    def add_run(self, text: str = "") -> Run:
        return self.hyperlink.add_run(text, style="Hyperlink")
