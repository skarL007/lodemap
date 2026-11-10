from __future__ import annotations

import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
for p in (RAIZ, RAIZ / "hooks"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))


@pytest.fixture
def home(tmp_path, monkeypatch):
    """HOME e ~/.config/lodemap temporários: nada toca o ~/.claude real."""
    h = tmp_path / "home"
    (h / ".claude").mkdir(parents=True)
    monkeypatch.setenv("HOME", str(h))
    monkeypatch.setenv("USERPROFILE", str(h))
    monkeypatch.setenv("LODEMAP_CONFIG_DIR", str(h / ".config" / "lodemap"))
    return h
