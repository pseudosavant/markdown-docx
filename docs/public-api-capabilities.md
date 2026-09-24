# Public `python-docx` capability matrix

`markdown-docx` pins `ps-python-docx` 1.3.0, which retains the `docx` import package. The executable probe is `tests/test_public_api_capabilities.py`.

| Capability | Public API in fork 1.3.0 | Current behavior |
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
| Create native hyperlinks | No | Supported through the isolated `hyperlinks.py` OOXML helper |
| Set image alt text | No | Source alt text is preserved in Markdown but cannot be embedded |

The public text API documents hyperlink reading but exposes no `add_hyperlink` method. The authorized exception in `AGENTS.md` permits `src/markdown_docx/hyperlinks.py` to create hyperlink elements and move runs into them. It registers external URL relationships and uses public APIs for run formatting and the Hyperlink character style. Existing template hyperlink styles are preserved. Optional link titles become tooltips. Empty destinations and document-local bookmark links are rejected with `unsupported_feature`. This helper is temporary and should be replaced when a supported upstream creation API becomes available.

`tests/test_public_api_boundary.py` confines private and OOXML access to the hyperlink helper, including checking the theme font adapter. `tests/test_hyperlinks.py` checks saved relationships, text, formatting, titles, supported block contexts, and template styling. The dependency pin and these checks bound the compatibility risk of using library internals.

The public theme API implements the requirement that explicit Markdown font overrides appear in Word's actual theme settings. `theme_fonts.py` now contains only Markdown style mapping and diagnostics. It assigns the major and minor Latin typefaces through `Document.theme_fonts`, binds mapped and linked styles through `Font.theme_font`, and sets `Styles.default_font` for body inheritance. The library owns theme creation and XML changes. Font names are never assigned to individual heading runs. Other formatting and script fonts are preserved. Code keeps its explicit monospace font. Malformed themes and conflicting style roles retain their stable template diagnostics.

`tests/test_theme_fonts.py` checks serialized theme definitions, references, effective font resolution, partial overrides, custom mappings, and preservation. `tests/test_font_rendering.py` verifies actual PDF font names after layout and again after a theme change. The default suite runs without Office. CI enables the layout test with LibreOffice and Liberation fonts. The optional Word run uses Aptos and Aptos Display and fails on font substitution.

The public drawing API exposes inline shape dimensions and type but no alt-text property. The hyperlink exception does not authorize direct XML changes for image alt text or other features.

Word lists are paragraph numbering, not container objects. The public API can apply a list style to a paragraph, but it cannot attach an unnumbered continuation paragraph to the preceding list item or inspect the numbering definition that owns its indentation. Treating every source paragraph as a new numbered item or flattening paragraphs into line breaks would change the source meaning. Version 0.1.0 therefore rejects multi-paragraph list items instead of approximating them.

References:

- https://python-docx.readthedocs.io/en/latest/api/text.html
- https://python-docx.readthedocs.io/en/latest/api/dml.html
- https://python-docx.readthedocs.io/en/latest/api/document.html
- https://python-docx.readthedocs.io/en/latest/api/table.html
