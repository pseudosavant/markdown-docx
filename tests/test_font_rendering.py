"""Opt-in layout-engine checks. LibreOffice runs in CI and Word runs on Windows."""

from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path
from zipfile import ZipFile

import pdfplumber
import pytest
from docx import Document

from markdown_docx.parser import parse_document
from markdown_docx.renderer import render_docx
from markdown_docx.styles import apply_font_overrides

RENDERER = os.environ.get("MARKDOWN_DOCX_FONT_RENDERER", "")
pytestmark = pytest.mark.skipif(not RENDERER, reason="Set MARKDOWN_DOCX_FONT_RENDERER to word or libreoffice")


def normalized_font(name: str) -> str:
    return re.sub(r"[^a-z]", "", name.split("+")[-1].lower())


def export_pdf(source: Path, tmp_path: Path) -> Path:
    output = source.with_suffix(".pdf")
    if RENDERER == "word":
        command = ["uvx", "office-export", str(source), "--to", "pdf", "--output", str(output), "--json"]
    elif RENDERER == "libreoffice":
        profile = (tmp_path / "lo-profile").as_uri()
        command = [
            "libreoffice",
            f"-env:UserInstallation={profile}",
            "--headless",
            "--convert-to",
            "pdf",
            "--outdir",
            str(tmp_path),
            str(source),
        ]
    else:
        raise AssertionError(f"Unknown font renderer: {RENDERER}")
    result = subprocess.run(command, capture_output=True, text=True, timeout=180, check=False)
    assert result.returncode == 0, result.stdout + result.stderr
    if RENDERER == "word":
        details = json.loads(result.stdout)
        assert details["ok"], details
        assert all(warning["code"] == "owned_office_process_forced" for warning in details["warnings"]), details
    assert output.is_file(), result.stdout + result.stderr
    return output


def assert_pdf_fonts(path: Path, body: str, headings: str, monospace: str) -> None:
    expected = {f"Heading{level}": headings for level in range(1, 7)}
    expected.update(
        dict.fromkeys(
            [
                "BodyPlain",
                "BodyBold",
                "BodyItalic",
                "BodyBoth",
                "BodyLink",
                "QuoteText",
                "BulletText",
                "NumberText",
                "TableHeader",
                "TableCell",
            ],
            body,
        )
    )
    expected.update({"InlineCode": monospace, "BlockCode": monospace, "HeadingCode": monospace})
    found = {}
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            for word in page.extract_words(extra_attrs=["fontname"]):
                text = word["text"]
                if text in expected:
                    expected_family = normalized_font(expected[text])
                    actual = normalized_font(word["fontname"])
                    suffix = actual.removeprefix(expected_family)
                    assert suffix in {
                        "",
                        "regular",
                        "bold",
                        "italic",
                        "bolditalic",
                        "mt",
                        "boldmt",
                        "italicmt",
                        "bolditalicmt",
                    }, (text, expected[text], word["fontname"])
                    found[text] = word["fontname"]
    assert set(found) == set(expected), f"Missing rendered text: {set(expected) - set(found)}"


def test_rendered_fonts_follow_theme_and_subsequent_theme_change(tmp_path: Path) -> None:
    if RENDERER == "word":
        body, headings, mono = "Aptos", "Aptos Display", "Consolas"
        next_body, next_headings = "Verdana", "Georgia"
    else:
        body, headings, mono = "Liberation Sans", "Liberation Serif", "Liberation Mono"
        next_body, next_headings = headings, body
    source = f"""<!-- markdown-docx
document:
  fonts:
    body: {body}
    headings: {headings}
    monospace: {mono}
-->

# Heading1 `HeadingCode`

## Heading2

### Heading3

#### Heading4

##### Heading5

###### Heading6

BodyPlain **BodyBold** *BodyItalic* ***BodyBoth*** [BodyLink](https://example.com) `InlineCode`

> QuoteText

- BulletText

1. NumberText

| TableHeader |
| --- |
| TableCell |

```text
BlockCode
```
"""
    model = parse_document(source, input_path=tmp_path / "fonts.md", source_name="fonts.md")
    output = tmp_path / "fonts.docx"
    render_docx(model, output, template_path=None, base_dir=tmp_path, allow_remote_images=False)
    assert_pdf_fonts(export_pdf(output, tmp_path), body, headings, mono)

    document = Document(output)
    model.options.fonts.body = next_body
    model.options.fonts.headings = next_headings
    apply_font_overrides(document, model.options)
    changed = tmp_path / "changed-theme.docx"
    document.save(changed)
    with ZipFile(output) as before, ZipFile(changed) as after:
        for part in ("word/document.xml", "word/styles.xml"):
            assert before.read(part) == after.read(part), f"Retheming changed {part}"
        assert before.read("word/theme/theme1.xml") != after.read("word/theme/theme1.xml")
    assert_pdf_fonts(export_pdf(changed, tmp_path), next_body, next_headings, mono)
