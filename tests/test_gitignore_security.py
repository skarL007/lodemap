"""Ensure local secrets are not accidentally staged in a normal checkout."""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest


@pytest.mark.parametrize(("path", "should_ignore"), [
    (".env", True),
    ("subdir/.env.production", True),
    ("certs/private.key", True),
    ("certs/private.pem", True),
    ("certs/private.p12", True),
    ("credentials.json", True),
    ("a/id_ed25519", True),
    (".env.example", False),
    ("subdir/.env.sample", False),
    ("README.md", False),
])
def test_sensitive_files_are_ignored_but_examples_are_allowed(tmp_path, path, should_ignore):
    source = Path(__file__).resolve().parents[1] / ".gitignore"
    (tmp_path / ".gitignore").write_bytes(source.read_bytes())
    init = subprocess.run(["git", "init", "-q"], cwd=tmp_path, capture_output=True, text=True)
    assert init.returncode == 0, init.stderr
    result = subprocess.run(
        ["git", "check-ignore", "-q", "--no-index", path], cwd=tmp_path,
        capture_output=True, text=True,
    )
    assert result.returncode in (0, 1), result.stderr
    assert (result.returncode == 0) == should_ignore
