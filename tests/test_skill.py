from __future__ import annotations

import hashlib
import io
import json
import re
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from markdown_docx import __version__, skill
from markdown_docx.errors import UsageError

OLD_VERSION = "0.0.1"


@pytest.fixture
def installed_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(skill, "runtime_source", lambda: "installed")


def write_skill(content: str, root: Path | None = None) -> Path:
    path = skill.skill_dir(root) / "SKILL.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content.encode("utf-8"))
    return path


def synchronize(version: str = __version__) -> str:
    stderr = io.StringIO()
    skill.synchronize_skill(stderr=stderr, version=version)
    return stderr.getvalue()


def with_hash(content: str) -> str:
    blanked = re.sub(r"(?m)^(  managed-content-sha256: ).*$", r'\1""', content)
    digest = hashlib.sha256(blanked.encode("utf-8")).hexdigest()
    return blanked.replace('managed-content-sha256: ""', f'managed-content-sha256: "sha256:{digest}"')


def test_canonical_install_metadata_and_hash() -> None:
    result = skill.install_skill()
    path = Path(result["path"])
    data = path.read_bytes()
    text = data.decode("utf-8")
    front = yaml.safe_load(text.split("---\n")[1])
    fields = front["metadata"]
    assert front["name"] == skill.SKILL_NAME
    assert "uvx markdown-docx" in front["description"]
    assert fields["managed-by"] == "markdown-docx"
    assert fields["managed-version"] == __version__
    assert f'managed-version: "{__version__}"' in text
    assert re.fullmatch(r"sha256:[0-9a-f]{64}", fields["managed-content-sha256"])
    assert with_hash(text) == text
    assert "version" not in front
    assert skill.MANAGED_MARKER not in text
    assert "Always invoke the tool as `uvx markdown-docx ...`" in text
    assert not data.startswith(b"\xef\xbb\xbf")
    assert b"\r" not in data
    assert data.endswith(b"\n")
    assert list(path.parent.iterdir()) == [path]
    assert result["created"] and not result["updated"]


@pytest.mark.parametrize("newline", ["\n", "\r\n", "\r"])
def test_hash_normalizes_line_endings(newline: str) -> None:
    content = skill.render_skill().replace("\n", newline)
    assert skill.inspect_skill(content).integrity == "valid"


@pytest.mark.parametrize(
    ("before", "after"),
    [
        ("# Markdown DOCX", "# My customized DOCX"),
        ("name: markdown-docx", "name: customized-docx"),
        ("description: Create", "description: Altered"),
        (f'managed-version: "{__version__}"', 'managed-version: "0.0.1"'),
        ("metadata:\n", "metadata:\n  author: Someone\n"),
    ],
)
def test_hash_covers_body_and_front_matter(before: str, after: str) -> None:
    assert skill.inspect_skill(skill.render_skill().replace(before, after)).integrity == "altered"


def test_hash_preserves_yaml_formatting_and_unrelated_metadata() -> None:
    content = skill.render_skill().replace("metadata:\n", "metadata:\n  author: 'Someone'  # Preserve formatting\n")
    content = with_hash(content)
    content = content.replace('managed-content-sha256: "sha256:', "managed-content-sha256: 'sha256:")
    content = re.sub(r"(?m)^(  managed-content-sha256: .*?)\"$", r"\1'", content)
    assert skill.inspect_skill(content).integrity == "valid"
    assert yaml.safe_load(content.split("---\n")[1])["metadata"]["author"] == "Someone"


@pytest.mark.parametrize("directory_exists", [False, True])
def test_absent_skill_is_not_installed(installed_runtime: None, directory_exists: bool) -> None:
    target = skill.skill_dir()
    if directory_exists:
        target.mkdir(parents=True)
    assert synchronize() == ""
    assert not (target / "SKILL.md").exists()
    assert target.exists() == directory_exists


@pytest.mark.parametrize(
    "content",
    [
        "A personal skill\n",
        "---\nname: markdown-docx\n---\nPersonal instructions\n",
        skill.render_skill(OLD_VERSION).replace("managed-by: markdown-docx", "managed-by: another-tool")
        + skill.MANAGED_MARKER,
        "---\nmetadata:\n  managed-by: null\n---\n" + skill.MANAGED_MARKER,
        "--- \nmetadata:\n  managed-by: another-tool\n---\n" + skill.MANAGED_MARKER,
        "\ufeff---\nmetadata:\n  managed-by: another-tool\n---\n" + skill.MANAGED_MARKER,
    ],
)
def test_unmanaged_content_is_never_replaced(installed_runtime: None, content: str) -> None:
    path = write_skill(content)
    assert synchronize() == ""
    for force in (False, True):
        with pytest.raises(UsageError, match="unmanaged"):
            skill.install_skill(force=force)
    assert path.read_text(encoding="utf-8") == content


def test_pristine_older_skill_updates(installed_runtime: None) -> None:
    path = write_skill(skill.render_skill(OLD_VERSION))
    notice = synchronize()
    assert OLD_VERSION in notice and __version__ in notice and str(path) in notice
    assert len(notice.splitlines()) == 1
    assert path.read_bytes() == skill.render_skill().encode("utf-8")
    assert skill.skill_status()["version_relation"] == "equal"


@pytest.mark.parametrize("mutation", ["body", "missing", "malformed", "uppercase"])
def test_older_unverifiable_skill_is_preserved_and_force_can_restore(installed_runtime: None, mutation: str) -> None:
    content = skill.render_skill(OLD_VERSION)
    if mutation == "body":
        content += "Local instructions\n"
    elif mutation == "missing":
        content = re.sub(r"(?m)^  managed-content-sha256: .*\n", "", content)
    elif mutation == "malformed":
        content = re.sub(r"sha256:[0-9a-f]{64}", "sha256:123", content)
    else:
        content = re.sub(r"sha256:[0-9a-f]{64}", lambda match: match[0].upper(), content)
    path = write_skill(content)
    before = path.stat().st_mtime_ns
    notice = synchronize()
    status = skill.skill_status()
    assert skill.FORCE_INSTALL_COMMAND in notice
    assert len(notice.splitlines()) == 1
    assert status["integrity"] == {"body": "altered", "uppercase": "malformed"}.get(mutation, mutation)
    assert not status["automatic_sync_eligible"]
    assert status["force_install_command"] == skill.FORCE_INSTALL_COMMAND
    with pytest.raises(UsageError, match=re.escape(skill.FORCE_INSTALL_COMMAND)):
        skill.install_skill()
    assert path.read_bytes() == content.encode("utf-8")
    assert path.stat().st_mtime_ns == before
    assert skill.install_skill(force=True)["updated"]
    assert path.read_bytes() == skill.render_skill().encode("utf-8")


@pytest.mark.parametrize("version", [__version__, "999.0"])
@pytest.mark.parametrize("altered", [False, True])
def test_equal_and_newer_versions_are_quiet_and_never_rewritten(
    installed_runtime: None, version: str, altered: bool, monkeypatch: pytest.MonkeyPatch
) -> None:
    content = skill.render_skill(version) + ("Changes\n" if altered else "")
    path = write_skill(content)

    def forbidden(*args: object) -> None:
        pytest.fail("An equal or newer skill must not be replaced automatically")

    monkeypatch.setattr(skill.os, "replace", forbidden)
    assert synchronize() == ""
    assert path.read_bytes() == content.encode("utf-8")
    if version == "999.0":
        assert not skill.install_skill(force=True)["updated"]
    elif not altered:
        assert not skill.install_skill()["updated"]
    else:
        with pytest.raises(UsageError, match="altered"):
            skill.install_skill()


def test_force_restores_equal_version_edits() -> None:
    path = write_skill(skill.render_skill() + "Edited\n")
    assert skill.install_skill(force=True)["updated"]
    assert path.read_bytes() == skill.render_skill().encode("utf-8")


@pytest.mark.parametrize(
    ("installed", "running", "relation"),
    [
        ("1.9", "1.10", "older"),
        ("1.0rc1", "1.0", "older"),
        ("1.0.dev1", "1.0a1", "older"),
        ("1.0", "1.0.post1", "older"),
        ("1.0", "1.0.0", "equal"),
        ("1!0.1", "9.9", "newer"),
        ("1.0+local", "1.0", "newer"),
    ],
)
def test_pep440_ordering(installed_runtime: None, installed: str, running: str, relation: str) -> None:
    path = write_skill(skill.render_skill(installed))
    assert skill.skill_status(version=running)["version_relation"] == relation
    notice = synchronize(running)
    assert bool(notice) == (relation == "older")
    assert skill.inspect_skill(path.read_text(encoding="utf-8")).managed_version == (
        running if relation == "older" else installed
    )


@pytest.mark.parametrize("version_field", [None, '"invalid"', "false", "[1, 2]", '""'])
def test_missing_or_malformed_version_recovers_without_hash(installed_runtime: None, version_field: str | None) -> None:
    content = "---\nmetadata:\n  managed-by: markdown-docx\n"
    if version_field is not None:
        content += f"  managed-version: {version_field}\n"
    content += "  managed-content-sha256: broken\n---\nChanged content\n"
    path = write_skill(content)
    assert skill.skill_status()["automatic_sync_eligible"]
    assert "Updated managed skill" in synchronize()
    assert path.read_bytes() == skill.render_skill().encode("utf-8")


def test_legacy_migration_treats_unversioned_skill_as_zero(installed_runtime: None) -> None:
    path = write_skill("---\nname: markdown-docx\n---\n\n" + skill.MANAGED_MARKER + "\nLegacy instructions\n")
    assert skill.skill_status()["integrity"] == "legacy"
    assert skill.skill_status()["version_relation"] == "older"
    assert f"0 -> {__version__}" in synchronize()
    assert path.read_bytes() == skill.render_skill().encode("utf-8")


def test_legacy_marker_with_valid_version_still_requires_hash(installed_runtime: None) -> None:
    content = f'---\nmetadata:\n  managed-version: "{OLD_VERSION}"\n---\n{skill.MANAGED_MARKER}\n'
    path = write_skill(content)
    assert skill.skill_status()["integrity"] == "missing"
    assert skill.FORCE_INSTALL_COMMAND in synchronize()
    assert path.read_text(encoding="utf-8") == content


def test_hash_replacement_only_changes_metadata_value() -> None:
    content = re.sub(r"sha256:[0-9a-f]{64}", "", skill.render_skill(), count=1)
    content += '\nExample 🐕:\n  managed-content-sha256: "sha256:' + "a" * 64 + '"\n'
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
    content = content.replace('managed-content-sha256: ""', f'managed-content-sha256: "sha256:{digest}"', 1)
    assert skill.inspect_skill(content).integrity == "valid"


def test_invalid_running_version_skips_sync(installed_runtime: None) -> None:
    path = write_skill(skill.render_skill(OLD_VERSION))
    before = path.read_bytes()
    assert synchronize("not-a-version") == ""
    assert path.read_bytes() == before
    assert skill.skill_status(version="not-a-version")["automatic_sync_reason"] == "invalid_cli_version"


@pytest.mark.parametrize(
    ("origin", "expected"),
    [
        (None, "installed"),
        ({"url": "file:///project", "dir_info": {"editable": True}}, "local"),
        ({"url": "file:///project", "dir_info": {}}, "local"),
        ({"url": "file:///project"}, "local"),
        ({"url": "file:///source.tar.gz", "archive_info": {}}, "local"),
        ({"url": "file:///markdown_docx-0.1.0-py3-none-any.whl", "archive_info": {}}, "installed"),
        ({"url": "https://example.test/package.whl", "archive_info": {}}, "installed"),
        ({"url": "https://example.test/source", "dir_info": {"editable": True}}, "local"),
        ({"url": "file:///package.whl"}, "local"),
        ({"url": "relative/path"}, "unknown"),
        ({"url": 3}, "unknown"),
        ({"url": "file:///project", "dir_info": []}, "unknown"),
        ([], "unknown"),
        ("broken json", "unknown"),
    ],
)
def test_distribution_source_detection(monkeypatch: pytest.MonkeyPatch, origin: object, expected: str) -> None:
    direct_url = None if origin is None else origin if isinstance(origin, str) else json.dumps(origin)
    distribution = SimpleNamespace(
        read_text=lambda name: direct_url,
        locate_file=lambda path: Path(skill.__file__).parents[1] / path,
    )
    monkeypatch.setattr(skill.metadata, "distribution", lambda name: distribution)
    assert skill.runtime_source() == expected


def test_checkout_shadowing_an_installed_distribution_is_local(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    distribution = SimpleNamespace(read_text=lambda name: None, locate_file=lambda path: tmp_path / path)
    monkeypatch.setattr(skill.metadata, "distribution", lambda name: distribution)
    assert skill.runtime_source() == "local"


def test_missing_distribution_is_local(monkeypatch: pytest.MonkeyPatch) -> None:
    def missing(name: str) -> None:
        raise skill.metadata.PackageNotFoundError(name)

    monkeypatch.setattr(skill.metadata, "distribution", missing)
    assert skill.runtime_source() == "local"


@pytest.mark.parametrize("editable", [False, True])
def test_local_source_skips_automatic_but_allows_explicit_install(
    monkeypatch: pytest.MonkeyPatch, editable: bool
) -> None:
    distribution = SimpleNamespace(
        read_text=lambda name: json.dumps({"url": "file:///project", "dir_info": {"editable": editable}})
    )
    monkeypatch.setattr(skill.metadata, "distribution", lambda name: distribution)
    path = write_skill(skill.render_skill(OLD_VERSION))
    original = path.read_bytes()
    assert synchronize() == ""
    assert path.read_bytes() == original
    status = skill.skill_status()
    assert status["local_development"]
    assert status["automatic_sync_reason"] == "local_development"
    assert not status["automatic_sync_eligible"]
    assert skill.install_skill()["updated"]
    assert path.read_bytes() == skill.render_skill().encode("utf-8")


def test_custom_directory_requires_explicit_update(installed_runtime: None, tmp_path: Path) -> None:
    custom = tmp_path / "custom skills"
    result = skill.install_skill(custom, version=OLD_VERSION)
    path = Path(result["path"])
    original = path.read_bytes()
    assert synchronize() == ""
    assert not skill.skill_dir().exists()
    assert path.read_bytes() == original
    status = skill.skill_status(custom)
    assert not status["automatic_sync_eligible"]
    assert status["automatic_sync_reason"] == "custom_directory"
    assert status["version_relation"] == "older"
    assert skill.install_skill(custom)["updated"]


def test_status_is_read_only_and_reports_eligibility(installed_runtime: None) -> None:
    absent = skill.skill_status()
    assert not absent["installed"] and not absent["managed"]
    assert absent["integrity"] == "not_applicable"
    assert not absent["automatic_sync_eligible"]
    path = write_skill(skill.render_skill(OLD_VERSION))
    before = path.read_bytes(), path.stat().st_mtime_ns
    status = skill.skill_status()
    assert status["path"] == str(path)
    assert status["standard_location"] and status["installed"] and status["managed"]
    assert status["cli_version"] == __version__
    assert status["managed_version"] == OLD_VERSION
    assert status["version_relation"] == "older"
    assert status["integrity"] == "valid"
    assert status["automatic_sync_eligible"]
    assert not status["local_development"]
    assert (path.read_bytes(), path.stat().st_mtime_ns) == before


def test_replacement_is_complete_closed_and_atomic(installed_runtime: None, monkeypatch: pytest.MonkeyPatch) -> None:
    path = write_skill(skill.render_skill(OLD_VERSION))
    original = path.read_bytes()
    replace = skill.os.replace
    calls = []

    def observe(source: Path, destination: Path) -> None:
        assert source.parent == destination.parent == path.parent
        assert path.read_bytes() == original
        assert source.read_bytes() == skill.render_skill().encode("utf-8")
        replace(source, destination)
        assert path.read_bytes() == skill.render_skill().encode("utf-8")
        calls.append(destination)

    monkeypatch.setattr(skill.os, "replace", observe)
    assert "Updated" in synchronize()
    assert calls == [path]
    assert list(path.parent.iterdir()) == [path]


@pytest.mark.parametrize("operation", ["replace", "fsync"])
def test_write_failure_preserves_original_and_cleans_temp(
    installed_runtime: None, monkeypatch: pytest.MonkeyPatch, operation: str
) -> None:
    path = write_skill(skill.render_skill(OLD_VERSION))
    original = path.read_bytes()

    def failure(*args: object) -> None:
        raise OSError("Simulated failure")

    monkeypatch.setattr(skill.os, operation, failure)
    assert "Could not synchronize" in synchronize()
    assert path.read_bytes() == original
    assert list(path.parent.iterdir()) == [path]


@pytest.mark.parametrize(
    "replacement",
    [skill.render_skill("999.0"), "Unmanaged\n", skill.render_skill() + "Edits\n", None],
    ids=["newer", "unmanaged", "edited", "removed"],
)
def test_concurrent_changes_are_revalidated_before_replacement(
    installed_runtime: None, monkeypatch: pytest.MonkeyPatch, replacement: str | None
) -> None:
    path = write_skill(skill.render_skill(OLD_VERSION))

    def concurrent_change(descriptor: int) -> None:
        if replacement is None:
            path.unlink()
        else:
            path.write_bytes(replacement.encode("utf-8"))

    monkeypatch.setattr(skill.os, "fsync", concurrent_change)
    assert synchronize() == ""
    assert (path.read_bytes() if path.exists() else None) == (replacement.encode("utf-8") if replacement else None)
    assert not list(path.parent.glob(".SKILL-*.tmp"))


@pytest.mark.parametrize(
    "content", ["---\nmetadata: [\n---\n", "---\nmetadata:\n  managed-by: markdown-docx\n  managed-by: other\n---\n"]
)
def test_unparseable_metadata_is_preserved(installed_runtime: None, content: str) -> None:
    path = write_skill(content + skill.MANAGED_MARKER)
    before = path.read_bytes()
    assert "Could not synchronize" in synchronize()
    assert path.read_bytes() == before
    with pytest.raises(UsageError, match="Cannot inspect"):
        skill.install_skill(force=True)


@pytest.mark.parametrize("legacy", [False, True])
def test_managed_removal_and_extra_file_safety(legacy: bool) -> None:
    path = write_skill(skill.MANAGED_MARKER if legacy else skill.render_skill())
    extra = path.parent / "notes.txt"
    extra.write_text("Keep me", encoding="utf-8")
    with pytest.raises(UsageError, match="unmanaged entries"):
        skill.remove_skill()
    assert extra.read_text(encoding="utf-8") == "Keep me"
    extra.unlink()
    assert skill.remove_skill()["removed"]
    assert not path.parent.exists()
    assert not skill.remove_skill()["removed"]


def test_force_removal_retains_existing_unmanaged_and_extra_file_semantics() -> None:
    path = write_skill("Personal skill")
    extra = path.parent / "notes.txt"
    extra.write_text("Notes", encoding="utf-8")
    with pytest.raises(UsageError, match="unmanaged"):
        skill.remove_skill()
    assert skill.remove_skill(force=True)["removed"]
    assert not path.parent.exists()
    write_skill("---\nmalformed: [\n---\n")
    assert skill.remove_skill(force=True)["removed"]


def test_existing_directory_without_skill_is_preserved() -> None:
    target = skill.skill_dir()
    target.mkdir(parents=True)
    extra = target / "notes.txt"
    extra.write_text("Notes", encoding="utf-8")
    for force in (False, True):
        with pytest.raises(UsageError, match=r"no managed SKILL\.md"):
            skill.install_skill(force=force)
        with pytest.raises(UsageError, match=r"SKILL\.md is missing"):
            skill.remove_skill(force=force)
    assert extra.read_text(encoding="utf-8") == "Notes"


def test_install_preserves_unrelated_files_next_to_managed_skill() -> None:
    path = write_skill(skill.render_skill(OLD_VERSION))
    extra = path.parent / "notes.txt"
    extra.write_text("Notes", encoding="utf-8")
    assert skill.install_skill()["updated"]
    assert extra.read_text(encoding="utf-8") == "Notes"


@pytest.mark.parametrize("directory_is_file", [False, True])
def test_unexpected_filesystem_entries_are_preserved(installed_runtime: None, directory_is_file: bool) -> None:
    target = skill.skill_dir()
    target.parent.mkdir(parents=True)
    if directory_is_file:
        target.write_text("Unrelated file", encoding="utf-8")
    else:
        (target / "SKILL.md").mkdir(parents=True)
    with pytest.raises(UsageError, match="not a"):
        skill.install_skill(force=True)
    assert "Could not synchronize" in synchronize()
    if directory_is_file:
        assert target.read_text(encoding="utf-8") == "Unrelated file"
    else:
        assert (target / "SKILL.md").is_dir()
