# markdown-docx 1.0.0 Plan

## Purpose

`markdown-docx` will convert a constrained Markdown document into a predictable, editable Word `.docx` file.

The Markdown must remain readable and render normally in standard Markdown renderers. Word-specific instructions will live in reserved HTML comments, which normal renderers do not display.

Version 1.0.0 will use only supported public `python-docx` APIs when creating or modifying documents. It will not edit OOXML parts directly. If a feature needs private APIs or direct XML manipulation, it belongs in a later release after the needed capability is added upstream to `python-docx`.

## Product principles

- Keep the format strict, small, and predictable.
- Optimize for documents authored by people and coding agents.
- Preserve ordinary Markdown meaning whenever possible.
- Treat Word sections as the layout boundary. Do not treat Markdown headings as boundaries.
- Make page breaks explicit when the author needs one.
- Let templates and Word styles own most typography and formatting.
- Fail clearly when the requested result cannot be produced through the supported public API.
- Do not silently approximate unsupported Word behavior.
- Produce editable Word content, not a collection of positioned shapes.
- Do not claim a stable page count without running a Word-compatible layout engine.

## Project identity

Recommended initial identity:

- Published package: `markdown-docx`
- CLI command: `markdown-docx`
- Python import package: `markdown_docx`
- Source layout: `src/markdown_docx`

## Version 1.0.0 scope

### Included

- Markdown headings, paragraphs, blockquotes, fenced code blocks, and basic inline formatting
- Ordered and unordered lists, including mixed nested lists
- Pipe tables with a deliberately small formatting surface
- Inline images with optional width and paragraph alignment
- Document and section page geometry
- Explicit page breaks
- Explicit next-page section breaks
- Blank `.docx` formatting templates
- Semantic Markdown-to-Word style mappings
- Optional document-level body, heading, and monospace font overrides
- Strict validation with line-aware errors
- Human-readable and JSON CLI output
- A packaged default blank template
- A machine-readable syntax description

### Excluded

- `.dotx` templates
- Direct OOXML manipulation
- Private `python-docx` APIs
- Floating images and text wrapping
- Image cropping, filters, contrast changes, and other image manipulation
- Page number fields
- Headers and footers authored from Markdown
- Theme palette editing
- Character-style selection
- Ordered-list restart controls and arbitrary starting numbers
- Watermarks and page backgrounds
- Calculated fields, tables of contents, citations, bookmarks, and cross-references
- Footnotes and endnotes
- Tracked changes, comments, forms, and document protection
- Arbitrary raw HTML
- Floating tables and text boxes

## Authoring format

### Ordinary Markdown

The supported Markdown subset should look normal without `markdown-docx`:

- ATX headings from `#` through `######`
- Paragraphs
- Emphasis and strong emphasis
- Inline backtick code
- Links, if the pinned `python-docx` release provides a supported public creation API
- Fenced code blocks
- Blockquotes
- Ordered and unordered lists
- Nested lists
- Pipe tables
- Local and remote images
- Soft and hard line breaks

Unsupported Markdown extensions must produce a clear diagnostic. They must not be silently dropped.

### Invisible metadata

Reserve HTML comments beginning with `markdown-docx`. All other HTML is unsupported in 1.0.0.

Document metadata appears once, before the first visible block:

```md
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
    body: Aptos
    headings: Aptos Display
    monospace: Consolas
-->
```

The metadata payload is YAML. The parser must reject duplicate keys, unknown keys, invalid types, invalid values, and misplaced document metadata.

Metadata comments are invisible in normal HTML rendering. The raw Markdown file remains the authoritative input because some Markdown processors strip comments.

### Metadata attachment rules

- A document block must be the first non-whitespace content in the file.
- A section block applies to content that follows it.
- A page-break directive inserts a break before the next content block.
- Table metadata must be immediately before a table, with only whitespace between them.
- Image metadata must be immediately before a standalone image, with only whitespace between them.
- Metadata cannot be attached across another visible block.
- Unknown directives are errors.
- More than one metadata block attached to the same object is an error.
- Diagnostics must identify the input path, line, metadata kind, and invalid key or value.

## Page geometry and sections

### Page sizes

Version 1.0.0 supports these named sizes:

| Name | Portrait width | Portrait height |
| --- | ---: | ---: |
| `letter` | 8.5 in | 11 in |
| `legal` | 8.5 in | 14 in |
| `a4` | 210 mm | 297 mm |

It also supports custom sizes:

```md
<!-- markdown-docx
section:
  page_size:
    width: 7in
    height: 10in
  orientation: portrait
-->
```

Rules:

- Custom dimensions are supplied as nominal portrait dimensions.
- Custom width must be less than or equal to custom height.
- `orientation: landscape` swaps the effective width and height.
- Accepted length units are `in`, `cm`, `mm`, and `pt`.
- Unitless lengths are invalid.
- Margins must leave a positive usable width and height.

### Document defaults

Document metadata establishes defaults for every section:

```md
<!-- markdown-docx
document:
  page_size: a4
  orientation: portrait
  margins:
    top: 20mm
    right: 20mm
    bottom: 20mm
    left: 20mm
-->
```

### Section breaks

A section directive starts a next-page Word section:

```md
<!-- markdown-docx
section:
  orientation: landscape
  page_size: letter
  margins:
    top: 0.75in
    right: 0.75in
    bottom: 0.75in
    left: 0.75in
-->
```

Each new section starts from the document defaults, then applies the section overrides. It does not inherit omitted properties from the preceding source section. This avoids accidental layout carryover.

A shorthand resets to document defaults:

```md
<!-- markdown-docx
section: default
-->
```

Continuous, odd-page, and even-page section breaks are outside the 1.0.0 scope.

### Page breaks

Use a compact directive:

```md
<!-- markdown-docx: page-break -->
```

The directive creates an explicit page break before the next content block. It does not create a new section.

### Pagination controls

The author-facing pagination surface in 1.0.0 consists only of page breaks and section breaks. Template paragraph styles may contain Word pagination behavior such as keep-with-next and widow control. The Markdown format will not expose those settings individually.

Page numbers are not part of the 1.0.0 schema. They should be added only after `python-docx` has a supported public field API that can create `PAGE` and `NUMPAGES` fields.

## Templates and styles

### Template contract

Version 1.0.0 accepts a `.docx` formatting template. It does not accept `.dotx`.

The renderer opens the template directly with `python-docx` and adds generated content to it. This preserves the package parts that Word and `python-docx` already retain, including styles, theme data, fonts, numbering definitions, and document defaults.

The template must be blank and formatting-only. Validate it before rendering. Reject templates containing any of the following:

- Non-whitespace body text
- Body tables
- Body images or drawings
- Nonempty headers or footers

The expected empty initial body paragraph is allowed and may be reused for the first generated block when practical.

Strict rejection is the 1.0.0 answer to the earlier goal of ignoring template content. Public `python-docx` APIs do not provide a general document-body clearing operation. Silently leaving content in place would produce the wrong document. Arbitrary content removal can be reconsidered after upstream support exists.

When no template is supplied, use a packaged blank `.docx` template with all styles required by the default mappings.

### Template inspection

Provide discovery commands so authors and agents can use exact Word style names:

```powershell
markdown-docx --template template.docx --list-styles
markdown-docx --template template.docx --list-table-styles
markdown-docx --template template.docx --inspect-template
```

`--inspect-template` should report whether the template satisfies the blank-template contract, its available styles grouped by type, its section defaults, and actionable validation errors.

### Semantic style mapping

Map Markdown constructs to named Word styles. Validate every configured style before rendering. Validate that each style has the required Word style type.

Document-level mappings:

- Paragraph
- Heading levels 1 through 6
- Blockquote
- Code block
- Ordered list style by nesting depth
- Unordered list style by nesting depth
- Table style

There is no Markdown metadata for selecting arbitrary character styles in 1.0.0.

### Font behavior

The template styles are the primary source of typeface, size, color, spacing, indentation, borders, shading, and pagination behavior.

Optional document font overrides may set concrete typefaces for:

- Body styles
- Heading styles
- Monospace text

Body and heading overrides update the mapped paragraph styles through public `python-docx` APIs. They do not introduce character styles. Inline backtick code receives a direct monospace run font override while inheriting surrounding size, color, emphasis, and paragraph formatting.

Do not expose document-wide font size or font color overrides in 1.0.0. Those values should come from the mapped template styles. Theme colors and theme font declarations are preserved from the template but cannot be edited through the Markdown schema in 1.0.0.

## Content mapping

### Paragraphs and headings

- A Markdown paragraph becomes one Word paragraph using the configured paragraph style.
- H1 through H6 become Word paragraphs using the corresponding configured heading style.
- Headings do not create sections or page breaks.
- A blockquote becomes one or more paragraphs using the configured blockquote style.
- A fenced code block becomes one or more paragraphs using the configured code-block style.
- Preserve line breaks inside code blocks.

### Inline formatting

- Markdown emphasis becomes italic runs.
- Markdown strong emphasis becomes bold runs.
- Nested strong and emphasis combine predictably.
- Inline backtick code becomes a run using the configured monospace font.
- Hard line breaks become Word line breaks.
- Soft line breaks follow standard Markdown paragraph behavior.
- Links become native Word hyperlinks only if the pinned `python-docx` version has a supported public creation API. Otherwise Phase 0 must define a strict temporary behavior before implementation proceeds.
- Raw inline HTML is unsupported.

Do not add metadata for underline, highlight, arbitrary font size, arbitrary inline color, superscript, or subscript in 1.0.0.

## Lists

Ordered and unordered lists are required for 1.0.0.

Use template-provided paragraph styles for each list type and nesting depth. A mixed nested list chooses the appropriate ordered or unordered style independently at every depth.

Example mapping:

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

Rules:

- The configured style arrays define the supported maximum depth.
- A list nested deeper than its configured style array is an error.
- Ordered lists must begin with `1` in 1.0.0.
- Source marker numbers after the first item are ignored according to normal Markdown parsing.
- There is no restart, continue-numbering, or arbitrary-start metadata.
- Word and the template own marker glyphs, numbering formats, indentation, and continuation behavior.
- Multi-paragraph list items and nested lists should be supported.
- Tables, blockquotes, code blocks, and images nested inside list items may be deferred if the parser or public API behavior is not reliable. If deferred, reject them clearly.

The Phase 0 capability spike must verify that applying the chosen built-in or custom list paragraph styles produces real Word list paragraphs with the expected numbering definitions. If public style application is insufficient for reliable custom templates, document that limitation and constrain the template contract instead of editing numbering XML.

## Tables

Standard Markdown pipe tables become Word tables.

Optional metadata appears immediately before the table:

```md
<!-- markdown-docx
table:
  style: Corporate Table
  alignment: center
  width: page
  column_widths: [3, 1, 1]
-->

| Item | Count | Price |
| --- | ---: | ---: |
| Widget | 2 | $10 |
```

Supported table settings:

- Named Word table style
- Table alignment of `left`, `center`, or `right`
- `width: auto` or `width: page`
- Relative column widths
- Markdown left, center, and right cell alignment
- Inline Markdown formatting inside cells
- Cell vertical alignment if a clear need emerges during implementation

Defaults:

- Use the document-level mapped table style.
- Use `width: page` unless the capability spike shows that `auto` is more stable across Word and LibreOffice.
- Divide available width evenly when column widths are not provided.
- Interpret `column_widths` as ratios, not physical units.
- Calculate available width from the active section page size and margins.

Validation:

- Every row must have the same number of cells after Markdown parsing.
- The number of column-width entries must match the table column count.
- All width ratios must be positive.
- If a table cannot fit the usable width, report a clear error or warning with a suggestion to use a landscape section.

Not supported in 1.0.0:

- Merged cells
- Nested tables
- Per-cell borders or background colors
- Fixed row heights
- Floating tables
- Repeated header rows
- Row split controls
- Direct banding controls

The first Markdown row is a semantic header row. Word may repeat it only if the selected template or a future supported API provides that behavior.

## Images

Images are inline in 1.0.0. Text wrapping around images requires a floating drawing anchor and is deferred until it is supported by a public `python-docx` API.

An ordinary Markdown image is inserted inline at its source location:

```md
Text before ![Diagram](images/diagram.png) text after.
```

A standalone image can have metadata:

```md
<!-- markdown-docx
image:
  width: 40%
  alignment: right
-->
![Architecture](images/architecture.png)
```

Supported settings:

- Width
- Paragraph alignment of `left`, `center`, or `right` for standalone images

Width accepts `in`, `cm`, `mm`, `pt`, or a percentage of the active section's usable width. Set only the width in `python-docx` so the original aspect ratio is preserved.

Defaults:

- Use the image's natural size when it fits.
- Clamp oversized images to the active section's usable width.
- Leave inline images inline when no image metadata is present.
- Use left paragraph alignment for standalone images unless metadata specifies otherwise.

Input handling:

- Resolve relative local paths from the Markdown file's directory.
- Support absolute local paths.
- Support `http` and `https` images with timeouts, download-size limits, and content-type validation.
- Provide `--no-remote-images` for deterministic or offline use.
- Cache each remote image once during a render.

The Markdown alt text remains meaningful source content. Embed it into the Word drawing only if the pinned `python-docx` release exposes a supported public API. Do not use private XML to set it.

## CLI contract

Proposed usage:

```powershell
markdown-docx input.md output.docx
markdown-docx input.md --template template.docx
markdown-docx input.md --json
markdown-docx --syntax
markdown-docx --template template.docx --inspect-template
```

Initial options:

- Positional input path
- Optional positional output path
- `--template PATH`
- `--force`
- `--json`
- `--syntax`
- `--list-styles`
- `--list-table-styles`
- `--inspect-template`
- `--no-remote-images`
- `--base-dir PATH` for stdin and controlled asset resolution
- `--version`
- `--about`

Use stdout for requested output and machine-readable status. Use stderr for diagnostics in plain mode. JSON mode must emit one complete JSON object and no additional prose.

A successful JSON response should include:

- Success state
- Input path
- Output path
- Template path or packaged-default identifier
- Generated section count
- Warning list

Do not report a page count. A `.docx` file does not have a reliable intrinsic page count until a layout engine paginates it.

## Validation and errors

Use stable error codes in addition to readable messages. Suggested groups:

- `markdown_parse_error`
- `metadata_parse_error`
- `metadata_placement_error`
- `unknown_metadata_key`
- `unsupported_markdown`
- `unsupported_feature`
- `template_not_found`
- `template_not_blank`
- `template_style_missing`
- `template_style_type_mismatch`
- `invalid_page_geometry`
- `list_depth_unsupported`
- `ordered_list_start_unsupported`
- `table_shape_invalid`
- `image_not_found`
- `image_download_failed`
- `output_exists`
- `render_failed`

Every source-related error should include the file and line when available. Never silently fall back to a different style, page size, list depth, or image behavior.

## Proposed repository structure

```text
markdown-docx/
  pyproject.toml
  README.md
  LICENSE
  AGENTS.md
  PLAN.md
  src/
    markdown_docx/
      __init__.py
      cli.py
      errors.py
      models.py
      parser.py
      markdown_body.py
      metadata.py
      template.py
      styles.py
      images.py
      renderer.py
      assets/
        default.docx
        syntax.json
  tests/
    test_cli.py
    test_parser.py
    test_metadata.py
    test_template.py
    test_renderer_text.py
    test_renderer_lists.py
    test_renderer_tables.py
    test_renderer_images.py
    test_renderer_sections.py
  sample/
    showcase.md
    showcase.docx
    assets/
```

Use `markdown-it-py` or another CommonMark-oriented parser that preserves token locations and HTML comments. Keep the internal document model independent of `python-docx` objects so parsing and validation can be tested without rendering.

## Implementation plan

### Phase 0: Public API capability spike

Pin a candidate `python-docx` version and prove each required behavior in small tests before building the full renderer.

- Open and save a blank `.docx` while preserving styles, theme data, and numbering definitions.
- Enumerate paragraph, character, and table styles through public APIs.
- Validate style types.
- Modify mapped paragraph-style fonts through public APIs.
- Create sections and set page size, orientation, and margins.
- Insert explicit page breaks.
- Produce ordered and unordered list paragraphs by applying template styles.
- Verify nested and mixed lists in Word and LibreOffice.
- Create and size tables through public APIs.
- Add inline images to paragraphs and preserve aspect ratio when only width is supplied.
- Align standalone image paragraphs.
- Determine whether native hyperlink creation is publicly supported in the pinned version.
- Determine whether image alt text can be set through a public API.
- Record every supported and unsupported operation in a capability matrix under `docs/` or in the README.

Exit criterion: every 1.0.0 rendering feature has a proven public API path. Any failed item must be narrowed, deferred, or proposed upstream before full implementation begins.

### Phase 1: Project foundation

- Create the `src` package layout.
- Configure packaging, console entry point, linting, type checking, and pytest.
- Define typed models and structured diagnostics.
- Add CLI skeleton, version output, JSON mode, overwrite protection, and exit codes.
- Add a minimal `AGENTS.md` that records the strict-format and public-API-only rules.

### Phase 2: Parsing and metadata

- Parse the Markdown into a location-aware token stream.
- Extract and validate reserved `markdown-docx` comments.
- Enforce attachment and placement rules.
- Parse document defaults, sections, page breaks, table metadata, and image metadata.
- Reject unsupported raw HTML and extensions.
- Publish the same metadata schema through `--syntax`.

### Phase 3: Template and style system

- Package a blank default template.
- Load explicit `.docx` templates.
- Implement blank-template validation.
- Enumerate styles and validate mappings and types.
- Implement style inspection commands.
- Apply optional body, heading, and monospace font overrides.
- Verify that saving retains template styles, theme parts, and numbering parts.

### Phase 4: Core text rendering

- Render headings, paragraphs, blockquotes, code blocks, and line breaks.
- Render emphasis, strong emphasis, inline code, and supported hyperlinks.
- Preserve Unicode and escape behavior.
- Add XML-level and public-API round-trip assertions.

### Phase 5: Lists

- Render unordered, ordered, nested, and mixed lists.
- Support multi-paragraph list items where public style behavior remains reliable.
- Enforce maximum configured depth.
- Reject non-1 ordered-list starts.
- Test custom templates and the packaged default template.

### Phase 6: Sections and page breaks

- Apply document page defaults.
- Create next-page sections from document defaults plus overrides.
- Implement the reset shorthand.
- Implement explicit page breaks.
- Validate custom sizes and usable page area.
- Test portrait to landscape to portrait transitions.

### Phase 7: Tables

- Render pipe tables.
- Apply named table styles and table alignment.
- Calculate usable width per section.
- Apply even or relative column widths.
- Render inline formatting and cell alignment.
- Add strict structural validation.

### Phase 8: Images

- Render images inside text runs.
- Render standalone image paragraphs.
- Apply width and alignment metadata.
- Clamp images to usable section width.
- Add local and remote asset handling with safety limits.
- Handle unsupported formats and corrupt files with clear diagnostics.

### Phase 9: Documentation and examples

- Write the README as the normative user guide.
- Generate `syntax.json` from, or validate it against, the parser schema.
- Create a showcase document covering every supported construct in isolation.
- Add template creation guidance for Word users.
- Document limitations without implying that unsupported behavior is approximated.
- Document agent-friendly examples and common failure recovery.

### Phase 10: Release hardening

- Run the full test suite on supported Python versions.
- Build and inspect wheel and source distributions.
- Install the built wheel into a clean environment.
- Render the showcase with the packaged template and at least two custom templates.
- Open outputs in current Microsoft Word and LibreOffice Writer.
- Confirm round-trip editability.
- Confirm that templates remain unchanged on disk.
- Confirm that no implementation code writes private OOXML or calls private `python-docx` members.
- Tag 1.0.0 only after every acceptance criterion below passes.

## Testing strategy

### Parser and schema tests

- Valid and invalid document metadata
- Duplicate and unknown keys
- Metadata placement and adjacency
- Line-number accuracy
- Page and section directives
- Custom units and dimensions
- Table and image metadata
- Unsupported Markdown and raw HTML

### Renderer tests

- Paragraph and table style assignments
- Run-level bold, italic, and monospace behavior
- Section geometry and orientation
- Explicit page-break elements
- Ordered, unordered, nested, and mixed lists
- Table dimensions, alignment, and cell alignment
- Inline and standalone images
- Template preservation
- Reopening every output with `python-docx`

Implementation code must use public APIs only. Tests may inspect the generated ZIP package and OOXML read-only. This is useful for precise assertions and does not weaken the authoring boundary.

### Visual smoke tests

Semantic and XML tests do not prove layout quality. Maintain a small visual smoke suite:

- Render the showcase through LibreOffice in CI when practical.
- Review representative outputs in Microsoft Word before release.
- Check page transitions, list indentation, table width, image sizing, and style fidelity.
- Treat Word as the primary compatibility target. Treat LibreOffice differences as documented compatibility findings rather than automatic Word regressions.

## 1.0.0 acceptance criteria

- A normal Markdown renderer displays the authored content without visible Word metadata.
- The packaged default template can render every supported construct.
- A valid blank custom `.docx` template preserves its styles, fonts, theme, and numbering definitions.
- Every Markdown block receives a documented semantic Word style.
- Ordered, unordered, nested, and mixed lists render as real Word lists within the declared limits.
- Sections reliably change page size, orientation, and margins.
- Page breaks do not create sections.
- Tables fit the active section's usable width and honor supported metadata.
- Images preserve aspect ratio and never exceed usable width by default.
- Unsupported requests fail with stable, line-aware diagnostics.
- The CLI supports safe overwrite behavior and clean JSON output.
- The output reopens successfully with `python-docx`, Microsoft Word, and LibreOffice Writer.
- No production path uses private `python-docx` members or direct OOXML edits.
- README, `--help`, `--syntax`, tests, and showcase examples agree on the format contract.

## Post-1.0.0 roadmap

Post-1.0.0 features should follow upstream `python-docx` support. Prefer contributing a general public API upstream, waiting for a released version, then consuming that API here.

### DOTX templates

First upstream goal:

- Add supported `.dotx` loading and `.docx` output behavior to `python-docx`.
- Preserve styles, themes, numbering, document defaults, relationships, and other template parts.
- Ensure the saved package has the correct document content type and extension semantics.
- Define clear behavior for template body content.

After the capability ships in a stable `python-docx` release, `markdown-docx` can accept `.dotx` alongside blank `.docx` templates.

### Numbering API

Potential upstream capabilities:

- Create numbering instances through public APIs.
- Bind paragraphs to list definitions without private XML.
- Restart numbering.
- Set an ordered-list start value.
- Control numbering independently across lists and sections.
- Improve reliable custom list-style inspection and binding.

Afterward, this project may add explicit restart and start-value metadata. It should not add a `continue_numbering` feature unless a real authoring need emerges.

### Floating images and wrapping

Potential upstream capabilities:

- Create floating drawing anchors.
- Select square, tight, top-and-bottom, and other wrap modes.
- Position an image relative to page, margin, column, paragraph, or character.
- Set distance from surrounding text.
- Set accessible alt text through a public API if it remains unavailable.

Afterward, this project may add left and right wrapped images. Centered images can remain inline unless a floating use case is demonstrated.

### Fields and page numbers

Potential upstream capabilities:

- Create and update Word fields through public APIs.
- Add `PAGE` and `NUMPAGES` fields to headers and footers.
- Control first-page and odd-even header or footer linkage.

Afterward, this project may add document-level and section-level page-number presets:

- No page numbers
- `Page X`
- `Page X of Y`

Keep this preset-based. Do not turn Markdown into a general header and footer layout language.

### Theme editing

Potential upstream capabilities:

- Read and write all theme color slots.
- Read and write major and minor theme fonts.
- Preserve transforms and relationships correctly.

Afterward, this project may add document metadata for theme palette and theme font overrides. Concrete style mappings should remain the main typography mechanism.

### Richer tables

Potential upstream capabilities:

- Repeat a header row.
- Control whether rows split across pages.
- Control table look and banding flags.
- Expose cell margins and borders through public APIs.

Only add the subset that improves predictable Markdown table representation. Do not expose every Word table property.

### Template content removal

If `python-docx` gains a supported way to clear document body content while retaining formatting parts, reconsider allowing nonblank formatting templates and ignoring their body content. Until then, strict blank-template validation is safer and more predictable.

### Continuing non-goals

The following do not become automatic roadmap items merely because an API becomes available:

- Arbitrary Word fields
- General header and footer authoring
- Watermarks and page backgrounds
- Drawing canvases and text boxes
- Tracked changes
- Comments and review workflows
- Forms and document protection
- Full Word feature parity

## First implementation task

Begin with Phase 0. Create executable capability tests against the latest stable `python-docx`, record the exact version, and resolve the hyperlink and image-alt-text questions. Do not scaffold the full renderer until the required public API paths are proven. That short investigation protects the 1.0.0 contract from accidental private XML dependencies.
