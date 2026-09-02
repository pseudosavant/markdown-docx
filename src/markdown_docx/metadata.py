from __future__ import annotations

import re
from dataclasses import replace
from typing import Any, NoReturn, cast

import yaml

from markdown_docx.errors import ParseError
from markdown_docx.models import (
    Alignment,
    DocumentOptions,
    FontOverrides,
    ImageOptions,
    Margins,
    Orientation,
    PageSize,
    SectionSettings,
    StyleMappings,
    TableOptions,
)

EMU_PER_INCH = 914400
EMU_PER_CM = 360000
EMU_PER_MM = 36000
EMU_PER_PT = 12700

PAGE_SIZES = {
    "letter": PageSize(int(8.5 * EMU_PER_INCH), 11 * EMU_PER_INCH, "letter"),
    "legal": PageSize(int(8.5 * EMU_PER_INCH), 14 * EMU_PER_INCH, "legal"),
    "a4": PageSize(210 * EMU_PER_MM, 297 * EMU_PER_MM, "a4"),
}

LENGTH_PATTERN = re.compile(r"^(?P<value>(?:\d+(?:\.\d*)?|\.\d+))(?P<unit>in|cm|mm|pt)$", re.IGNORECASE)


class UniqueKeyLoader(yaml.SafeLoader):
    pass


def _construct_mapping(loader: UniqueKeyLoader, node: yaml.MappingNode, deep: bool = False) -> dict[Any, Any]:
    mapping: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise yaml.constructor.ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                f"found duplicate key {key!r}",
                key_node.start_mark,
            )
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


UniqueKeyLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_mapping)


def default_document_options() -> DocumentOptions:
    one_inch = EMU_PER_INCH
    return DocumentOptions(
        section=SectionSettings(
            page_size=PAGE_SIZES["letter"],
            orientation="portrait",
            margins=Margins(one_inch, one_inch, one_inch, one_inch),
        )
    )


def parse_yaml_payload(text: str, *, line: int, input_path: str | None, metadata_kind: str) -> Any:
    try:
        return yaml.load(text, Loader=UniqueKeyLoader)
    except yaml.YAMLError as exc:
        problem_line = line
        problem_mark = getattr(exc, "problem_mark", None)
        if problem_mark is not None:
            problem_line += int(problem_mark.line) + 1
        raise ParseError(
            "metadata_parse_error",
            f"Invalid {metadata_kind} metadata: {exc}",
            line=problem_line,
            input_path=input_path,
            metadata_kind=metadata_kind,
        ) from exc


def parse_document_options(value: Any, *, line: int, input_path: str | None) -> DocumentOptions:
    mapping = _mapping(value, "document", line, input_path)
    _known_keys(mapping, {"page_size", "orientation", "margins", "styles", "fonts"}, "document", line, input_path)
    options = default_document_options()
    section = _parse_section_fields(mapping, options.section, "document", line, input_path)
    styles = _parse_styles(mapping.get("styles"), options.styles, line, input_path)
    fonts = _parse_fonts(mapping.get("fonts"), options.fonts, line, input_path)
    return DocumentOptions(section=section, styles=styles, fonts=fonts)


def parse_section_options(
    value: Any,
    *,
    defaults: SectionSettings,
    line: int,
    input_path: str | None,
) -> SectionSettings:
    if value == "default":
        return defaults
    mapping = _mapping(value, "section", line, input_path)
    _known_keys(mapping, {"page_size", "orientation", "margins"}, "section", line, input_path)
    return _parse_section_fields(mapping, defaults, "section", line, input_path)


def parse_table_options(value: Any, *, line: int, input_path: str | None) -> TableOptions:
    mapping = _mapping(value, "table", line, input_path)
    _known_keys(mapping, {"style", "alignment", "width", "column_widths"}, "table", line, input_path)
    style = mapping.get("style")
    if style is not None:
        style = _nonempty_string(style, "style", "table", line, input_path)
    alignment = cast(
        Alignment,
        _choice(mapping.get("alignment", "left"), {"left", "center", "right"}, "alignment", "table", line, input_path),
    )
    width = _choice(mapping.get("width", "page"), {"auto", "page"}, "width", "table", line, input_path)
    ratios_value = mapping.get("column_widths")
    ratios: tuple[float, ...] | None = None
    if ratios_value is not None:
        if not isinstance(ratios_value, list) or not ratios_value:
            _invalid("column_widths must be a nonempty list", "table", line, input_path)
        converted: list[float] = []
        for ratio in ratios_value:
            if isinstance(ratio, bool) or not isinstance(ratio, (int, float)) or ratio <= 0:
                _invalid("column_widths entries must be positive numbers", "table", line, input_path)
            converted.append(float(ratio))
        ratios = tuple(converted)
    return TableOptions(style=style, alignment=alignment, width=width, column_widths=ratios)  # type: ignore[arg-type]


def parse_image_options(value: Any, *, line: int, input_path: str | None) -> ImageOptions:
    mapping = _mapping(value, "image", line, input_path)
    _known_keys(mapping, {"width", "alignment"}, "image", line, input_path)
    alignment = cast(
        Alignment,
        _choice(mapping.get("alignment", "left"), {"left", "center", "right"}, "alignment", "image", line, input_path),
    )
    width_value = mapping.get("width")
    width: int | float | None = None
    is_percent = False
    if width_value is not None:
        if isinstance(width_value, str) and width_value.endswith("%"):
            try:
                percentage = float(width_value[:-1])
            except ValueError:
                _invalid("width percentage is invalid", "image", line, input_path)
            if percentage <= 0 or percentage > 100:
                _invalid("width percentage must be greater than 0 and at most 100", "image", line, input_path)
            width = percentage
            is_percent = True
        else:
            width = parse_length(width_value, field="width", kind="image", line=line, input_path=input_path)
    return ImageOptions(width=width, width_is_percent=is_percent, alignment=alignment)


def parse_length(value: Any, *, field: str, kind: str, line: int, input_path: str | None) -> int:
    if not isinstance(value, str):
        _invalid(f"{field} must include a unit", kind, line, input_path)
    match = LENGTH_PATTERN.fullmatch(value.strip())
    if match is None:
        _invalid(f"{field} must use in, cm, mm, or pt", kind, line, input_path)
    amount = float(match.group("value"))
    if amount <= 0:
        _invalid(f"{field} must be greater than zero", kind, line, input_path)
    factors = {"in": EMU_PER_INCH, "cm": EMU_PER_CM, "mm": EMU_PER_MM, "pt": EMU_PER_PT}
    return round(amount * factors[match.group("unit").lower()])


def _parse_section_fields(
    mapping: dict[str, Any],
    defaults: SectionSettings,
    kind: str,
    line: int,
    input_path: str | None,
) -> SectionSettings:
    page_size = defaults.page_size
    if "page_size" in mapping:
        page_size = _parse_page_size(mapping["page_size"], kind, line, input_path)
    orientation = defaults.orientation
    if "orientation" in mapping:
        orientation = cast(
            Orientation,
            _choice(mapping["orientation"], {"portrait", "landscape"}, "orientation", kind, line, input_path),
        )
    margins = defaults.margins
    if "margins" in mapping:
        margin_values = _mapping(mapping["margins"], kind, line, input_path)
        _known_keys(margin_values, {"top", "right", "bottom", "left"}, kind, line, input_path)
        margins = replace(
            margins,
            **{
                key: parse_length(value, field=f"margins.{key}", kind=kind, line=line, input_path=input_path)
                for key, value in margin_values.items()
            },
        )
    settings = SectionSettings(page_size=page_size, orientation=orientation, margins=margins)
    if settings.usable_width <= 0 or settings.usable_height <= 0:
        raise ParseError(
            "invalid_page_geometry",
            "Margins must leave a positive usable page width and height.",
            line=line,
            input_path=input_path,
            metadata_kind=kind,
        )
    return settings


def _parse_page_size(value: Any, kind: str, line: int, input_path: str | None) -> PageSize:
    if isinstance(value, str):
        key = value.lower()
        if key not in PAGE_SIZES:
            _invalid("page_size must be letter, legal, a4, or a custom width and height", kind, line, input_path)
        return PAGE_SIZES[key]
    mapping = _mapping(value, kind, line, input_path)
    _known_keys(mapping, {"width", "height"}, kind, line, input_path)
    if set(mapping) != {"width", "height"}:
        _invalid("custom page_size requires width and height", kind, line, input_path)
    width = parse_length(mapping["width"], field="page_size.width", kind=kind, line=line, input_path=input_path)
    height = parse_length(mapping["height"], field="page_size.height", kind=kind, line=line, input_path=input_path)
    if width > height:
        _invalid("custom page_size width must not exceed height", kind, line, input_path)
    return PageSize(width, height)


def _parse_styles(
    value: Any,
    defaults: StyleMappings,
    line: int,
    input_path: str | None,
) -> StyleMappings:
    if value is None:
        return defaults
    mapping = _mapping(value, "document", line, input_path)
    _known_keys(
        mapping,
        {"paragraph", "headings", "blockquote", "code_block", "ordered_list", "unordered_list", "table"},
        "document",
        line,
        input_path,
    )
    result = StyleMappings(
        paragraph=defaults.paragraph,
        headings=dict(defaults.headings),
        blockquote=defaults.blockquote,
        code_block=defaults.code_block,
        ordered_list=list(defaults.ordered_list),
        unordered_list=list(defaults.unordered_list),
        table=defaults.table,
    )
    for key in ("paragraph", "blockquote", "code_block", "table"):
        if key in mapping:
            setattr(result, key, _nonempty_string(mapping[key], key, "document", line, input_path))
    if "headings" in mapping:
        headings_value = mapping["headings"]
        if not isinstance(headings_value, dict):
            _invalid("headings must be a mapping", "document", line, input_path)
        headings = headings_value
        normalized: dict[int, str] = {}
        for raw_level, style_name in headings.items():
            try:
                level = int(raw_level)
            except (TypeError, ValueError):
                _invalid("heading style keys must be levels 1 through 6", "document", line, input_path)
            if isinstance(raw_level, bool) or level not in range(1, 7):
                _invalid("heading style keys must be levels 1 through 6", "document", line, input_path)
            normalized[level] = _nonempty_string(style_name, f"headings.{level}", "document", line, input_path)
        result.headings.update(normalized)
    for key in ("ordered_list", "unordered_list"):
        if key in mapping:
            values = mapping[key]
            if not isinstance(values, list) or not values:
                _invalid(f"{key} must be a nonempty list of style names", "document", line, input_path)
            setattr(
                result,
                key,
                [_nonempty_string(item, key, "document", line, input_path) for item in values],
            )
    return result


def _parse_fonts(value: Any, defaults: FontOverrides, line: int, input_path: str | None) -> FontOverrides:
    if value is None:
        return defaults
    mapping = _mapping(value, "document", line, input_path)
    _known_keys(mapping, {"body", "headings", "monospace"}, "document", line, input_path)
    result = replace(defaults)
    for key in ("body", "headings", "monospace"):
        if key in mapping:
            setattr(result, key, _nonempty_string(mapping[key], f"fonts.{key}", "document", line, input_path))
    return result


def _mapping(value: Any, kind: str, line: int, input_path: str | None) -> dict[str, Any]:
    if not isinstance(value, dict) or any(not isinstance(key, str) for key in value):
        _invalid(f"{kind} metadata must be a mapping with string keys", kind, line, input_path)
    return value


def _known_keys(
    mapping: dict[str, Any],
    allowed: set[str],
    kind: str,
    line: int,
    input_path: str | None,
) -> None:
    unknown = sorted(set(mapping) - allowed)
    if unknown:
        raise ParseError(
            "unknown_metadata_key",
            f"Unknown {kind} metadata key: {unknown[0]}",
            line=line,
            input_path=input_path,
            metadata_kind=kind,
            details={"key": unknown[0]},
        )


def _choice(
    value: Any,
    choices: set[str],
    field: str,
    kind: str,
    line: int,
    input_path: str | None,
) -> str:
    if not isinstance(value, str) or value not in choices:
        _invalid(f"{field} must be one of: {', '.join(sorted(choices))}", kind, line, input_path)
    return value


def _nonempty_string(value: Any, field: str, kind: str, line: int, input_path: str | None) -> str:
    if not isinstance(value, str) or not value.strip():
        _invalid(f"{field} must be a nonempty string", kind, line, input_path)
    return value


def _invalid(message: str, kind: str, line: int, input_path: str | None) -> NoReturn:
    raise ParseError(
        "metadata_parse_error",
        message,
        line=line,
        input_path=input_path,
        metadata_kind=kind,
    )
