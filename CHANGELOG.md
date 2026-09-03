# Changelog

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
