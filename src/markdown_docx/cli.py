from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any, NoReturn, TextIO

from markdown_docx import __version__
from markdown_docx.assets import load_syntax_payload
from markdown_docx.errors import EXIT_INTERNAL, InputError, MarkdownDocxError, UsageError
from markdown_docx.parser import parse_document
from markdown_docx.renderer import render_docx
from markdown_docx.skill import install_skill, remove_skill
from markdown_docx.template import inspect_template

PROGRAM_NAME = "markdown-docx"
PROJECT_URL = "https://github.com/pseudosavant/markdown-docx"
PROJECT_SUMMARY = "Convert constrained Markdown documents into editable Word files."
PROJECT_LICENSE = "MIT"
EXIT_CODES = (
    (0, "success"),
    (2, "usage or input error"),
    (3, "Markdown or metadata parse error"),
    (4, "template or style error"),
    (5, "image or asset error"),
    (6, "unsupported Markdown or feature"),
    (7, "DOCX rendering error"),
    (8, "unexpected internal error"),
)


class CliArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise UsageError(message)


def build_parser() -> argparse.ArgumentParser:
    parser = CliArgumentParser(prog=PROGRAM_NAME, description=PROJECT_SUMMARY, add_help=False)
    parser.add_argument("-h", "--help", action="store_true")
    parser.add_argument("input", nargs="?", help="Input Markdown path, or '-' for stdin.")
    parser.add_argument("output", nargs="?", help="Optional output .docx path.")
    parser.add_argument("--input", dest="input_flag", help="Input Markdown path, or '-' for stdin.")
    parser.add_argument("--output", dest="output_flag", help="Output .docx path.")
    parser.add_argument("--template", help="Blank DOCX formatting template.")
    parser.add_argument("--base-dir", help="Resolve stdin image paths from this directory.")
    parser.add_argument("--force", action="store_true", help="Overwrite an existing generated DOCX.")
    parser.add_argument("--no-remote-images", action="store_true", help="Reject HTTP and HTTPS images.")
    parser.add_argument("--json", action="store_true", help="Emit one structured JSON object.")
    parser.add_argument("--syntax", action="store_true", help="Show the complete input syntax.")
    parser.add_argument("--list-styles", action="store_true", help="List paragraph and character styles.")
    parser.add_argument("--list-table-styles", action="store_true", help="List table styles.")
    parser.add_argument("--inspect-template", action="store_true", help="Inspect blank-template compatibility.")
    parser.add_argument("--about", action="store_true", help="Show project metadata.")
    parser.add_argument("--version", action="store_true", help="Show the installed version.")
    return parser


def build_root_help() -> str:
    exit_lines = "\n".join(f"  {code}  {meaning}" for code, meaning in EXIT_CODES)
    return f"""{PROGRAM_NAME} {__version__}
{PROJECT_SUMMARY}

Usage:
  {PROGRAM_NAME} INPUT.md [OUTPUT.docx] [OPTIONS]
  {PROGRAM_NAME} --input - --output OUTPUT.docx --base-dir DIR [OPTIONS]

Happy path:
  {PROGRAM_NAME} document.md
  {PROGRAM_NAME} document.md output.docx --template formatting.docx

Inspection:
  {PROGRAM_NAME} --syntax [--json]
  {PROGRAM_NAME} --inspect-template [--template formatting.docx] [--json]
  {PROGRAM_NAME} --list-styles [--template formatting.docx] [--json]
  {PROGRAM_NAME} --list-table-styles [--template formatting.docx] [--json]

Agent skill:
  {PROGRAM_NAME} skill install [--skills-dir DIR] [--json]
  {PROGRAM_NAME} skill remove [--skills-dir DIR] [--force] [--json]

Common options:
  -h, --help              Show this quick reference.
  --template PATH         Use a blank DOCX formatting template.
  --base-dir PATH         Resolve relative stdin assets from PATH.
  --force                 Overwrite an existing generated DOCX.
  --no-remote-images      Reject HTTP and HTTPS images.
  --json                  Emit structured output.

Metadata:
  {PROGRAM_NAME} --about
  {PROGRAM_NAME} --version

Exit codes:
{exit_lines}

Project: {PROJECT_URL}
License: {PROJECT_LICENSE}
"""


def main(
    argv: Sequence[str] | None = None,
    *,
    stdin: TextIO | None = None,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    stdin = sys.stdin if stdin is None else stdin
    stdout = sys.stdout if stdout is None else stdout
    stderr = sys.stderr if stderr is None else stderr
    args_list = list(sys.argv[1:] if argv is None else argv)
    json_mode = "--json" in args_list
    try:
        if not args_list:
            stdout.write(build_root_help())
            return 0
        if "-h" in args_list or "--help" in args_list:
            stdout.write(build_skill_help() if args_list[0] == "skill" else build_root_help())
            return 0
        if "--version" in args_list:
            if args_list != ["--version"]:
                raise UsageError("--version cannot be combined with other arguments.")
            stdout.write(f"{PROGRAM_NAME} {__version__}\n")
            return 0
        if "--about" in args_list:
            if args_list != ["--about"]:
                raise UsageError("--about cannot be combined with other arguments.")
            stdout.write(
                f"{PROGRAM_NAME} {__version__}\n{PROJECT_SUMMARY}\nProject: {PROJECT_URL}\nLicense: {PROJECT_LICENSE}\n"
            )
            return 0
        if args_list[0] == "skill":
            return _run_skill_command(args_list[1:], stdout=stdout)
        args = build_parser().parse_args(args_list)
        return _run(args, stdin=stdin, stdout=stdout)
    except MarkdownDocxError as exc:
        _write_error(exc, json_mode=json_mode, stdout=stdout, stderr=stderr)
        return exc.context.exit_code
    except KeyboardInterrupt:
        stderr.write("interrupted: operation cancelled\n")
        return 130
    except Exception as exc:
        message = f"unexpected {type(exc).__name__}: {exc}"
        if json_mode:
            stdout.write(
                json.dumps({"ok": False, "error": {"code": "internal_error", "message": message}}, indent=2) + "\n"
            )
        else:
            stderr.write(f"internal_error: {message}\n")
        return EXIT_INTERNAL


def _run(args: argparse.Namespace, *, stdin: TextIO, stdout: TextIO) -> int:
    inspection = [
        name for name in ("syntax", "list_styles", "list_table_styles", "inspect_template") if getattr(args, name)
    ]
    if len(inspection) > 1:
        raise UsageError("Inspection modes are mutually exclusive.")
    if inspection:
        return _run_inspection(args, mode=inspection[0], stdout=stdout)

    input_arg = args.input_flag or args.input
    output_arg = args.output_flag or args.output
    if args.input_flag and args.input:
        raise UsageError("Use either positional input or --input, not both.")
    if args.output_flag and args.output:
        raise UsageError("Use either positional output or --output, not both.")
    if not input_arg:
        raise UsageError("An input Markdown file is required.")
    if input_arg == "-":
        if not output_arg:
            raise UsageError("stdin input requires an output path.")
        if not args.base_dir:
            raise UsageError("stdin input requires --base-dir for relative assets.")
        base_dir = Path(args.base_dir).resolve()
        if not base_dir.is_dir():
            raise InputError("invalid_base_dir", f"Base directory does not exist: {base_dir}", input_path=str(base_dir))
        source = stdin.read()
        input_path = None
        source_name = "<stdin>"
    else:
        if args.base_dir:
            raise UsageError("--base-dir is valid only with stdin input.")
        input_path = Path(input_arg).resolve()
        source = _read_input(input_path)
        base_dir = input_path.parent
        source_name = str(input_path)
    output_path = Path(output_arg).resolve() if output_arg else input_path.with_suffix(".docx")  # type: ignore[union-attr]
    if output_path.suffix.lower() != ".docx":
        raise UsageError("Output path must use the .docx extension.")
    if output_path.exists() and not args.force:
        raise InputError("output_exists", f"Output already exists: {output_path}", input_path=str(output_path))
    template_path = Path(args.template).resolve() if args.template else None
    model = parse_document(source, input_path=input_path, source_name=source_name)
    result = render_docx(
        model,
        output_path,
        template_path=template_path,
        base_dir=base_dir,
        allow_remote_images=not args.no_remote_images,
    )
    payload = {
        "ok": True,
        "mode": "render",
        "input": source_name,
        "template": str(template_path) if template_path else "packaged-default",
        **result,
    }
    if args.json:
        stdout.write(json.dumps(payload, indent=2) + "\n")
    else:
        stdout.write(str(output_path) + "\n")
    return 0


def _run_inspection(args: argparse.Namespace, *, mode: str, stdout: TextIO) -> int:
    allowed = {"json", mode}
    if mode != "syntax":
        allowed.add("template")
    _validate_args(args, allowed=allowed)
    if mode == "syntax":
        syntax = load_syntax_payload()
        payload = {"ok": True, "mode": "syntax", **syntax}
        plain = syntax["text"].rstrip() + "\n"
    else:
        template_path = Path(args.template).resolve() if args.template else None
        details = inspect_template(template_path)
        if mode == "list_styles":
            styles = [*details["styles"]["paragraph"], *details["styles"]["character"]]
            payload = {"ok": True, "mode": mode, "template": details["template"], "styles": styles}
            plain = "\n".join(styles) + "\n"
        elif mode == "list_table_styles":
            styles = details["styles"]["table"]
            payload = {"ok": True, "mode": mode, "template": details["template"], "styles": styles}
            plain = "\n".join(styles) + "\n"
        else:
            payload = {"ok": True, "mode": mode, **details}
            plain = _format_template_inspection(details)
    stdout.write(json.dumps(payload, indent=2) + "\n" if args.json else plain)
    return 0


def _read_input(path: Path) -> str:
    if not path.is_file():
        raise InputError("input_not_found", f"Input does not exist: {path}", input_path=str(path))
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise InputError("input_not_utf8", f"Input must be UTF-8: {path}", input_path=str(path)) from exc


def _validate_args(args: argparse.Namespace, *, allowed: set[str]) -> None:
    ignored = {"help", "about", "version"}
    for name, value in vars(args).items():
        if name in allowed or name in ignored or value in (None, False):
            continue
        raise UsageError(f"--{name.replace('_', '-')} cannot be used with this inspection mode.")


def _format_template_inspection(details: dict[str, Any]) -> str:
    status = "valid" if details["valid"] else "invalid"
    lines = [f"Template: {details['template']}", f"Blank-template contract: {status}"]
    lines.extend(f"Error: {error}" for error in details["errors"])
    for key in ("paragraph", "character", "table"):
        lines.append(f"{key.title()} styles: {len(details['styles'][key])}")
    for section in details["sections"]:
        lines.append(
            f"Section {section['index']}: {section['orientation']}, "
            f"{section['width_inches']} x {section['height_inches']} in"
        )
    return "\n".join(lines) + "\n"


def _write_error(exc: MarkdownDocxError, *, json_mode: bool, stdout: TextIO, stderr: TextIO) -> None:
    if json_mode:
        stdout.write(json.dumps({"ok": False, "error": exc.context.as_dict()}, indent=2) + "\n")
        return
    prefix = exc.context.input_path or ""
    if prefix and exc.context.line is not None:
        prefix += f":{exc.context.line}"
    if prefix:
        prefix += ": "
    stderr.write(f"{prefix}{exc.context.code}: {exc.context.message}\n")


def build_skill_help() -> str:
    return f"""Usage:
  {PROGRAM_NAME} skill install [--skills-dir DIR] [--json]
  {PROGRAM_NAME} skill remove [--skills-dir DIR] [--force] [--json]

Install or remove the managed `{PROGRAM_NAME}` agent skill. The default root is ~/.agents/skills.
Removal refuses unmanaged content unless --force is supplied.
"""


def _run_skill_command(args_list: list[str], *, stdout: TextIO) -> int:
    parser = CliArgumentParser(prog=f"{PROGRAM_NAME} skill", add_help=False)
    parser.add_argument("action", choices=("install", "remove"))
    parser.add_argument("--skills-dir", type=Path)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(args_list)
    if args.action == "install" and args.force:
        raise UsageError("--force is valid only with 'skill remove'.")
    root = args.skills_dir.resolve() if args.skills_dir else None
    result = install_skill(root) if args.action == "install" else remove_skill(root, force=args.force)
    if args.json:
        stdout.write(json.dumps({"ok": True, "mode": f"skill_{args.action}", **result}, indent=2) + "\n")
    elif args.action == "install":
        verb = "Installed" if result["created"] else "Updated" if result["updated"] else "Already installed"
        stdout.write(f"{verb} {result['path']}\n")
    elif result["removed"]:
        stdout.write(f"Removed {result['path']}\n")
    else:
        stdout.write(f"Skill is not installed at {result['path']}\n")
    return 0
