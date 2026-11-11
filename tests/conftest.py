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


@pytest.fixture(autouse=True)
def _idioma_pt(monkeypatch):
    """Os testes não dependem do idioma da máquina: o padrão é pt (os textos esperados são em português).

    Testes de inglês fazem monkeypatch.setenv("LODEMAP_IDIOMA", "en") por conta própria.
    """
    monkeypatch.setenv("LODEMAP_IDIOMA", "pt")
    from lodemap import idioma
    idioma.usar_mapa(None)


# Fixtures de sessão do Playwright vivem aqui, uma única vez: importadas em dois módulos, cada um criaria o seu
# `sync_playwright()` e o segundo falharia com "Sync API inside the asyncio loop".
from _ui_site import navegador, site  # noqa: E402,F401
