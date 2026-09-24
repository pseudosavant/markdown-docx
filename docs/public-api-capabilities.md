# Public `python-docx` capability matrix

`markdown-docx` pins `ps-python-docx` 1.3.4, which retains the `docx` import package. The executable probe is `tests/test_public_api_capabilities.py`.

| Capability | Public API in fork 1.3.4 | Current behavior |
| --- | --- | --- |
| Open and save blank DOCX templates | Yes | Supported |
| Enumerate and validate styles | Yes | Supported |
| Change paragraph style fonts | Yes | Supported |
| Set document theme fonts and theme inheritance | Yes | Uses `Document.theme_fonts`, `Font.theme_font`, `Styles.default_font`, and `Style.linked_style` |
| Add sections and set page geometry | Yes | Supported |
| Add explicit page breaks | Yes | Supported |
| Apply list paragraph styles | Yes | Supported within configured depth |
| Preserve multiple Word paragraphs as one list item | Yes | Uses `ListInstance.apply_continuation` |
| Control independent lists, starts, and restarts | Yes | Uses `Document.add_list` and `ListInstance.apply` |
| Create, align, and size tables | Yes | Supported |
| Add inline pictures with preserved aspect ratio | Yes | Supported |
| Align picture paragraphs | Yes | Supported |
| Create and find bookmarks | Yes | Uses `Document.bookmarks` |
| Create native hyperlinks | Yes | Uses `Paragraph.add_hyperlink`, `Hyperlink.add_run`, and tooltip support |
| Set image alt text and titles | Yes | Uses `InlineShape.description` and `InlineShape.title` for standalone, inline, and linked images |

The fork's public text API creates external hyperlinks with `Paragraph.add_hyperlink` and formatted label runs with `Hyperlink.add_run`. `src/markdown_docx/hyperlinks.py` applies the Hyperlink character style through public APIs. Existing template hyperlink styles are preserved. Optional link titles become tooltips. Empty destinations are rejected with `unsupported_feature`. Internal links use `Paragraph.add_hyperlink(anchor=...)` and heading targets use `Document.bookmarks.add`. The converter owns heading slugs and unresolved-target diagnostics. The library owns hyperlink XML and external relationships.

`tests/test_public_api_boundary.py` forbids private and OOXML access throughout production code, including the hyperlink and theme font adapters. `tests/test_hyperlinks.py` checks saved relationships, text, formatting, titles, supported block contexts, and template styling.

The public theme API implements the requirement that explicit Markdown font overrides appear in Word's actual theme settings. `theme_fonts.py` now contains only Markdown style mapping and diagnostics. It assigns the major and minor Latin typefaces through `Document.theme_fonts`, binds mapped and linked styles through `Font.theme_font`, and sets `Styles.default_font` for body inheritance. The library owns theme creation and XML changes. Font names are never assigned to individual heading runs. Other formatting and script fonts are preserved. Code keeps its explicit monospace font. Malformed themes and conflicting style roles retain their stable template diagnostics.

`tests/test_theme_fonts.py` checks serialized theme definitions, references, effective font resolution, partial overrides, custom mappings, and preservation. `tests/test_font_rendering.py` verifies actual PDF font names after layout and again after a theme change. The default suite runs without Office. CI enables the layout test with LibreOffice and Liberation fonts. The optional Word run uses Aptos and Aptos Display and fails on font substitution.

The public drawing API exposes read/write `InlineShape.description` and `InlineShape.title` properties. Markdown image labels become plain-text descriptions and optional image titles are preserved. Empty alt text stays empty without marking the image as decorative. Metadata belongs to each placed image. The library owns the drawing XML, and production code uses only its public properties.

Word represents lists with paragraph numbering. `Document.add_list` creates an independent sequence using template numbering. The converter keeps one handle per Markdown list and uses its first marker as the starting number. `ListInstance.apply_continuation` makes a separate Word paragraph unnumbered and preserves its text alignment. The fork copies numbering definitions for each sequence because Word can otherwise share counters across interleaved lists. Original template definitions are preserved. Markdown list identity, item boundaries, and nesting remain in converter models. No custom source directives are required.

References:

- https://python-docx.readthedocs.io/en/latest/api/text.html
- https://python-docx.readthedocs.io/en/latest/api/dml.html
- https://python-docx.readthedocs.io/en/latest/api/document.html
- https://python-docx.readthedocs.io/en/latest/api/table.html
