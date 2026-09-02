from __future__ import annotations

from pathlib import Path


def test_production_code_does_not_use_private_docx_or_direct_ooxml_apis() -> None:
    package_dir = Path(__file__).parents[1] / "src" / "markdown_docx"
    forbidden = (
        "docx.oxml",
        "._element",
        "._p",
        "._r",
        "._tc",
        "._tbl",
        "._sectPr",
        "._part",
    )
    for path in package_dir.glob("*.py"):
        source = path.read_text(encoding="utf-8")
        for marker in forbidden:
            assert marker not in source, f"{path.name} uses forbidden private or OOXML marker {marker}"
