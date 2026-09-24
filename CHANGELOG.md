# Changelog

## 0.3.7

- Repeat pipe-table header rows automatically across pages through ps-python-docx 1.3.6.
- Leave body rows and unrelated table formatting unchanged.

## 0.3.6

- Convert named Markdown footnotes into native editable Word notes through ps-python-docx 1.3.5.
- Preserve formatted text, multiple paragraphs, and links within notes.
- Validate labels, repeated references, and unsupported note content with source lines.

## 0.3.5

- Generate native Word bookmarks for headings and support internal Markdown links such as `[Details](#details)`.
- Resolve forward references, duplicate heading slugs, Unicode headings, and percent-encoded fragments.
- Preserve existing template bookmark names and report unresolved links with source lines.
- Use ps-python-docx 1.3.4 public bookmark and internal-hyperlink APIs.

## 0.3.4

- Preserve ordered-list starting numbers, including zero, through ps-python-docx 1.3.3 public APIs.
- Give separate and nested Markdown lists independent native Word numbering sequences.
- Support multiple paragraphs within list items. Continuation paragraphs stay unnumbered and align with item text.
- Preserve template list formatting and report invalid numbering styles with source lines.

## 0.3.3

- Embed Markdown image alt text as native Word image descriptions through ps-python-docx 1.3.2 public APIs.
- Preserve optional image titles for standalone, inline, reference, and linked images.
- Convert formatted image labels to plain descriptions. Preserve empty descriptions and separate metadata for each use of an image.
- Remove the image_alt_text_not_embedded warning and update the managed skill and showcase.

## 0.3.2

- Use ps-python-docx 1.3.1 public hyperlink authoring APIs. Remove the remaining production OOXML access.
- Preserve link formatting, tooltips, linked images, and template hyperlink styles.
- Enforce the public API boundary across all production modules.

## 0.3.1

- Use ps-python-docx 1.3.0 public theme APIs. Remove theme-related OOXML access from production code.
- Apply body and heading font overrides to Word's actual theme fonts. Preserve theme inheritance in mapped styles and linked character styles instead of applying literal fonts to individual headings.
- Preserve unspecified theme slots and unrelated theme settings. Keep code in its explicit monospace font. Handle missing themes and diagnose malformed themes and conflicting style roles.
- Add saved-package font cascade tests and layout-engine regression checks that verify PDF fonts before and after changing the theme. Exercise Aptos and Aptos Display with Word and Liberation fonts in visual CI.

## 0.3.0

- Convert Markdown links into native, clickable, editable Word hyperlinks in paragraphs, headings, blockquotes, lists, and table cells.
- Preserve formatted link labels, optional title tooltips, and linked inline images. Support reference links, angle-bracket autolinks, email links, and relative file destinations.
- Preserve template hyperlink styles and supply a theme-aware default when needed. Keep hyperlink OOXML creation isolated until python-docx provides a public authoring API.
- Update syntax discovery, managed skill guidance, documentation, and the showcase. Add hyperlink parsing, rendering, relationship, and CLI regression tests.
- Continue rejecting empty destinations and document-local bookmark links with line-aware diagnostics.

## 0.2.0

- Synchronize existing pristine managed skills to the running CLI version during normal commands.
- Store managed ownership, version, and normalized content hashes in `SKILL.md` front matter. Migrate legacy managed skills and recover invalid version metadata.
- Add read-only skill status and force installation for managed edits. Preserve custom directory support, removal safety, and JSON output.
- Skip automatic synchronization for local source and editable builds. Add atomic replacement, concurrent-change checks, and installed-wheel lifecycle smoke tests.

## 0.1.0

- Add strict Markdown parsing with invisible YAML directives and line-aware diagnostics.
- Add editable Word rendering for text, headings, blockquotes, code, mixed nested lists, tables, images, page breaks, and sections.
- Add blank `.docx` templates, semantic style mapping, font overrides, template inspection, and a packaged default template.
- Add safe local and remote image handling, JSON automation output, overwrite protection, syntax discovery, and managed agent skill commands.
- Add a complete test suite, showcase document, CI, package validation, wheel smoke tests, and trusted PyPI publishing.
