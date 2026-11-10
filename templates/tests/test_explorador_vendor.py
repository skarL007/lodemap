"""Explorador sem CDN: as bibliotecas vêm de explorador/vendor/ (MIT, com licença) e nada aponta para fora."""
from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
EXPLORADOR = ROOT / "{{ARQ_REL}}" / "explorador"
BIBLIOTECAS = {
    "cytoscape.min.js": ("LICENSE-cytoscape.txt", "3.30.2"),
    "dagre.min.js": ("LICENSE-dagre.txt", "0.8.5"),
    "cytoscape-dagre.js": ("LICENSE-cytoscape-dagre.txt", None),
}


def _html() -> str:
    return (EXPLORADOR / "index.html").read_text(encoding="utf-8")


@pytest.mark.parametrize("arquivo", sorted(BIBLIOTECAS))
def test_biblioteca_embutida_com_licenca_mit(arquivo):
    licenca, versao = BIBLIOTECAS[arquivo]
    js = EXPLORADOR / "vendor" / arquivo
    assert js.is_file() and js.stat().st_size > 5000, f"falta vendor/{arquivo}"
    texto_licenca = (EXPLORADOR / "vendor" / licenca).read_text(encoding="utf-8")
    assert "Permission is hereby granted, free of charge" in texto_licenca
    if versao:
        assert versao in js.read_text(encoding="utf-8", errors="replace")
    assert f'<script src="vendor/{arquivo}"></script>' in _html()


def test_nenhum_recurso_externo_no_index():
    html = _html()
    externos = re.findall(r"""(?:src|href)\s*=\s*["'](?:https?:)?//[^"']+""", html)
    assert not externos, externos
    assert "cdnjs" not in html and "jsdelivr" not in html and "unpkg" not in html


def test_sem_player_nem_structurizr_lite():
    html = _html()
    for proibido in ('id="tocar"', 'id="velocidade"', "animarCamadas", "setInterval", 'id="lnkLite"', 'id="modal"', 'id="layout"'):
        assert proibido not in html, proibido
    for exigido in ('id="paleta"', 'role="dialog"', 'id="colorir"', 'id="btnReorganizar"', "#fluxo/", "../leitor/index.html"):
        assert exigido in html, exigido
