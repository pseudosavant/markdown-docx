"""Check packaged skill behavior without accessing the user's skills directory."""

from __future__ import annotations

import argparse
import io
import json
import tempfile
from importlib.metadata import version
from pathlib import Path
from unittest.mock import patch

from markdown_docx import __version__, skill
from markdown_docx.cli import main


def invoke(args: list[str]) -> tuple[str, str]:
    stdout, stderr = io.StringIO(), io.StringIO()
    code = main(args, stdout=stdout, stderr=stderr)
    assert code == 0, (code, stdout.getvalue(), stderr.getvalue())
    return stdout.getvalue(), stderr.getvalue()


def check(expected_source: str) -> None:
    assert skill.runtime_source() == expected_source
    assert version("markdown-docx") == __version__
    with tempfile.TemporaryDirectory(prefix="markdown-docx-skill-smoke-") as directory:
        root = Path(directory) / "skills"
        with patch.object(skill, "default_skills_dir", return_value=root):
            stdout, stderr = invoke(["--version"])
            assert stdout == f"markdown-docx {__version__}\n" and not stderr
            assert not root.exists()
            stdout, stderr = invoke(["skill", "install", "--json"])
            installed = json.loads(stdout)
            assert installed["created"] and not stderr
            path = Path(installed["path"])
            canonical = path.read_bytes()
            assert canonical == skill.render_skill().encode("utf-8")
            assert b"Always invoke the tool as `uvx markdown-docx ...`" in canonical
            assert list(path.parent.iterdir()) == [path]
            stdout, stderr = invoke(["skill", "status", "--json"])
            status = json.loads(stdout)
            assert status["managed_version"] == __version__
            assert status["integrity"] == "valid" and not stderr
            assert status["local_development"] == (expected_source == "local")
            older = skill.render_skill("0.0.0").encode("utf-8")
            path.write_bytes(older)
            stdout, stderr = invoke(["--syntax", "--json"])
            assert json.loads(stdout)["ok"]
            if expected_source == "installed":
                assert "Updated managed skill" in stderr
                assert path.read_bytes() == canonical
            else:
                assert not stderr
                assert path.read_bytes() == older
            altered = older + b"Local edits\n"
            path.write_bytes(altered)
            stdout, stderr = invoke(["--syntax", "--json"])
            assert json.loads(stdout)["ok"]
            assert path.read_bytes() == altered
            if expected_source == "installed":
                assert skill.FORCE_INSTALL_COMMAND in stderr
            else:
                assert not stderr
            stdout, stderr = invoke(["skill", "install", "--force", "--json"])
            assert json.loads(stdout)["updated"] and not stderr
            assert path.read_bytes() == canonical
            stdout, stderr = invoke(["skill", "remove", "--json"])
            assert json.loads(stdout)["removed"] and not stderr
            assert not path.exists()
    print(f"Managed skill smoke passed for {expected_source} runtime {__version__}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected-source", choices=("installed", "local"), default="installed")
    check(parser.parse_args().expected_source)
