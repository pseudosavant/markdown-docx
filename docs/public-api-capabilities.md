# Public `python-docx` capability matrix

`markdown-docx` pins `python-docx` 1.2.0. The executable probe is `tests/test_public_api_capabilities.py`.

| Capability | Public API in 1.2.0 | Current behavior |
| --- | --- | --- |
| Open and save blank DOCX templates | Yes | Supported |
| Enumerate and validate styles | Yes | Supported |
| Change paragraph style fonts | Yes | Supported |
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

`tests/test_public_api_boundary.py` confines private and OOXML access to that helper. `tests/test_hyperlinks.py` checks saved relationships, text, formatting, titles, supported block contexts, and template styling. The dependency pin and these checks bound the compatibility risk of using library internals.

The public drawing API exposes inline shape dimensions and type but no alt-text property. The hyperlink exception does not authorize direct XML changes for image alt text or other features.

Word lists are paragraph numbering, not container objects. The public API can apply a list style to a paragraph, but it cannot attach an unnumbered continuation paragraph to the preceding list item or inspect the numbering definition that owns its indentation. Treating every source paragraph as a new numbered item or flattening paragraphs into line breaks would change the source meaning. Version 0.1.0 therefore rejects multi-paragraph list items instead of approximating them.

References:

- https://python-docx.readthedocs.io/en/latest/api/text.html
- https://python-docx.readthedocs.io/en/latest/api/dml.html
- https://python-docx.readthedocs.io/en/latest/api/document.html
- https://python-docx.readthedocs.io/en/latest/api/table.html
