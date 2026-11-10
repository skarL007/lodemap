"""Barra comum ({{ARQ_REL}}): explorador e leitor têm a mesma navegação, o mesmo CSS e o mesmo JS.

Os blocos ``<!-- lodemap:barra:start/end -->`` (marca, seções e menu compacto), ``<!-- lodemap:barra-fim:start/end -->``
(tema e script) e ``/* lodemap:barra:css:start/end */`` precisam ser idênticos nas duas páginas; entre os dois blocos
de marcação fica a busca da página (a ordem do DOM é a ordem visual, para o Tab). A navegação é
Mapa | Documentação | Decisões, com links relativos dentro da pasta da arquitetura, e cada página
declara qual seção está ativa (``data-lm-pagina`` no ``<body>``).
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
ARQ = ROOT / "{{ARQ_REL}}"
PAGINAS = {"explorador": "mapa", "leitor": "docs"}
NAV = [("mapa", "Mapa", "../explorador/index.html"), ("docs", "Documentação", "../leitor/index.html"),
       ("decisoes", "Decisões", "../leitor/index.html#decisoes")]


def _html(pagina: str) -> str:
    return (ARQ / pagina / "index.html").read_text(encoding="utf-8")


def _bloco(texto: str, ini: str, fim: str) -> str:
    assert ini in texto and fim in texto, f"faltam os marcadores {ini} ... {fim}"
    return texto[texto.index(ini):texto.index(fim) + len(fim)]


@pytest.mark.parametrize("ini,fim", [("<!-- lodemap:barra:start -->", "<!-- lodemap:barra:end -->"),
                                     ("<!-- lodemap:barra-fim:start -->", "<!-- lodemap:barra-fim:end -->"),
                                     ("/* lodemap:barra:css:start */", "/* lodemap:barra:css:end */")])
def test_bloco_identico_nas_duas_paginas(ini, fim):
    blocos = {p: _bloco(_html(p), ini, fim) for p in PAGINAS}
    base = blocos["explorador"]
    diferentes = [p for p, b in blocos.items() if b != base]
    assert not diferentes, f"o bloco {ini} difere em {diferentes}; copie o mesmo bloco nas duas páginas"


def test_navegacao_na_ordem_com_links_relativos():
    html = _html("explorador")
    barra = (_bloco(html, "<!-- lodemap:barra:start -->", "<!-- lodemap:barra:end -->")
             + _bloco(html, "<!-- lodemap:barra-fim:start -->", "<!-- lodemap:barra-fim:end -->"))
    nav = re.search(r'<nav class="lm-nav"[^>]*>(.*?)</nav>', barra, re.S)
    assert nav, "falta <nav class=\"lm-nav\">"
    links = re.findall(r'<a href="([^"]+)" data-lm-href="([^"]+)" data-lm="([^"]+)">([^<]+)</a>', nav.group(1))
    assert [(c, r, h) for h, _, c, r in links] == NAV
    assert all(h == dh for h, dh, _, _ in links)
    assert 'aria-controls="lmNav"' in barra and 'aria-expanded="false"' in barra, "menu compacto acessível"
    assert 'id="lmTema"' in barra and "window.LodemapBarra" in barra


@pytest.mark.parametrize("pagina,chave", PAGINAS.items())
def test_cada_pagina_declara_a_secao_ativa(pagina, chave):
    html = _html(pagina)
    assert f'<body class="sds" data-lm-pagina="{chave}">' in html
    cab = html[html.index('<header class="sds-bar lm-barra">'):html.index("</header>")]
    ordem = [cab.find(x) for x in ("<!-- lodemap:barra:start -->", "lm-busca", "<!-- lodemap:barra-fim:start -->")]
    assert -1 not in ordem and ordem == sorted(ordem), "no <header>: bloco da barra, a busca da página e o bloco do fim"
    assert cab.rstrip().endswith("<!-- lodemap:barra-fim:end -->"), "o bloco do fim (tema e script) fecha o <header>"
    assert ":focus-visible" in _bloco(html, "/* lodemap:barra:css:start */", "/* lodemap:barra:css:end */")


def test_leitor_marca_decisoes_pela_ancora():
    html = _html("leitor")
    assert 'LodemapBarra.ativar(base === "decisoes" || /^adr-/.test(base) ? "decisoes" : "docs")' in html
