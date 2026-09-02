from __future__ import annotations

import json
from importlib import resources
from typing import Any


def default_template_bytes() -> bytes:
    return resources.files("markdown_docx").joinpath("assets", "default.docx").read_bytes()


def load_syntax_payload() -> dict[str, Any]:
    text = resources.files("markdown_docx").joinpath("assets", "syntax.json").read_text(encoding="utf-8")
    payload: dict[str, Any] = json.loads(text)
    return payload
