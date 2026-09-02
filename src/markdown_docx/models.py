from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, TypeAlias

Orientation = Literal["portrait", "landscape"]
Alignment = Literal["left", "center", "right"]
ListKind = Literal["ordered", "unordered"]


@dataclass(slots=True, frozen=True)
class PageSize:
    width: int
    height: int
    name: str | None = None


@dataclass(slots=True, frozen=True)
class Margins:
    top: int
    right: int
    bottom: int
    left: int


@dataclass(slots=True, frozen=True)
class SectionSettings:
    page_size: PageSize
    orientation: Orientation
    margins: Margins

    @property
    def effective_width(self) -> int:
        return self.page_size.height if self.orientation == "landscape" else self.page_size.width

    @property
    def effective_height(self) -> int:
        return self.page_size.width if self.orientation == "landscape" else self.page_size.height

    @property
    def usable_width(self) -> int:
        return self.effective_width - self.margins.left - self.margins.right

    @property
    def usable_height(self) -> int:
        return self.effective_height - self.margins.top - self.margins.bottom


@dataclass(slots=True)
class StyleMappings:
    paragraph: str = "Normal"
    headings: dict[int, str] = field(default_factory=lambda: {level: f"Heading {level}" for level in range(1, 7)})
    blockquote: str = "Quote"
    code_block: str = "Code Block"
    ordered_list: list[str] = field(default_factory=lambda: ["List Number", "List Number 2", "List Number 3"])
    unordered_list: list[str] = field(default_factory=lambda: ["List Bullet", "List Bullet 2", "List Bullet 3"])
    table: str = "Table Grid"


@dataclass(slots=True)
class FontOverrides:
    body: str | None = None
    headings: str | None = None
    monospace: str = "Consolas"


@dataclass(slots=True)
class DocumentOptions:
    section: SectionSettings
    styles: StyleMappings = field(default_factory=StyleMappings)
    fonts: FontOverrides = field(default_factory=FontOverrides)


@dataclass(slots=True, frozen=True)
class TableOptions:
    style: str | None = None
    alignment: Alignment = "left"
    width: Literal["auto", "page"] = "page"
    column_widths: tuple[float, ...] | None = None


@dataclass(slots=True, frozen=True)
class ImageOptions:
    width: int | float | None = None
    width_is_percent: bool = False
    alignment: Alignment = "left"


@dataclass(slots=True)
class InlineFragment:
    kind: Literal["text", "break", "image"]
    text: str | None = None
    src: str | None = None
    alt: str | None = None
    bold: bool = False
    italic: bool = False
    code: bool = False


@dataclass(slots=True)
class ParagraphBlock:
    line: int
    fragments: list[InlineFragment]
    role: Literal["paragraph", "blockquote"] = "paragraph"


@dataclass(slots=True)
class HeadingBlock:
    line: int
    level: int
    fragments: list[InlineFragment]


@dataclass(slots=True)
class CodeBlock:
    line: int
    text: str


@dataclass(slots=True)
class ListParagraphBlock:
    line: int
    fragments: list[InlineFragment]
    list_kind: ListKind
    depth: int


@dataclass(slots=True)
class TableCell:
    fragments: list[InlineFragment]
    alignment: Alignment


@dataclass(slots=True)
class TableBlock:
    line: int
    headers: list[TableCell]
    rows: list[list[TableCell]]
    options: TableOptions


@dataclass(slots=True)
class ImageBlock:
    line: int
    src: str
    alt: str
    options: ImageOptions


@dataclass(slots=True)
class PageBreakBlock:
    line: int


@dataclass(slots=True)
class SectionBreakBlock:
    line: int
    settings: SectionSettings


Block: TypeAlias = (
    ParagraphBlock
    | HeadingBlock
    | CodeBlock
    | ListParagraphBlock
    | TableBlock
    | ImageBlock
    | PageBreakBlock
    | SectionBreakBlock
)


@dataclass(slots=True)
class DocumentModel:
    input_path: Path | None
    source_name: str
    options: DocumentOptions
    blocks: list[Block]
    warnings: list[str] = field(default_factory=list)
