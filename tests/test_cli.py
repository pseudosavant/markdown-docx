from __future__ import annotations

import io
import json
from pathlib import Path

from markdown_docx.cli import main


def invoke(args: list[str], *, stdin_text: str = "") -> tuple[int, str, str]:
    stdout = io.StringIO()
    stderr = io.StringIO()
    code = main(args, stdin=io.StringIO(stdin_text), stdout=stdout, stderr=stderr)
    return code, stdout.getvalue(), stderr.getvalue()


def test_no_arguments_shows_help() -> None:
    code, stdout, stderr = invoke([])
    assert code == 0
    assert "markdown-docx 1.0.0" in stdout
    assert "Agent skill:" in stdout
    assert stderr == ""


def test_version_and_about() -> None:
    assert invoke(["--version"]) == (0, "markdown-docx 1.0.0\n", "")
    code, stdout, stderr = invoke(["--about"])
    assert code == 0
    assert "pseudosavant/markdown-docx" in stdout
    assert stderr == ""


def test_render_default_path_and_overwrite_protection(tmp_path: Path) -> None:
    source = tmp_path / "brief.md"
    source.write_text("# Brief\n\nBody.\n", encoding="utf-8")
    code, stdout, stderr = invoke([str(source)])
    output = source.with_suffix(".docx").resolve()
    assert code == 0
    assert stdout.strip() == str(output)
    assert output.is_file()
    assert stderr == ""

    code, stdout, stderr = invoke([str(source)])
    assert code == 2
    assert stdout == ""
    assert "output_exists" in stderr


def test_render_json_is_clean_and_structured(tmp_path: Path) -> None:
    source = tmp_path / "brief.md"
    source.write_text("# Brief\n\nBody.\n", encoding="utf-8")
    output = tmp_path / "brief.docx"
    code, stdout, stderr = invoke([str(source), str(output), "--json"])
    payload = json.loads(stdout)
    assert code == 0
    assert payload == {
        "ok": True,
        "mode": "render",
        "input": str(source.resolve()),
        "template": "packaged-default",
        "output": str(output.resolve()),
        "sections": 1,
        "warnings": [],
    }
    assert stderr == ""


def test_json_error_uses_stdout_only(tmp_path: Path) -> None:
    source = tmp_path / "bad.md"
    source.write_text("[link](https://example.com)\n", encoding="utf-8")
    code, stdout, stderr = invoke([str(source), "--json"])
    payload = json.loads(stdout)
    assert code == 6
    assert payload["ok"] is False
    assert payload["error"]["code"] == "unsupported_feature"
    assert payload["error"]["line"] == 1
    assert stderr == ""


def test_syntax_and_template_inspection_modes() -> None:
    code, stdout, stderr = invoke(["--syntax", "--json"])
    assert code == 0
    syntax = json.loads(stdout)
    assert syntax["format"] == "markdown-docx"
    assert "multi-paragraph list items" in syntax["text"]
    assert stderr == ""

    code, stdout, stderr = invoke(["--inspect-template", "--json"])
    payload = json.loads(stdout)
    assert code == 0
    assert payload["valid"] is True
    assert payload["template"] == "packaged-default"
    assert stderr == ""


def test_style_listing_modes() -> None:
    code, stdout, stderr = invoke(["--list-styles"])
    assert code == 0
    assert "Heading 1" in stdout
    assert "Code Block" in stdout
    assert stderr == ""

    code, stdout, stderr = invoke(["--list-table-styles"])
    assert code == 0
    assert "Table Grid" in stdout
    assert stderr == ""


def test_stdin_requires_and_uses_base_dir(tmp_path: Path) -> None:
    output = tmp_path / "stdin.docx"
    code, stdout, stderr = invoke(
        ["--input", "-", "--output", str(output), "--base-dir", str(tmp_path), "--json"],
        stdin_text="# From stdin\n",
    )
    assert code == 0
    assert json.loads(stdout)["input"] == "<stdin>"
    assert output.is_file()
    assert stderr == ""

    code, stdout, stderr = invoke(["--input", "-", "--output", str(output)], stdin_text="# Bad\n")
    assert code == 2
    assert "requires --base-dir" in stderr


def test_skill_install_remove_and_unmanaged_safety(tmp_path: Path) -> None:
    root = tmp_path / "skills"
    code, stdout, stderr = invoke(["skill", "install", "--skills-dir", str(root), "--json"])
    payload = json.loads(stdout)
    skill_file = root / "markdown-docx" / "SKILL.md"
    assert code == 0
    assert payload["created"] is True
    assert skill_file.is_file()
    assert "managed-by: markdown-docx" in skill_file.read_text(encoding="utf-8")
    assert stderr == ""

    code, stdout, stderr = invoke(["skill", "remove", "--skills-dir", str(root), "--json"])
    assert code == 0
    assert json.loads(stdout)["removed"] is True
    assert not skill_file.parent.exists()
    assert stderr == ""

    skill_file.parent.mkdir(parents=True)
    skill_file.write_text("unmanaged", encoding="utf-8")
    code, stdout, stderr = invoke(["skill", "install", "--skills-dir", str(root)])
    assert code == 2
    assert stdout == ""
    assert "unmanaged" in stderr.lower()


def test_conflicting_and_invalid_arguments_fail_cleanly(tmp_path: Path) -> None:
    source = tmp_path / "x.md"
    source.write_text("Text\n", encoding="utf-8")
    code, _, stderr = invoke([str(source), "--input", str(source)])
    assert code == 2
    assert "either positional input" in stderr

    code, _, stderr = invoke(["--syntax", "--list-styles"])
    assert code == 2
    assert "mutually exclusive" in stderr

    code, _, stderr = invoke([str(source), str(tmp_path / "wrong.pdf")])
    assert code == 2
    assert ".docx extension" in stderr
