from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from markdown_docx.errors import UsageError

SKILL_NAME = "markdown-docx"
MANAGED_MARKER = "<!-- managed-by: markdown-docx -->"

SKILL_MD = f"""---
name: markdown-docx
description: Create editable Word documents from strict Markdown using `uvx markdown-docx`. Use for authoring, rendering, validating, or inspecting markdown-docx sources and blank DOCX formatting templates.
---

{MANAGED_MARKER}

# Markdown DOCX

Use the published CLI through `uvx markdown-docx`. It converts strict Markdown into editable Word documents and keeps Word-specific settings inside invisible HTML comments.

Always invoke the tool as `uvx markdown-docx ...`. Do not assume a global install.

## Inspect first

Inspect the syntax and template before authoring a document:

```text
uvx markdown-docx --syntax
uvx markdown-docx --inspect-template --template formatting.docx --json
uvx markdown-docx --list-styles --template formatting.docx
uvx markdown-docx --list-table-styles --template formatting.docx
```

Custom templates must be blank `.docx` files. They may contain styles, themes, fonts, numbering definitions, and page defaults. They may not contain body content, tables, drawings, or nonempty headers and footers.

## Render a document

```text
uvx markdown-docx input.md output.docx --json
```

If no output is supplied, the tool writes a `.docx` beside the Markdown source. Add `--force` only when replacing generated output is authorized.

## Metadata

Document metadata must be the first non-whitespace content:

```text
<!-- markdown-docx
document:
  page_size: letter
  orientation: portrait
  margins:
    top: 1in
    right: 1in
    bottom: 1in
    left: 1in
-->
```

Start a next-page section with a `section` comment. Insert an explicit page break with `<!-- markdown-docx: page-break -->`. Put `table` metadata immediately before a pipe table and `image` metadata immediately before a standalone image.

Run `uvx markdown-docx --syntax` for every accepted key and value.

## Supported Markdown

Use ATX headings, paragraphs, emphasis, strong text, inline code, hard line breaks, fenced code blocks, blockquotes, lists, pipe tables, and local or remote images. Links are rejected in 0.1.0 because `python-docx` 1.2.0 does not provide public hyperlink creation. Raw HTML, task lists, footnotes, horizontal rules, indented code, multi-paragraph list items, and unsupported nested block content are rejected.

Relative image paths resolve from the Markdown file. When reading stdin, provide an output and `--base-dir`. Use `--no-remote-images` for offline or untrusted input.

## Handle results

Prefer `--json` for automation. Success includes the absolute output path, section count, template identifier, and warnings. Failures include a stable code, message, input path, and line when available. Correct the source before retrying.
"""


def default_skills_dir() -> Path:
    return Path.home() / ".agents" / "skills"


def skill_dir(skills_dir: Path | None = None) -> Path:
    return (skills_dir or default_skills_dir()) / SKILL_NAME


def install_skill(skills_dir: Path | None = None) -> dict[str, Any]:
    target = skill_dir(skills_dir)
    skill_path = target / "SKILL.md"
    if target.exists() and not skill_path.exists():
        raise UsageError(f"Refusing to install into '{target}' because it contains no managed SKILL.md.")
    if skill_path.exists() and MANAGED_MARKER not in skill_path.read_text(encoding="utf-8"):
        raise UsageError(f"Refusing to overwrite unmanaged skill file '{skill_path}'.")
    target.mkdir(parents=True, exist_ok=True)
    existed = skill_path.exists()
    previous = skill_path.read_text(encoding="utf-8") if existed else ""
    updated = existed and previous != SKILL_MD
    skill_path.write_text(SKILL_MD, encoding="utf-8", newline="\n")
    return {
        "installed": True,
        "created": not existed,
        "updated": updated,
        "skill": SKILL_NAME,
        "path": str(skill_path),
    }


def remove_skill(skills_dir: Path | None = None, *, force: bool = False) -> dict[str, Any]:
    target = skill_dir(skills_dir)
    skill_path = target / "SKILL.md"
    if not target.exists():
        return {"removed": False, "skill": SKILL_NAME, "path": str(target), "reason": "not_installed"}
    if not skill_path.exists():
        raise UsageError(f"Refusing to remove '{target}' because SKILL.md is missing.")
    content = skill_path.read_text(encoding="utf-8")
    if MANAGED_MARKER not in content and not force:
        raise UsageError(f"Refusing to remove unmanaged skill '{target}'. Use --force to override.")
    extra_paths = [path for path in target.iterdir() if path.name != "SKILL.md"]
    if extra_paths and not force:
        names = ", ".join(sorted(path.name for path in extra_paths))
        raise UsageError(f"Refusing to remove '{target}' because it contains unmanaged entries: {names}. Use --force.")
    shutil.rmtree(target)
    return {"removed": True, "skill": SKILL_NAME, "path": str(target)}
