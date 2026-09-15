from __future__ import annotations

from pathlib import Path


def test_private_docx_and_ooxml_apis_are_isolated_to_hyperlink_helper() -> None:
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
    for path in package_dir.rglob("*.py"):
        if path == package_dir / "hyperlinks.py":
            continue
        source = path.read_text(encoding="utf-8")
        for marker in forbidden:
            assert marker not in source, f"{path.name} uses forbidden private or OOXML marker {marker}"
