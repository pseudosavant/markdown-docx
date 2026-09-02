# AGENTS.md

This repository contains `markdown-docx`, a strict Python CLI that converts constrained Markdown into editable Word `.docx` files.

## Project identity

- Published package: `markdown-docx`
- CLI command: `markdown-docx`
- Python package: `markdown_docx`

## Core rules

- Use only supported public `python-docx` APIs in production code.
- Never edit OOXML parts directly in production code.
- Preserve normal Markdown meaning and keep Word metadata in invisible reserved HTML comments.
- Reject unsupported behavior with stable, line-aware diagnostics.
- Treat Word sections as layout boundaries. Headings never create sections.
- Never report a stable page count without a Word-compatible layout engine.
- Keep parser models independent of `python-docx` objects.
- Add or update tests whenever behavior changes.
- Do not use em dashes or semicolons in documentation, messages, or comments.

Tests may inspect generated OOXML read-only for precise assertions.

## Commands

```powershell
$env:UV_LINK_MODE="copy"
uv sync --locked --all-groups
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv build
uv run twine check dist/*
uvx --refresh --from . markdown-docx sample\showcase.md sample\showcase.docx --force
```

## Contract files

When the input format changes, update the parser, tests, `README.md`, `src/markdown_docx/assets/syntax.json`, the managed skill text, and the showcase together.
