"""Leitor no navegador (Playwright): gaveta do sumário no celular e dica da busca vazia."""
from __future__ import annotations

from _ui_site import abrir


def _aberta(pg) -> bool:
    return pg.evaluate("document.getElementById('lateral').classList.contains('aberta')")


def test_gaveta_fecha_ao_tocar_no_item_da_pagina_atual(navegador, site):
    ctx, pg, erros = abrir(navegador, site / "leitor" / "index.html", 375, 812, "light", True)
    pg.wait_for_selector("#lateral .nav-item", state="attached")
    pg.tap("#btnSumario")
    pg.tap("#lateral .nav-item >> nth=1")          # troca de página: o hash passa a ser o do item
    pg.wait_for_timeout(300)
    pg.tap("#btnSumario")
    assert _aberta(pg)
    pg.tap("#lateral [aria-current=page]")         # mesmo hash: não há hashchange
    pg.wait_for_timeout(300)
    assert not _aberta(pg)
    assert not erros
    ctx.close()


def test_gaveta_fechada_fora_da_ordem_de_foco_e_esc_devolve_o_foco(navegador, site):
    ctx, pg, erros = abrir(navegador, site / "leitor" / "index.html", 375, 812, "light", True)
    pg.wait_for_selector("#lateral .nav-item", state="attached")
    assert pg.evaluate("getComputedStyle(document.getElementById('lateral')).visibility") == "hidden"
    assert pg.evaluate("getComputedStyle(document.getElementById('lateral')).boxShadow") == "none"
    pg.focus("#btnSumario")
    for _ in range(25):
        pg.keyboard.press("Tab")
        assert not pg.evaluate("document.activeElement.closest('#lateral') !== null")
    pg.tap("#btnSumario")
    pg.wait_for_timeout(300)
    assert pg.evaluate("document.activeElement.closest('#lateral') !== null")
    pg.keyboard.press("Escape")
    pg.wait_for_timeout(300)
    assert not _aberta(pg)
    assert pg.evaluate("document.activeElement.id") == "btnSumario"
    assert not erros
    ctx.close()


def test_itens_do_sumario_tem_alvo_de_toque_de_44px_no_celular(navegador, site):
    ctx, pg, _ = abrir(navegador, site / "leitor" / "index.html", 375, 812, "dark", True)
    pg.wait_for_selector("#lateral .nav-item", state="attached")
    pg.tap("#btnSumario")
    pg.wait_for_timeout(400)
    alturas = pg.evaluate("[...document.querySelectorAll('#lateral .nav-item')].map(e => e.getBoundingClientRect().height)")
    assert alturas and min(alturas) >= 44
    assert not pg.evaluate("document.documentElement.scrollWidth > innerWidth")
    ctx.close()


def test_busca_vazia_sugere_identificador_que_existe_no_mapa(navegador, site):
    ctx, pg, erros = abrir(navegador, site / "leitor" / "index.html", 1440, 900, "dark")
    pg.wait_for_selector("#lateral .nav-item", state="attached")
    pg.fill("#campoBusca", "zzzxxx")
    pg.wait_for_selector("#resultados code")
    exemplo = pg.inner_text("#resultados code")
    assert exemplo == "nucleo03" and "orqEscala" not in pg.inner_text("#resultados")
    pg.fill("#campoBusca", exemplo)
    pg.wait_for_selector("#resultados .res")
    assert not erros
    ctx.close()
