from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import tempfile
from dataclasses import dataclass
from importlib import metadata
from pathlib import Path
from typing import Any, TextIO, cast
from urllib.parse import urlsplit

import yaml
from packaging.version import InvalidVersion, Version

from markdown_docx import __version__
from markdown_docx.errors import UsageError

SKILL_NAME = "markdown-docx"
MANAGED_BY = "markdown-docx"
MANAGED_MARKER = "<!-- managed-by: markdown-docx -->"
FORCE_INSTALL_COMMAND = "uvx markdown-docx skill install --force"
HASH_PATTERN = re.compile(r"sha256:[0-9a-f]{64}")

_SKILL_TEMPLATE = """---
name: markdown-docx
description: Create editable Word documents from strict Markdown using `uvx markdown-docx`. Use for authoring, rendering, validating, or inspecting markdown-docx sources and blank DOCX formatting templates.
metadata:
  managed-by: markdown-docx
  managed-version: {managed_version}
  managed-content-sha256: ""
---

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

Use ATX headings, paragraphs, emphasis, strong text, inline code, hard line breaks, fenced code blocks, blockquotes, lists, pipe tables, and local or remote images. Links are rejected in 0.2.0 because `python-docx` 1.2.0 does not provide public hyperlink creation. Raw HTML, task lists, footnotes, horizontal rules, indented code, multi-paragraph list items, and unsupported nested block content are rejected.

Relative image paths resolve from the Markdown file. When reading stdin, provide an output and `--base-dir`. Use `--no-remote-images` for offline or untrusted input.

## Handle results

Prefer `--json` for automation. Success includes the absolute output path, section count, template identifier, and warnings. Failures include a stable code, message, input path, and line when available. Correct the source before retrying.
"""


def _normalize(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _digest(text: str) -> str:
    return "sha256:" + hashlib.sha256(_normalize(text).encode("utf-8")).hexdigest()


def render_skill(version: str | None = None) -> str:
    """Render the single bundled skill with the exact CLI version and its integrity hash."""
    text = _normalize(_SKILL_TEMPLATE.format(managed_version=json.dumps(__version__ if version is None else version)))
    return text.replace('  managed-content-sha256: ""', f'  managed-content-sha256: "{_digest(text)}"', 1)


def default_skills_dir() -> Path:
    return Path.home() / ".agents" / "skills"


def skill_dir(skills_dir: Path | None = None) -> Path:
    return (skills_dir or default_skills_dir()) / SKILL_NAME


def runtime_source() -> str:
    """Identify installed code using distribution records, never launcher heuristics."""
    try:
        distribution = metadata.distribution(MANAGED_BY)
    except metadata.PackageNotFoundError:
        return "local"
    direct_url = distribution.read_text("direct_url.json")
    if direct_url is not None:
        try:
            origin = json.loads(direct_url)
            if not isinstance(origin, dict) or not isinstance(origin.get("url"), str):
                return "unknown"
            directory = origin.get("dir_info", {})
            if not isinstance(directory, dict):
                return "unknown"
            url = urlsplit(origin["url"])
            if directory.get("editable") or "dir_info" in origin:
                return "local"
            if url.scheme == "file" and not (
                url.path.lower().endswith(".whl") and isinstance(origin.get("archive_info"), dict)
            ):
                return "local"
            if not url.scheme:
                return "unknown"
        except (ValueError, TypeError):
            return "unknown"
    installed_module = Path(str(distribution.locate_file("markdown_docx/skill.py"))).resolve()
    if installed_module != Path(__file__).resolve():
        return "local"
    return "installed"


def _version(value: str | None) -> Version | None:
    if value is None:
        return None
    try:
        return Version(value)
    except InvalidVersion:
        return None


def _mapping(node: yaml.Node) -> dict[str, yaml.Node]:
    if not isinstance(node, yaml.MappingNode):
        raise ValueError("Skill front matter and metadata must be YAML mappings.")
    result: dict[str, yaml.Node] = {}
    for key, value in node.value:
        if not isinstance(key, yaml.ScalarNode) or key.tag != "tag:yaml.org,2002:str" or key.value in result:
            raise ValueError("Skill metadata contains a duplicate or unsupported key.")
        if value.start_mark.index < key.end_mark.index:
            raise ValueError("Skill metadata aliases are not supported.")
        result[key.value] = value
    return result


def _scalar(node: yaml.Node | None) -> str | None:
    if isinstance(node, yaml.ScalarNode) and node.tag == "tag:yaml.org,2002:str":
        return cast(str, node.value)
    return None


@dataclass(frozen=True)
class SkillState:
    content: str | None
    managed: bool = False
    managed_version: str | None = None
    version_state: str = "missing"
    integrity: str = "not_applicable"

    def relation(self, current: str) -> str:
        installed, running = _version(self.managed_version), _version(current)
        if installed is None and self.integrity == "legacy":
            installed = Version("0")
        if installed is None or running is None:
            return "unknown" if self.managed else "not_applicable"
        return "older" if installed < running else "newer" if installed > running else "equal"


def inspect_skill(content: str | None) -> SkillState:
    """Parse metadata and hash the original text using YAML source positions."""
    if content is None:
        return SkillState(None)
    normalized = _normalize(content)
    fields: dict[str, yaml.Node] = {}
    offset = 0
    opening = re.match(r"\A\ufeff?---[ \t]*\n", normalized)
    if opening is not None:
        offset = opening.end()
        end = re.search(r"^---[ \t]*(?:\n|$)", normalized[offset:], re.MULTILINE)
        if end is None:
            raise ValueError("Skill front matter is missing its closing delimiter.")
        node = yaml.compose(normalized[offset : offset + end.start()], Loader=yaml.SafeLoader)
        if node is None:
            raise ValueError("Skill front matter must be a YAML mapping.")
        root = _mapping(node)
        if "metadata" in root:
            fields = _mapping(root["metadata"])
    legacy = MANAGED_MARKER in content
    owner = _scalar(fields.get("managed-by"))
    managed = owner == MANAGED_BY or ("managed-by" not in fields and legacy)
    if not managed:
        return SkillState(content)
    raw_version = _scalar(fields.get("managed-version"))
    valid_version = raw_version if _version(raw_version) is not None else None
    version_state = "valid" if valid_version is not None else "malformed" if "managed-version" in fields else "missing"
    hash_node = fields.get("managed-content-sha256")
    stored_hash = _scalar(hash_node)
    if hash_node is None:
        integrity = "legacy" if legacy and "managed-by" not in fields and version_state == "missing" else "missing"
    elif stored_hash is None or HASH_PATTERN.fullmatch(stored_hash) is None:
        integrity = "malformed"
    else:
        start, end_index = offset + hash_node.start_mark.index, offset + hash_node.end_mark.index
        # Only a literal scalar value may be replaced. Aliases and block scalars are unverifiable.
        original_value = normalized[start:end_index]
        if original_value not in (stored_hash, f'"{stored_hash}"', f"'{stored_hash}'"):
            integrity = "malformed"
        else:
            blanked = normalized[:start] + '""' + normalized[end_index:]
            integrity = "valid" if _digest(blanked) == stored_hash else "altered"
    return SkillState(content, True, valid_version, version_state, integrity)


def _read_content(path: Path) -> str | None:
    if path.parent.is_symlink() or path.is_symlink():
        raise UsageError(f"Refusing to manage a linked skill at '{path}'.")
    if path.parent.exists() and not path.parent.is_dir():
        raise UsageError(f"Skill directory is not a directory: '{path.parent}'.")
    if path.exists() and not path.is_file():
        raise UsageError(f"SKILL.md is not a regular file: '{path}'.")
    try:
        with path.open(encoding="utf-8", newline="") as stream:
            return stream.read()
    except FileNotFoundError:
        return None


def _read_skill(path: Path) -> SkillState:
    try:
        return inspect_skill(_read_content(path))
    except (ValueError, yaml.YAMLError) as exc:
        raise UsageError(f"Cannot inspect skill at '{path}': {exc}") from exc


def _update_reason(state: SkillState, current: str) -> str:
    if _version(current) is None:
        return "invalid_cli_version"
    if state.content is None:
        return "not_installed"
    if not state.managed:
        return "unmanaged"
    if state.managed_version is None:
        return "recover_metadata"
    relation = state.relation(current)
    if relation != "older":
        return relation
    return "older_pristine" if state.integrity == "valid" else "altered_or_unverifiable"


def _atomic_replace(path: Path, content: str, previous: SkillState) -> bool:
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", newline="\n", dir=path.parent, prefix=".SKILL-", suffix=".tmp", delete=False
        ) as stream:
            temporary = Path(stream.name)
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        # Recheck the complete snapshot after writing, including ownership, version, and edits.
        if _read_skill(path).content != previous.content:
            return False
        if previous.content is None and any(entry != temporary for entry in path.parent.iterdir()):
            return False
        os.replace(temporary, path)
        return True
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def synchronize_skill(*, stderr: TextIO, version: str | None = None) -> None:
    """Best-effort local maintenance. Its failures never escape to the primary command."""
    current = __version__ if version is None else version
    try:
        if _version(current) is None or runtime_source() != "installed":
            return
        path = skill_dir() / "SKILL.md"
        state = _read_skill(path)
        reason = _update_reason(state, current)
        if reason == "altered_or_unverifiable":
            notice = f"Skill at '{path}' is altered or unverifiable. Use {FORCE_INSTALL_COMMAND}.\n"
        elif reason in {"recover_metadata", "older_pristine"} and _atomic_replace(path, render_skill(current), state):
            old = state.managed_version or ("0" if state.integrity == "legacy" else "unknown")
            notice = f"Updated managed skill {old} -> {current} at '{path}'.\n"
        else:
            return
    except Exception as exc:
        notice = f"Could not synchronize managed skill: {type(exc).__name__}.\n"
    try:
        stderr.write(notice)
    except Exception:
        pass


def skill_status(skills_dir: Path | None = None, *, version: str | None = None) -> dict[str, Any]:
    current = __version__ if version is None else version
    path = skill_dir(skills_dir) / "SKILL.md"
    state = _read_skill(path)
    source = runtime_source()
    standard = skills_dir is None or skills_dir.resolve() == default_skills_dir().resolve()
    reason = _update_reason(state, current)
    if not standard:
        reason = "custom_directory"
    elif source != "installed":
        reason = "local_development" if source == "local" else "unknown_runtime_source"
    recommendation = None
    if (
        state.managed
        and state.managed_version is not None
        and state.integrity != "valid"
        and state.relation(current) != "newer"
    ):
        recommendation = _force_command(skills_dir)
    return {
        "skill": SKILL_NAME,
        "path": str(path),
        "standard_location": standard,
        "installed": state.content is not None,
        "managed": state.managed,
        "cli_version": current,
        "managed_version": state.managed_version,
        "version_state": state.version_state,
        "version_relation": state.relation(current),
        "integrity": state.integrity,
        "automatic_sync_eligible": reason in {"recover_metadata", "older_pristine"},
        "automatic_sync_reason": reason,
        "runtime_source": source,
        "local_development": source == "local",
        "force_install_command": recommendation,
    }


def _force_command(skills_dir: Path | None) -> str:
    if skills_dir is None:
        return FORCE_INSTALL_COMMAND
    return f'{FORCE_INSTALL_COMMAND} --skills-dir "{skills_dir}"'


def install_skill(skills_dir: Path | None = None, *, force: bool = False, version: str | None = None) -> dict[str, Any]:
    current = __version__ if version is None else version
    target = skill_dir(skills_dir)
    skill_path = target / "SKILL.md"
    state = _read_skill(skill_path)
    if target.exists() and state.content is None:
        raise UsageError(f"Refusing to install into '{target}' because it contains no managed SKILL.md.")
    existed = state.content is not None
    if existed and not state.managed:
        raise UsageError(f"Refusing to overwrite unmanaged skill file '{skill_path}'.")
    canonical = render_skill(current)
    relation = state.relation(current)
    if (
        existed
        and relation != "newer"
        and state.managed_version is not None
        and state.integrity != "valid"
        and not force
    ):
        raise UsageError(
            f"Managed skill at '{skill_path}' is altered or unverifiable. Use {_force_command(skills_dir)}."
        )
    replace = (
        state.content != canonical
        and relation != "newer"
        and (not existed or state.managed_version is None or relation == "older" or force)
    )
    if replace:
        target.mkdir(parents=True, exist_ok=True)
        if not _atomic_replace(skill_path, canonical, state):
            raise UsageError(f"Skill at '{skill_path}' changed during installation. Retry the command.")
    return {
        "installed": True,
        "created": not existed,
        "updated": existed and replace,
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
    managed = _read_content(skill_path) is not None if force else _read_skill(skill_path).managed
    if not managed and not force:
        raise UsageError(f"Refusing to remove unmanaged skill '{target}'. Use --force to override.")
    extra_paths = [path for path in target.iterdir() if path.name != "SKILL.md"]
    if extra_paths and not force:
        names = ", ".join(sorted(path.name for path in extra_paths))
        raise UsageError(f"Refusing to remove '{target}' because it contains unmanaged entries: {names}. Use --force.")
    shutil.rmtree(target)
    return {"removed": True, "skill": SKILL_NAME, "path": str(target)}
