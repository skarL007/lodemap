"""Explorador no navegador (Playwright), sobre um mapa sintético gerado pelos geradores reais (`_ui_site.py`)."""
from __future__ import annotations

import pytest

from _ui_site import abrir


def _pronto(pg):
    pg.wait_for_function("window.cytoscape && document.querySelector('#cy canvas') && !document.getElementById('carregando').offsetParent")
    pg.wait_for_timeout(500)


def _sem_overflow(pg):
    return not pg.evaluate("document.documentElement.scrollWidth > innerWidth")


@pytest.mark.parametrize("largura,altura,toque", [(375, 812, True), (1440, 900, False)])
def test_aviso_da_saude_cabe_na_tela_some_sozinho_e_a_ressalva_fica_na_legenda(navegador, site, largura, altura, toque):
    ctx, pg, erros = abrir(navegador, site / "explorador" / "index.html", largura, altura, "dark", toque)
    _pronto(pg)
    if toque:
        pg.tap("#btnPainel")
        pg.wait_for_timeout(400)
    pg.click("text=Saúde dos componentes")
    pg.wait_for_selector("#aviso:not([hidden])")
    caixa = pg.evaluate("(() => { const b = document.getElementById('aviso').getBoundingClientRect(); return [b.left, b.right, innerWidth]; })()")
    assert caixa[0] >= 0 and caixa[1] <= caixa[2], caixa
    pg.wait_for_function("document.getElementById('aviso').hidden", timeout=9000)       # item 5: o aviso não fica para sempre
    pg.evaluate("document.getElementById('legendaCaixa').open = true")
    assert "não execução" in pg.inner_text("#legenda")                                  # a ressalva continua na Legenda
    assert _sem_overflow(pg)
    assert not [e for e in erros if "local.json" not in e and "404" not in e], erros
    ctx.close()


def _visao(pg) -> str:
    return pg.evaluate("document.querySelector('#listaVisoes .item.ativo').innerText")


def test_trocar_de_visao_empilha_historico_e_voltar_volta_a_visao_anterior(navegador, site):
    ctx, pg, erros = abrir(navegador, site / "explorador" / "index.html", 1440, 900, "dark")
    _pronto(pg)
    inicio = pg.evaluate("history.length")
    pg.click("#listaVisoes .item >> nth=1")
    pg.wait_for_function("document.querySelector('#listaVisoes .item.ativo') && document.querySelector('#listaVisoes .item.ativo').innerText !== ''")
    primeira, hash1 = _visao(pg), pg.evaluate("location.hash")
    pg.click("#listaVisoes .item >> nth=2")
    pg.wait_for_function("h => location.hash !== h", arg=hash1)
    segunda, hash2 = _visao(pg), pg.evaluate("location.hash")
    assert primeira != segunda and pg.evaluate("history.length") >= inicio + 2
    pg.go_back()
    pg.wait_for_function("h => location.hash === h", arg=hash1)
    pg.wait_for_function("p => document.querySelector('#listaVisoes .item.ativo').innerText === p", arg=primeira)
    pg.go_forward()
    pg.wait_for_function("h => location.hash === h", arg=hash2)
    pg.wait_for_function("p => document.querySelector('#listaVisoes .item.ativo').innerText === p", arg=segunda)
    assert not [e for e in erros if "local.json" not in e and "404" not in e], erros
    ctx.close()


def test_linha_do_tempo_tem_rota_propria_e_fecha_ao_escolher_visao_ou_esc(navegador, site):
    ctx, pg, erros = abrir(navegador, site / "explorador" / "index.html", 1440, 900, "dark")
    _pronto(pg)
    painel = "document.getElementById('timelinePanel').hidden"
    pg.click("#tlAbrir")
    pg.wait_for_selector("#tlTrilho button")
    assert pg.evaluate("location.hash") == "#linha-do-tempo" and not pg.evaluate(painel)
    pg.reload()                                              # a rota reabre o painel
    pg.wait_for_selector("#tlTrilho button")
    assert not pg.evaluate(painel)
    pg.click("#listaVisoes .item >> nth=1")                  # escolher visão fecha o painel
    pg.wait_for_function(painel)
    assert pg.evaluate("location.hash") != "#linha-do-tempo"
    pg.go_back()                                             # Voltar devolve o painel
    pg.wait_for_function("!" + painel)
    pg.keyboard.press("Escape")                              # Esc fecha o painel e devolve o hash do mapa
    pg.wait_for_function(painel)
    assert pg.evaluate("location.hash") != "#linha-do-tempo"
    assert _sem_overflow(pg)
    assert not [e for e in erros if "local.json" not in e and "404" not in e], erros
    ctx.close()


@pytest.mark.parametrize("largura,altura,toque,tema", [(375, 812, True, "light"), (1440, 900, False, "dark")])
def test_linha_do_tempo_grafo_legivel_dagre_e_cores_seguem_o_tema(navegador, site, largura, altura, toque, tema):
    ctx, pg, erros = abrir(navegador, site / "explorador" / "index.html", largura, altura, tema, toque)
    pg.goto((site / "explorador" / "index.html").as_uri() + "#linha-do-tempo")
    pg.reload()
    pg.wait_for_selector("#tlTrilho button")
    pg.wait_for_timeout(800)
    assert _sem_overflow(pg)
    assert pg.evaluate("document.querySelector('#tlGrafo canvas') !== null")
    assert "linha-do-tempo" in pg.evaluate("location.hash")
    assert not [e for e in erros if "local.json" not in e and "404" not in e], erros
    ctx.close()


def test_mapa_grande_para_no_zoom_legivel_e_avisa_que_o_resto_se_alcanca_arrastando(navegador, site):
    ctx, pg, erros = abrir(navegador, site / "explorador" / "index.html", 375, 812, "light", True)
    _pronto(pg)
    pg.evaluate("document.querySelector('#listaVisoes .item').click()")      # "Modelo inteiro": dezenas de componentes
    pg.wait_for_selector("#aviso:not([hidden])")
    assert "mínimo legível" in pg.inner_text("#aviso")
    caixa = pg.evaluate("(() => { const b = document.getElementById('aviso').getBoundingClientRect(); return [b.left, b.right, innerWidth]; })()")
    assert caixa[0] >= 0 and caixa[1] <= caixa[2], caixa
    assert _sem_overflow(pg)
    assert not [e for e in erros if "local.json" not in e and "404" not in e], erros
    ctx.close()


def test_inspetor_da_ligacao_nao_repete_o_rotulo_e_deixa_as_pontas_acima_da_folha(navegador, site):
    ctx, pg, erros = abrir(navegador, site / "explorador" / "index.html", 375, 812, "dark", True)
    _pronto(pg)
    pg.evaluate("[...document.querySelectorAll('#listaVisoes .item')].find(b => b.textContent.includes('Núcleo: componentes')).click()")   # visão com ligações
    pg.wait_for_timeout(600)
    pg.evaluate("(() => { const cy = document.getElementById('cy')._cyreg.cy; cy.edges(':visible')[0].emit('tap'); })()")
    pg.wait_for_function("document.getElementById('rotInspetor').textContent === 'Ligação'")
    pg.wait_for_timeout(600)
    assert pg.evaluate("[...document.querySelectorAll('#dir .det-tipo')].filter(e => e.textContent.trim() === 'Ligação').length") == 1
    r = pg.evaluate("""(() => { const cy = document.getElementById('cy')._cyreg.cy, topo = document.getElementById('dir').getBoundingClientRect().top;
        const base = document.getElementById('cy').getBoundingClientRect().top;
        return { pontas: cy.edges(':visible')[0].connectedNodes().map(n => n.renderedBoundingBox().y2 + base), topo }; })()""")
    assert all(y <= r["topo"] for y in r["pontas"]), r                                 # as duas pontas ficam acima da folha
    assert not [e for e in erros if "local.json" not in e and "404" not in e], erros
    ctx.close()


def test_rotulos_de_ligacao_do_foco_nao_se_sobrepoem(navegador, site):
    ctx, pg, erros = abrir(navegador, site / "explorador" / "index.html", 1440, 900, "dark")
    _pronto(pg)
    pg.click("#listaVisoes .item:has-text('Tudo junto')")
    pg.wait_for_timeout(600)
    pg.evaluate("(() => { const cy = document.getElementById('cy')._cyreg.cy; cy.nodes().filter(n => n.data('label') === 'Núcleo 01')[0].emit('tap'); })()")
    pg.wait_for_timeout(1500)
    r = pg.evaluate("""(() => { const cy = document.getElementById('cy')._cyreg.cy;
        const so = { includeNodes: false, includeEdges: false, includeLabels: true, includeOverlays: false };
        const eds = cy.edges('.vizinho, .caminho'), com = eds.filter(e => !e.hasClass('sem-rotulo')), bs = com.map(e => e.boundingBox(so));
        let sobre = 0;
        for (let i = 0; i < bs.length; i++) for (let j = i + 1; j < bs.length; j++) {
          const a = bs[i], b = bs[j]; if (a.x1 < b.x2 && a.x2 > b.x1 && a.y1 < b.y2 && a.y2 > b.y1) sobre++; }
        return { arestas: eds.length, comRotulo: com.length, sobre }; })()""")
    assert r["arestas"] >= 2 and r["comRotulo"] >= 1 and r["sobre"] == 0, r
    assert not [e for e in erros if "local.json" not in e and "404" not in e], erros
    ctx.close()


def test_toque_sem_atalho_de_teclado_e_legenda_com_alvo_de_44px(navegador, site):
    ctx, pg, erros = abrir(navegador, site / "explorador" / "index.html", 375, 812, "light", True)
    _pronto(pg)
    assert not pg.is_visible("#kbdPaleta")                                        # "Ctrl K" não aparece no toque
    assert pg.is_visible("#btnPaleta")                                            # a paleta continua ao alcance
    assert pg.evaluate("document.querySelector('#legendaCaixa summary').getBoundingClientRect().height") >= 44
    assert _sem_overflow(pg)
    ctx.close()
    ctx, pg, _ = abrir(navegador, site / "explorador" / "index.html", 1440, 900, "light")
    _pronto(pg)
    assert pg.is_visible("#kbdPaleta")                                            # no desktop o atalho continua
    ctx.close()


@pytest.mark.parametrize("lang,saude,tl_botao,tl_painel", [("en", "Health · evidence", "Timeline", "Back to the map"),
                                                          ("pt", "Saúde · evidências", "Linha do tempo", "Voltar ao mapa")])
def test_saude_e_linha_do_tempo_seguem_o_idioma_da_pagina(navegador, site, lang, saude, tl_botao, tl_painel):
    ctx, pg, erros = abrir(navegador, site / "explorador" / "index.html", 1440, 900, "dark")
    pg.goto((site / "explorador" / "index.html").as_uri() + f"?lang={lang}")
    _pronto(pg)
    pg.click("[data-i18n=saudeBotao]")                       # carrega as evidências
    pg.wait_for_selector("#aviso:not([hidden])")
    pg.evaluate("location.hash = '#nucleo01'")
    pg.wait_for_function("document.getElementById('detalhes').innerText.toLowerCase().includes('%s')" % saude.lower())
    assert pg.inner_text("#tlAbrir") == tl_botao
    pg.click("#tlAbrir")
    pg.wait_for_selector("#tlTrilho button")
    assert tl_painel in pg.inner_text("#timelinePanel")
    assert not [e for e in erros if "local.json" not in e and "404" not in e], erros
    ctx.close()


# ---------------------------------------------------------------- polimento 3: itens 12 (celular), 13 (rótulos) e 18 (datas)

def _abrir_visao(pg, titulo: str):
    pg.evaluate("t => [...document.querySelectorAll('#listaVisoes .item, #listaFluxos .item')]"
                ".find(b => b.textContent.trim().startsWith(t)).click()", titulo)
    pg.wait_for_timeout(900)


def _quadro(pg):
    """Caixas (em coordenadas da janela) dos nós visíveis e das caixas flutuantes, mais o zoom do grafo."""
    return pg.evaluate("""(() => { const cy = document.getElementById('cy')._cyreg.cy, base = document.getElementById('cy').getBoundingClientRect();
        const caixa = id => { const e = document.getElementById(id); if (!e || !e.offsetParent) return null; const r = e.getBoundingClientRect();
          return { x1: r.left, y1: r.top, x2: r.right, y2: r.bottom }; };
        const nos = cy.nodes(':visible').filter(n => !n.data('grupo')).map(n => { const b = n.renderedBoundingBox({ includeLabels: false });
          return { nome: n.data('label'), x1: b.x1 + base.left, y1: b.y1 + base.top, x2: b.x2 + base.left, y2: b.y2 + base.top }; });
        return { zoom: cy.zoom(), nos, caixas: { titulo: caixa('tituloVisao'), legenda: caixa('legendaCaixa'), ferramentas: caixa('ferramentas') },
                 largura: innerWidth, altura: innerHeight, tela: { x1: base.left, y1: base.top, x2: base.right, y2: base.bottom } }; })()""")


def _cobre(n, c):
    return bool(c) and n["x1"] < c["x2"] and n["x2"] > c["x1"] and n["y1"] < c["y2"] and n["y2"] > c["y1"]


@pytest.mark.parametrize("tema", ["light", "dark"])
def test_celular_visao_pequena_cabe_inteira_legivel_e_fora_das_caixas_flutuantes(navegador, site, tema):
    """Item 12: 4 pontas num mesmo nível não podem virar texto de 6 px nem nó cortado, coberto pelo título ou pela Legenda."""
    ctx, pg, erros = abrir(navegador, site / "explorador" / "index.html", 375, 812, tema, True)
    _pronto(pg)
    for titulo in ("Hub: adaptadores", "Containers"):
        _abrir_visao(pg, titulo)
        q = _quadro(pg)
        assert len(q["nos"]) >= 4, (titulo, q["nos"])
        assert 12 * q["zoom"] >= 10, (titulo, q["zoom"])                                  # texto de 10 px CSS ou mais
        t = q["tela"]
        for n in q["nos"]:
            assert n["x1"] >= t["x1"] - 1 and n["x2"] <= t["x2"] + 1 and n["y1"] >= t["y1"] - 1 and n["y2"] <= t["y2"] + 1, (titulo, n)
            for nome, c in q["caixas"].items():
                assert not _cobre(n, c), (titulo, n, nome, c)
        # dentro da faixa livre entre o título (topo) e a Legenda (base)
        livre_topo = max(c["y2"] for c in (q["caixas"]["titulo"], q["caixas"]["ferramentas"]) if c)
        livre_base = q["caixas"]["legenda"]["y1"]
        assert min(n["y1"] for n in q["nos"]) >= livre_topo and max(n["y2"] for n in q["nos"]) <= livre_base, (titulo, q["nos"])
    assert _sem_overflow(pg)
    assert not [e for e in erros if "local.json" not in e and "404" not in e], erros
    ctx.close()


def test_celular_fluxo_com_titulo_e_legenda_nao_cobre_o_primeiro_passo(navegador, site):
    ctx, pg, erros = abrir(navegador, site / "explorador" / "index.html", 375, 812, "dark", True)
    _pronto(pg)
    _abrir_visao(pg, "Fluxo B")
    pg.evaluate("document.getElementById('passoProx').click()")                          # acende o 1º passo
    pg.wait_for_timeout(700)
    q = _quadro(pg)
    passo = pg.evaluate("""(() => { const cy = document.getElementById('cy')._cyreg.cy, base = document.getElementById('cy').getBoundingClientRect();
        return cy.nodes('.passo').map(n => { const r = n.renderedBoundingBox({ includeLabels: false });
          return { x1: r.x1 + base.left, y1: r.y1 + base.top, x2: r.x2 + base.left, y2: r.y2 + base.top }; }); })()""")
    assert passo, "o primeiro passo do fluxo fica destacado"
    for n in passo:
        for nome, c in q["caixas"].items():
            assert not _cobre(n, c), (n, nome, c)
    ctx.close()


def test_rotulos_de_ligacao_ficam_horizontais_com_fundo_e_o_grafo_nao_passa_sob_o_inspetor(navegador, site):
    """Item 13: sem `autorotate`, com fundo opaco, sem cair sobre outro nó e com o enquadre contando a largura do inspetor."""
    ctx, pg, erros = abrir(navegador, site / "explorador" / "index.html", 1440, 900, "dark")
    _pronto(pg)
    _abrir_visao(pg, "Hub: adaptadores")
    pg.evaluate("(() => { const cy = document.getElementById('cy')._cyreg.cy; cy.nodes().filter(n => n.data('label') === 'Núcleo 01')[0].emit('tap'); })()")
    pg.wait_for_timeout(1500)
    r = pg.evaluate("""(() => { const cy = document.getElementById('cy')._cyreg.cy, base = document.getElementById('cy').getBoundingClientRect();
        const dir = document.getElementById('dir').getBoundingClientRect();
        const so = { includeNodes: false, includeEdges: false, includeLabels: true, includeOverlays: false };
        const bate = (a, b) => a.x1 < b.x2 && a.x2 > b.x1 && a.y1 < b.y2 && a.y2 > b.y1;
        const eds = cy.edges('.vizinho, .caminho'), nos = cy.nodes(':visible').filter(n => !n.data('grupo'));
        const com = eds.filter(e => !e.hasClass('sem-rotulo'));
        const sobreNo = com.filter(e => nos.some(n => n.id() !== e.source().id() && n.id() !== e.target().id() && bate(e.boundingBox(so), n.boundingBox({ includeLabels: false })))).length;
        const foco = cy.elements('.foco, .vizinho').nodes().map(n => n.renderedBoundingBox({ includeLabels: false }));
        return { arestas: eds.length, comRotulo: com.length, sobreNo,
                 rotacao: [...new Set(cy.edges().map(e => e.pstyle('text-rotation').strValue))],
                 fundo: [...new Set(cy.edges().map(e => e.pstyle('text-background-opacity').value))],
                 minFonte: cy.edges()[0].pstyle('min-zoomed-font-size').pfValue,
                 direita: Math.max(...foco.map(b => b.x2 + base.left)), esquerda: Math.min(...foco.map(b => b.x1 + base.left)),
                 inspetorEsq: dir.left, canvasEsq: base.left }; })()""")
    assert r["arestas"] >= 3 and r["comRotulo"] >= 1 and r["sobreNo"] == 0, r
    assert r["rotacao"] == ["none"] and r["fundo"] == [1], r                         # horizontal, fundo da cor da superfície
    assert r["minFonte"] >= 8, r                                                       # sem texto de 3 px: abaixo disso o rótulo some
    assert r["direita"] <= r["inspetorEsq"] and r["esquerda"] >= r["canvasEsq"], r     # nada atrás do inspetor
    assert not [e for e in erros if "local.json" not in e and "404" not in e], erros
    ctx.close()


def test_rotulo_de_ligacao_escondido_por_zoom_baixo_aparece_ao_passar_o_mouse(navegador, site):
    ctx, pg, erros = abrir(navegador, site / "explorador" / "index.html", 1440, 900, "light")
    _pronto(pg)
    _abrir_visao(pg, "Hub: adaptadores")
    pg.evaluate("(() => { const cy = document.getElementById('cy')._cyreg.cy; cy.nodes().filter(n => n.data('label') === 'Núcleo 01')[0].emit('tap'); cy.zoom(0.3); })()")
    pg.wait_for_timeout(400)
    r = pg.evaluate("""(() => { const cy = document.getElementById('cy')._cyreg.cy, e = cy.edges('.vizinho')[0];
        const antes = e.pstyle('min-zoomed-font-size').pfValue; e.emit('mouseover');
        const durante = e.pstyle('min-zoomed-font-size').pfValue, rot = e.pstyle('label').strValue; e.emit('mouseout');
        return { antes, durante, rot, depois: e.pstyle('min-zoomed-font-size').pfValue }; })()""")
    assert r["antes"] >= 8 and r["durante"] == 0 and r["rot"] and r["depois"] == r["antes"], r
    ctx.close()


@pytest.mark.parametrize("largura,altura,toque", [(375, 812, True), (1440, 900, False)])
def test_linha_do_tempo_mostra_a_data_da_release_e_a_do_mapa_como_secundaria(navegador, site, largura, altura, toque):
    """Item 18: as versões saem todas no mesmo dia (a do mapa); cada uma tem a data da sua tag."""
    ctx, pg, erros = abrir(navegador, site / "explorador" / "index.html", largura, altura, "dark", toque)
    _pronto(pg)
    pg.evaluate("document.getElementById('tlAbrir').click()")
    pg.wait_for_selector("#tlTrilho button")
    botoes = pg.evaluate("[...document.querySelectorAll('#tlTrilho .tl-versao')].map(b => [...b.querySelectorAll('span')].map(s => s.textContent.trim()))")
    assert botoes == [["release 2026-10-01", "mapa 2026-11-10"], ["release 2026-10-15", "mapa 2026-11-10"],
                      ["release 2026-11-05", "mapa 2026-11-10"]], botoes
    assert pg.evaluate("document.querySelector('#tlTrilho .tl-mapa') !== null")
    assert _sem_overflow(pg)
    ctx.close()


def test_linha_do_tempo_sem_data_tag_continua_mostrando_so_a_data_do_mapa(navegador, site, tmp_path):
    """Arquivos antigos (sem `data_tag`) e versões sem tag: só a data do mapa, sem rótulo."""
    import re
    import shutil
    copia = tmp_path / "antigo"
    shutil.copytree(site / "explorador", copia)
    js = copia / "linha-do-tempo.js"
    js.write_text(re.sub(r'"data_tag": ?(?:"[^"]*"|null),? ?', "", js.read_text(encoding="utf-8")), encoding="utf-8")
    assert "data_tag" not in js.read_text(encoding="utf-8")
    ctx, pg, erros = abrir(navegador, copia / "index.html", 1440, 900, "light")
    _pronto(pg)
    pg.evaluate("document.getElementById('tlAbrir').click()")
    pg.wait_for_selector("#tlTrilho button")
    botoes = pg.evaluate("[...document.querySelectorAll('#tlTrilho .tl-versao')].map(b => [...b.querySelectorAll('span')].map(s => s.textContent.trim()))")
    assert botoes == [["2026-11-10"]] * 3, botoes
    assert not [e for e in erros if "local.json" not in e and "404" not in e], erros
    ctx.close()
