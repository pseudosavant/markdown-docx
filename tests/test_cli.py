from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

from markdown_docx import __version__, skill
from markdown_docx import cli as cli_module
from markdown_docx.cli import main


def invoke(args: list[str], *, stdin_text: str = "") -> tuple[int, str, str]:
    stdout = io.StringIO()
    stderr = io.StringIO()
    code = main(args, stdin=io.StringIO(stdin_text), stdout=stdout, stderr=stderr)
    return code, stdout.getvalue(), stderr.getvalue()


def test_no_arguments_shows_help() -> None:
    code, stdout, stderr = invoke([])
    assert code == 0
    assert f"markdown-docx {__version__}" in stdout
    assert "Agent skill:" in stdout
    assert stderr == ""


def test_version_and_about() -> None:
    assert invoke(["--version"]) == (0, f"markdown-docx {__version__}\n", "")
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


@pytest.mark.parametrize(
    "args",
    [
        [],
        ["--help"],
        ["-h"],
        ["--version"],
        ["--about"],
        ["--syntax"],
        ["--inspect-template"],
        ["--list-styles"],
        ["--list-table-styles"],
    ],
)
def test_normal_entry_points_synchronize(args: list[str], monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(skill, "runtime_source", lambda: "installed")
    path = skill.skill_dir() / "SKILL.md"
    path.parent.mkdir(parents=True)
    path.write_bytes(skill.render_skill("0.0.1").encode("utf-8"))
    code, stdout, stderr = invoke(args)
    assert code == 0
    assert stdout
    assert "Updated managed skill" in stderr
    assert path.read_bytes() == skill.render_skill().encode("utf-8")


@pytest.mark.parametrize(
    "action", [[], ["--help"], ["install"], ["install", "--help"], ["remove"], ["status"], ["unknown"]]
)
def test_skill_commands_never_synchronize(action: list[str], monkeypatch: pytest.MonkeyPatch) -> None:
    def forbidden(**kwargs: object) -> None:
        pytest.fail("Skill management must not invoke automatic synchronization")

    monkeypatch.setattr(cli_module, "synchronize_skill", forbidden)
    code, _, _ = invoke(["skill", *action])
    assert code == (2 if action == ["unknown"] else 0)


@pytest.mark.parametrize("failure", [False, True])
def test_render_json_stdout_is_clean_during_maintenance(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: bool
) -> None:
    monkeypatch.setattr(skill, "runtime_source", lambda: "installed")
    path = skill.skill_dir() / "SKILL.md"
    path.parent.mkdir(parents=True)
    path.write_bytes(skill.render_skill("0.0.1").encode("utf-8"))
    if failure:

        def fail(*args: object) -> None:
            raise PermissionError("Simulated permission error")

        monkeypatch.setattr(skill, "_atomic_replace", fail)
    source = tmp_path / "source.md"
    source.write_text("# Document\n", encoding="utf-8")
    code, stdout, stderr = invoke([str(source), "--json"])
    assert code == 0
    payload = json.loads(stdout)
    assert payload["ok"] and payload["mode"] == "render"
    assert Path(payload["output"]).is_file()
    assert ("Could not synchronize" if failure else "Updated managed skill") in stderr


def test_sync_failure_does_not_mask_primary_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def failure() -> str:
        raise OSError("Metadata unavailable")

    monkeypatch.setattr(skill, "runtime_source", failure)
    code, stdout, stderr = invoke([str(tmp_path / "missing.md"), "--json"])
    assert code == 2
    assert json.loads(stdout)["error"]["code"] == "input_not_found"
    assert "Could not synchronize" in stderr


def test_skill_status_and_force_cli_contract(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(skill, "runtime_source", lambda: "local")
    root = tmp_path / "custom skills"
    args = ["--skills-dir", str(root)]
    code, stdout, stderr = invoke(["skill", "install", *args, "--json"])
    result = json.loads(stdout)
    assert code == 0 and stderr == "" and result["created"]
    path = Path(result["path"])
    path.write_bytes(path.read_bytes() + b"Edited instructions\n")
    before = path.read_bytes(), path.stat().st_mtime_ns
    code, stdout, stderr = invoke(["skill", "status", *args, "--json"])
    result = json.loads(stdout)
    assert code == 0 and stderr == ""
    assert result["ok"] and result["mode"] == "skill_status"
    assert result["path"] == str(path)
    assert result["cli_version"] == __version__ == result["managed_version"]
    assert result["integrity"] == "altered"
    assert result["version_relation"] == "equal"
    assert result["local_development"] and not result["automatic_sync_eligible"]
    assert skill.FORCE_INSTALL_COMMAND in result["force_install_command"]
    assert str(root) in result["force_install_command"]
    assert (path.read_bytes(), path.stat().st_mtime_ns) == before
    code, stdout, stderr = invoke(["skill", "status", *args])
    assert code == 0 and stderr == ""
    assert "Integrity: altered" in stdout
    assert "Local development: true" in stdout
    code, stdout, stderr = invoke(["skill", "install", *args, "--json"])
    assert code == 2 and stderr == ""
    assert skill.FORCE_INSTALL_COMMAND in json.loads(stdout)["error"]["message"]
    code, stdout, stderr = invoke(["skill", "install", *args, "--force", "--json"])
    assert code == 0 and stderr == "" and json.loads(stdout)["updated"]
    code, stdout, stderr = invoke(["skill", "install", *args, "--json"])
    assert code == 0 and stderr == "" and not json.loads(stdout)["updated"]
    code, _, stderr = invoke(["skill", "status", "--force"])
    assert code == 2 and "--force is valid only" in stderr


def test_install_force_refuses_unmanaged_json_and_remove_force_still_works() -> None:
    path = skill.skill_dir() / "SKILL.md"
    path.parent.mkdir(parents=True)
    path.write_text("Unmanaged", encoding="utf-8")
    code, stdout, stderr = invoke(["skill", "install", "--force", "--json"])
    assert code == 2 and stderr == ""
    assert "unmanaged" in json.loads(stdout)["error"]["message"]
    code, stdout, stderr = invoke(["skill", "remove", "--force", "--json"])
    assert code == 0 and stderr == "" and json.loads(stdout)["removed"]
    assert not path.parent.exists()


def test_skill_help_documents_status_and_force() -> None:
    for args in (["--help"], ["skill", "--help"]):
        code, stdout, stderr = invoke(args)
        assert code == 0 and stderr == ""
        assert "skill status [--skills-dir DIR] [--json]" in stdout
        assert "skill install [--skills-dir DIR] [--force] [--json]" in stdout
    assert skill.FORCE_INSTALL_COMMAND in invoke(["skill", "--help"])[1]
