# Public `python-docx` capability matrix

`markdown-docx` pins `ps-python-docx` 1.3.2, which retains the `docx` import package. The executable probe is `tests/test_public_api_capabilities.py`.

| Capability | Public API in fork 1.3.2 | Current behavior |
| --- | --- | --- |
| Open and save blank DOCX templates | Yes | Supported |
| Enumerate and validate styles | Yes | Supported |
| Change paragraph style fonts | Yes | Supported |
| Set document theme fonts and theme inheritance | Yes | Uses `Document.theme_fonts`, `Font.theme_font`, `Styles.default_font`, and `Style.linked_style` |
| Add sections and set page geometry | Yes | Supported |
| Add explicit page breaks | Yes | Supported |
| Apply list paragraph styles | Yes | Supported within configured depth |
| Preserve multiple Word paragraphs as one list item | No | Multi-paragraph list items are rejected |
| Create, align, and size tables | Yes | Supported |
| Add inline pictures with preserved aspect ratio | Yes | Supported |
| Align picture paragraphs | Yes | Supported |
| Create native hyperlinks | Yes | Uses `Paragraph.add_hyperlink`, `Hyperlink.add_run`, and tooltip support |
| Set image alt text and titles | Yes | Uses `InlineShape.description` and `InlineShape.title` for standalone, inline, and linked images |

The fork's public text API creates external hyperlinks with `Paragraph.add_hyperlink` and formatted label runs with `Hyperlink.add_run`. `src/markdown_docx/hyperlinks.py` applies the Hyperlink character style through public APIs. Existing template hyperlink styles are preserved. Optional link titles become tooltips. Empty destinations and document-local bookmark links are rejected with `unsupported_feature`. The library owns hyperlink XML and external relationships.

`tests/test_public_api_boundary.py` forbids private and OOXML access throughout production code, including the hyperlink and theme font adapters. `tests/test_hyperlinks.py` checks saved relationships, text, formatting, titles, supported block contexts, and template styling.

The public theme API implements the requirement that explicit Markdown font overrides appear in Word's actual theme settings. `theme_fonts.py` now contains only Markdown style mapping and diagnostics. It assigns the major and minor Latin typefaces through `Document.theme_fonts`, binds mapped and linked styles through `Font.theme_font`, and sets `Styles.default_font` for body inheritance. The library owns theme creation and XML changes. Font names are never assigned to individual heading runs. Other formatting and script fonts are preserved. Code keeps its explicit monospace font. Malformed themes and conflicting style roles retain their stable template diagnostics.

`tests/test_theme_fonts.py` checks serialized theme definitions, references, effective font resolution, partial overrides, custom mappings, and preservation. `tests/test_font_rendering.py` verifies actual PDF font names after layout and again after a theme change. The default suite runs without Office. CI enables the layout test with LibreOffice and Liberation fonts. The optional Word run uses Aptos and Aptos Display and fails on font substitution.

The public drawing API exposes read/write `InlineShape.description` and `InlineShape.title` properties. Markdown image labels become plain-text descriptions and optional image titles are preserved. Empty alt text stays empty without marking the image as decorative. Metadata belongs to each placed image. The library owns the drawing XML, and production code uses only its public properties.

Word lists are paragraph numbering, not container objects. The public API can apply a list style to a paragraph, but it cannot attach an unnumbered continuation paragraph to the preceding list item or inspect the numbering definition that owns its indentation. Treating every source paragraph as a new numbered item or flattening paragraphs into line breaks would change the source meaning. Version 0.1.0 therefore rejects multi-paragraph list items instead of approximating them.

References:

- https://python-docx.readthedocs.io/en/latest/api/text.html
- https://python-docx.readthedocs.io/en/latest/api/dml.html
- https://python-docx.readthedocs.io/en/latest/api/document.html
- https://python-docx.readthedocs.io/en/latest/api/table.html
