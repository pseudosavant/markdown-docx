# Public `python-docx` capability matrix

`markdown-docx` 0.1.0 pins `python-docx` 1.2.0. The executable probe is `tests/test_public_api_capabilities.py`.

| Capability | Public API in 1.2.0 | 0.1.0 behavior |
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
| Create native hyperlinks | No | Links are rejected with `unsupported_feature` |
| Set image alt text | No | Source alt text is preserved in Markdown but cannot be embedded |

The public text API documents hyperlink reading but exposes no `add_hyperlink` method. The public drawing API exposes inline shape dimensions and type but no alt-text property. Production code does not use private members or direct XML manipulation to bridge either gap.

Word lists are paragraph numbering, not container objects. The public API can apply a list style to a paragraph, but it cannot attach an unnumbered continuation paragraph to the preceding list item or inspect the numbering definition that owns its indentation. Treating every source paragraph as a new numbered item or flattening paragraphs into line breaks would change the source meaning. Version 0.1.0 therefore rejects multi-paragraph list items instead of approximating them.

References:

- https://python-docx.readthedocs.io/en/latest/api/text.html
- https://python-docx.readthedocs.io/en/latest/api/dml.html
- https://python-docx.readthedocs.io/en/latest/api/document.html
- https://python-docx.readthedocs.io/en/latest/api/table.html
