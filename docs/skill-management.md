# Managed agent skill

The distribution, CLI command, and skill are named `markdown-docx`. The Python import package is `markdown_docx`. `markdown_docx.__version__` supplies the version reported by the CLI and written by the canonical skill renderer in `src/markdown_docx/skill.py`.

## Metadata

New installations write lifecycle metadata inside the existing YAML front matter:

```yaml
---
name: markdown-docx
description: Existing skill description
metadata:
  managed-by: markdown-docx
  managed-version: "0.2.0"
  managed-content-sha256: "sha256:<64 lowercase hexadecimal characters>"
---
```

The description and all instructions come from one bundled template. The version is always a quoted string with the exact running CLI version. There is no top-level version field or sidecar file. New files use UTF-8 without a BOM, LF line endings, and a trailing newline.

To calculate the hash, render the complete file with `managed-content-sha256: ""`, normalize CRLF and CR to LF, then calculate SHA-256 over the UTF-8 bytes. Replace only the hash value with `sha256:` followed by the digest. Verification blanks that value using parsed YAML source positions. It preserves the rest of the original text rather than serializing YAML again. The hash covers the instructions, examples, front matter, and formatting. It detects edits and is not a signature or security boundary.

Front matter ownership is authoritative. The old `<!-- managed-by: markdown-docx -->` marker still identifies legacy managed files when no conflicting `managed-by` field is present. New files omit that marker. Unrelated metadata in the bundled template remains part of the generated skill and its hash.

## Automatic decisions

All normal CLI invocations check `~/.agents/skills/markdown-docx/SKILL.md`, including rendering, inspection, help, version, about, and no-argument help. Skill commands do not run this check.

| Installed state | Automatic action |
| --- | --- |
| Missing directory or file | Leave absent |
| Unmanaged or owned by another tool | Leave untouched |
| Legacy managed file without a version | Treat as version 0 and replace |
| Managed file with missing or invalid version | Replace without hash verification |
| Equal or newer valid version | Leave untouched |
| Older version with matching stored hash | Replace with the running CLI's bundled skill |
| Older version with missing, malformed, or mismatched hash | Preserve and recommend force installation |

Versions use PEP 440 ordering through `packaging.version.Version`. An invalid running CLI version disables automatic synchronization. Verification compares the installed file against its own stored hash. It never compares an older file against the current bundled hash to decide whether the older file was edited.

Replacements use a flushed and closed temporary file in the skill directory followed by an atomic replacement. The installed file is read again immediately before replacement. Any observed concurrent change cancels the replacement. There is no lock or long retry loop. An external writer can still race the final filesystem operation.

Updates and preservation notices go to stderr. Failures are best effort and do not change the primary command's exit status or JSON stdout. No notice is emitted for absent, unmanaged, current, or newer skills, or skipped development builds.

## Explicit commands

```powershell
uvx markdown-docx skill install
uvx markdown-docx skill install --force
uvx markdown-docx skill status --json
uvx markdown-docx skill remove
```

A normal install creates a missing skill and updates a pristine older skill. It refuses altered or unverifiable managed files with valid versions, including edits to the current version. Use `uvx markdown-docx skill install --force` to restore such a file. Force installation still refuses unmanaged content and never replaces a newer version. Missing or invalid managed versions use the recovery rule in the table.

Status is read-only. Plain and JSON results include the selected path, standard-location flag, installation and ownership state, exact CLI version, valid installed version, version relation, integrity state, runtime source, automatic synchronization eligibility and reason, and a force command when applicable. Missing or malformed managed versions are reported as null with a separate version state. Legacy status reports legacy integrity and compares its effective version 0 before migration.

Install retains the existing `installed`, `created`, `updated`, `skill`, and `path` JSON fields. Removal retains its existing result fields and force semantics. It refuses unmanaged skills or extra directory entries unless removal `--force` is supplied. Legacy managed skills remain removable. Installation and synchronization only write `SKILL.md`. They preserve unrelated files. Existing directories without `SKILL.md` are refused by explicit install and removal.

All three commands accept `--skills-dir PATH`. Custom directories participate only in explicit commands. Include the same directory when updating or forcing a custom installation.

## Runtime source and loading

Automatic synchronization uses installed-distribution records and PEP 610 `direct_url.json`. Local directories, local source archives, and editable installations are excluded. Source code that does not match the installed distribution's module path is also excluded. Unidentified or malformed provenance is handled conservatively. An installed wheel, including one installed from a local wheel file, remains eligible. No launcher detection is used.

Explicit installation remains available from a checkout with `uvx --from . markdown-docx skill install`. Tests redirect the standard skills directory to temporary storage. The package smoke check verifies wheel provenance, runtime version, canonical content, and lifecycle behavior in an isolated temporary skill directory.

This feature only synchronizes local skill content to the CLI that is already running. It never queries PyPI, updates the CLI, or refreshes uv's cache. Agent instructions continue to invoke `uvx markdown-docx`. Updates apply to future skill loading and may not affect instructions already loaded in an active agent session.
