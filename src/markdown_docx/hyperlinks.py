"""Isolate hyperlink authoring until python-docx provides a public creation API."""

from __future__ import annotations

from typing import cast

from docx.enum.dml import MSO_THEME_COLOR_INDEX
from docx.enum.style import WD_STYLE_TYPE
from docx.opc.constants import RELATIONSHIP_TYPE
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.oxml.text.hyperlink import CT_Hyperlink
from docx.parts.document import DocumentPart
from docx.text.paragraph import Paragraph
from docx.text.run import Run

from markdown_docx.errors import TemplateError


class HyperlinkWriter:
    """Create one native hyperlink with runs formatted through public APIs."""

    def __init__(self, paragraph: Paragraph, address: str, title: str | None = None) -> None:
        self.paragraph = paragraph
        styles = cast(DocumentPart, paragraph.part).document.styles
        if "Hyperlink" not in styles:
            style = styles.add_style("Hyperlink", WD_STYLE_TYPE.CHARACTER)
            style.font.color.theme_color = MSO_THEME_COLOR_INDEX.HYPERLINK
            style.font.underline = True
        if styles["Hyperlink"].type != WD_STYLE_TYPE.CHARACTER:
            raise TemplateError("template_style_type_mismatch", "Style 'Hyperlink' must be a character style.")
        self._element = cast(CT_Hyperlink, OxmlElement("w:hyperlink"))
        relationship_id = paragraph.part.relate_to(address, RELATIONSHIP_TYPE.HYPERLINK, is_external=True)
        self._element.set(qn("r:id"), relationship_id)
        self._element.set(qn("w:history"), "1")
        if title is not None:
            self._element.set(qn("w:tooltip"), title)
        paragraph._p.append(self._element)

    def add_run(self, text: str = "") -> Run:
        run = self.paragraph.add_run(text, style="Hyperlink")
        self._element.append(run._r)
        return run
