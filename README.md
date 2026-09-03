# markdown-docx

`markdown-docx` turns constrained Markdown into predictable, editable Word `.docx` files. The Markdown stays readable in normal renderers. Word-specific layout and style settings live in invisible HTML comments.

The format is strict by design. Unsupported input produces a stable, line-aware error instead of an approximate document.

## Prerequisite

The documented workflow uses [`uv`](https://docs.astral.sh/uv/getting-started/installation/). Install `uv` before continuing.

## Quick start with an agent

Install the managed agent skill:

```powershell
uvx markdown-docx skill install
```

Then ask an agent to create both the Markdown source and the editable Word output:

> Use $markdown-docx to create a project brief. Keep the source readable as normal Markdown and save the editable DOCX beside it.

The skill teaches the agent how to inspect the format, inspect blank Word templates, render safely, and handle structured results.

## Manage the agent skill

The standard location is `~/.agents/skills/markdown-docx/SKILL.md`. Normally installed CLI builds automatically synchronize an already-installed managed skill during ordinary commands, including help and version output. The running CLI version is the authority. A pristine older skill is replaced with the bundled skill. Equal and newer versions are left alone. Missing and unmanaged skills are never installed or overwritten automatically.

Synchronization is local. It does not query a package index, refresh uv's cache, or update the CLI. The skill continues to instruct agents to use `uvx markdown-docx`. Updates affect future skill loading. Instructions already loaded by a running agent may stay unchanged until the agent reloads them.

Inspect the skill without changing it:

```powershell
uvx markdown-docx skill status
uvx markdown-docx skill status --json
```

Status reports the selected path, ownership, CLI and skill versions, version ordering, integrity, and automatic synchronization eligibility. Modified or unverifiable skills with valid version metadata are preserved. To replace a managed skill intentionally:

```powershell
uvx markdown-docx skill install --force
```

Install `--force` still refuses unmanaged content and never downgrades a newer skill. A normal install creates a missing skill, updates a pristine older skill, or leaves a current skill alone. Legacy managed skills and managed skills with missing or invalid version metadata receive a fresh replacement. This recovery does not require a valid hash.

Custom directories require explicit updates. Automatic synchronization only checks the standard directory. Local source and editable development builds skip automatic synchronization, but explicit installation still works:

```powershell
uvx markdown-docx skill install --skills-dir PATH
uvx markdown-docx skill status --skills-dir PATH
uvx --from . markdown-docx skill install
```

Remove the skill with `uvx markdown-docx skill remove`. Removal refuses unmanaged content and extra files unless `--force` is supplied. All skill commands accept `--skills-dir` and `--json`. Skill commands never trigger automatic synchronization. Maintenance notices go to stderr and leave JSON stdout intact.

See [skill lifecycle metadata and decisions](docs/skill-management.md) for the hash format and recovery rules.

## Use the CLI directly

```powershell
uvx markdown-docx document.md document.docx
```

When the output path is omitted, the tool writes a `.docx` beside the input Markdown file.

```powershell
uvx markdown-docx document.md
```

Inspect the supported syntax:

```powershell
uvx markdown-docx --syntax
uvx markdown-docx --syntax --json
```

## Supported Markdown

Version 0.2.0 supports:

- ATX headings from `#` through `######`
- Paragraphs and standard soft or hard line breaks
- Emphasis, strong emphasis, and inline backtick code
- Fenced code blocks
- Blockquotes containing paragraphs
- Ordered and unordered lists, including mixed nesting
- Pipe tables with inline text formatting
- Local and remote inline images
- Standalone images with width and alignment metadata

Links are rejected in 0.2.0. `python-docx` 1.2.0 can read hyperlinks but has no supported public API for creating them. The source alt text for images remains meaningful Markdown content, but the same library release has no public API for embedding it in a Word drawing. A rendered document containing images reports `image_alt_text_not_embedded` in its warning list.

The following syntax is intentionally unsupported:

- Raw HTML and non-reserved HTML comments
- Setext headings and horizontal rules
- Indented code blocks
- Task lists and footnotes
- Multi-paragraph list items
- Tables, images, code blocks, or blockquotes nested inside list items
- Images inside table cells or blockquotes
- Arbitrary Markdown extensions

## Invisible Word metadata

Only HTML comments beginning with `markdown-docx` are accepted. All other HTML is an error.

Document metadata may appear once. It must be the first non-whitespace content:

```markdown
<!-- markdown-docx
document:
  page_size: letter
  orientation: portrait
  margins:
    top: 1in
    right: 1in
    bottom: 1in
    left: 1in
  styles:
    paragraph: Normal
    headings:
      1: Heading 1
      2: Heading 2
      3: Heading 3
      4: Heading 4
      5: Heading 5
      6: Heading 6
    blockquote: Quote
    code_block: Code Block
    ordered_list:
      - List Number
      - List Number 2
      - List Number 3
    unordered_list:
      - List Bullet
      - List Bullet 2
      - List Bullet 3
    table: Table Grid
  fonts:
    body: Calibri
    headings: Calibri
    monospace: Consolas
-->

# Project brief

This remains ordinary Markdown.
```

Metadata uses strict YAML. Duplicate keys, unknown keys, invalid types, unitless lengths, and misplaced comments are errors.

### Page sizes and margins

Named page sizes are `letter`, `legal`, and `a4`. Custom page sizes use nominal portrait dimensions. The width must not exceed the height.

```markdown
<!-- markdown-docx
document:
  page_size:
    width: 7in
    height: 10in
  orientation: portrait
  margins:
    top: 0.75in
    right: 0.75in
    bottom: 0.75in
    left: 0.75in
-->
```

Lengths accept `in`, `cm`, `mm`, and `pt`. Margins must leave a positive usable page area.

### Sections

A section directive starts a next-page Word section before the following content block:

```markdown
<!-- markdown-docx
section:
  page_size: letter
  orientation: landscape
  margins:
    top: 0.75in
    right: 0.75in
    bottom: 0.75in
    left: 0.75in
-->

## Landscape analysis
```

Each section starts from the document defaults and applies its own overrides. It does not inherit omitted values from the preceding section. Reset to the document defaults with:

```markdown
<!-- markdown-docx
section: default
-->
```

Headings never create sections.

### Page breaks

Insert a page break before the next content block:

```markdown
<!-- markdown-docx: page-break -->

## Appendix
```

A page break does not create a new section.

## Templates and styles

A custom template must be a blank `.docx` formatting template. `.dotx` is not supported. The template may define styles, theme data, fonts, numbering definitions, and section defaults. It must not contain:

- Non-whitespace body text
- Body tables
- Body images or drawings
- Nonempty headers or footers

Inspect a template before writing Markdown that refers to its style names:

```powershell
uvx markdown-docx --inspect-template --template formatting.docx
uvx markdown-docx --list-styles --template formatting.docx
uvx markdown-docx --list-table-styles --template formatting.docx
```

Render with the template:

```powershell
uvx markdown-docx report.md report.docx --template formatting.docx
```

The template remains unchanged. When no template is supplied, the packaged blank template provides every default style.

The Markdown metadata maps semantic constructs to paragraph and table style names. Each configured style must exist and must have the correct Word style type. Body and heading font overrides modify the mapped paragraph styles. The monospace override applies to code blocks and inline code. Sizes, colors, spacing, borders, and other typography remain owned by the template.

## Lists

Apply one Word paragraph style per list type and nesting depth:

```yaml
styles:
  ordered_list:
    - List Number
    - List Number 2
    - List Number 3
  unordered_list:
    - List Bullet
    - List Bullet 2
    - List Bullet 3
```

Mixed nested lists select ordered or unordered styles independently at every depth. A list deeper than the configured style array is an error. Ordered lists must begin with `1`. Restart controls and arbitrary start values are not supported.

## Tables

Standard pipe tables become editable Word tables. Put optional table metadata immediately before the table:

```markdown
<!-- markdown-docx
table:
  style: Table Grid
  alignment: center
  width: page
  column_widths: [3, 1, 1]
-->

| Item | Count | Price |
| --- | ---: | ---: |
| Widget | 2 | $10 |
```

The first Markdown row is the semantic header row. Cell alignment follows the Markdown delimiter row. `column_widths` contains positive ratios and must match the column count. `width: page` uses the active section's usable width. `width: auto` lets Word size the table unless ratios are supplied.

Merged cells, nested tables, fixed row heights, repeated-header controls, and per-cell border or fill metadata are not supported.

## Images

Relative paths resolve from the Markdown file's directory:

```markdown
Text before ![Status icon](images/status.png) text after.
```

Put metadata immediately before a standalone image:

```markdown
<!-- markdown-docx
image:
  width: 40%
  alignment: center
-->
![Architecture](images/architecture.png)
```

Widths accept `in`, `cm`, `mm`, `pt`, or a percentage of the active section's usable width. Images preserve aspect ratio. Natural-size images are clamped to the usable width. An explicit physical width that exceeds the usable width is an error.

HTTP and HTTPS images use timeouts, a 25 MiB download limit, content-type validation, a 50 megapixel decode limit, and one download per unique URL. Reject remote images for offline builds or untrusted input:

```powershell
uvx markdown-docx report.md --no-remote-images
```

## Automation and safety

Use `--json` for one complete machine-readable result:

```powershell
uvx markdown-docx report.md report.docx --json
```

A successful result contains the input path, output path, template identifier, section count, and warnings. It does not report a page count. DOCX files do not have a reliable intrinsic page count until a compatible layout engine paginates them.

The CLI refuses to overwrite an existing output. Add `--force` only when replacement is intended:

```powershell
uvx markdown-docx report.md report.docx --force --json
```

For stdin, provide both an output path and a base directory:

```powershell
Get-Content report.md | uvx markdown-docx --input - --output report.docx --base-dir .
```

Exit codes:

| Code | Meaning |
| ---: | --- |
| `0` | Success |
| `2` | Usage or input error |
| `3` | Markdown or metadata parse error |
| `4` | Template or style error |
| `5` | Image or asset error |
| `6` | Unsupported Markdown or feature |
| `7` | DOCX rendering error |
| `8` | Unexpected internal error |

## Complete example

See [the showcase Markdown](sample/showcase.md). It opens with an illustrated three-dog story, then exercises supported text, list, table, image, page-break, and section behavior in a dedicated capability lab. Regenerate it from a repository checkout:

```powershell
uvx --refresh --from . markdown-docx sample\showcase.md sample\showcase.docx --force
```

## Public API boundary

Production code uses only documented public `python-docx` APIs. It does not write OOXML directly and does not call private library members. Tests may inspect generated package XML read-only. The complete capability decision record is in [docs/public-api-capabilities.md](docs/public-api-capabilities.md).

Word is the primary compatibility target. LibreOffice Writer is used as a visual smoke-test engine. Differences in pagination or font metrics can occur between layout engines.

## Development

```powershell
$env:UV_LINK_MODE="copy"
uv sync --locked --all-groups
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy
```

Build and validate distributions:

```powershell
uv build
uv run twine check dist/*
```
