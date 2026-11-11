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


# ---------------------------------------------------------------- polimento 4: itens 9, 12, 13, 14 e 19

# Interseções aresta x nó: o segmento reto entre as pontas e o caminho que o Cytoscape realmente desenha (a bezier lida
# de `rscratch.allpts`), contra a caixa de cada nó que não é ponta da aresta (encolhida 2 px). `sel` é o id do container.
_INTERSECOES = """(sel => { const cy = document.getElementById(sel)._cyreg.cy;
  const nos = cy.nodes(':visible').filter(n => !n.data('grupo'));
  const bate = (p, q, b) => { let t0 = 0, t1 = 1; const dx = q.x - p.x, dy = q.y - p.y;
    for (const [pp, qq] of [[-dx, p.x - b.x1], [dx, b.x2 - p.x], [-dy, p.y - b.y1], [dy, b.y2 - p.y]]) {
      if (pp === 0) { if (qq < 0) return false; } else { const r = qq / pp; if (pp < 0) { if (r > t1) return false; if (r > t0) t0 = r; } else { if (r < t0) return false; if (r < t1) t1 = r; } } }
    return t0 < t1; };
  const encolhe = (b, k) => ({ x1: b.x1 + k, y1: b.y1 + k, x2: b.x2 - k, y2: b.y2 - k });
  const poli = e => { const r = e._private.rscratch, a = r.allpts, pts = []; if (!a || a.length < 4) return null;
    if ((r.edgeType === 'bezier' || r.edgeType === 'multibezier') && a.length >= 6) { let x0 = a[0], y0 = a[1];
      for (let i = 2; i + 3 < a.length; i += 4) { const cx = a[i], cy_ = a[i + 1], x1 = a[i + 2], y1 = a[i + 3];
        for (let k = 0; k <= 16; k++) { const t = k / 16; pts.push({ x: (1 - t) * (1 - t) * x0 + 2 * (1 - t) * t * cx + t * t * x1, y: (1 - t) * (1 - t) * y0 + 2 * (1 - t) * t * cy_ + t * t * y1 }); }
        x0 = x1; y0 = y1; } }
    else for (let i = 0; i + 1 < a.length; i += 2) pts.push({ x: a[i], y: a[i + 1] });
    return pts; };
  let reta = 0, caminho = 0, arestas = 0;
  cy.edges(':visible').not('.apagado').forEach(e => { const s = e.source(), t = e.target(); if (s.id() === t.id()) return; arestas++;
    const pts = poli(e);
    nos.filter(n => n.id() !== s.id() && n.id() !== t.id()).forEach(n => { const b = encolhe(n.boundingBox({ includeLabels: false }), 2);
      if (bate(s.position(), t.position(), b)) reta++;
      if (pts) { let h = false; for (let i = 0; i + 1 < pts.length && !h; i++) if (bate(pts[i], pts[i + 1], b)) h = true; if (h) caminho++; } }); });
  return { arestas, reta, caminho }; })"""


def _intersecoes(pg, cy_id: str = "cy"):
    return pg.evaluate(_INTERSECOES + "('" + cy_id + "')")


def _toca_no(pg, nome: str):
    pg.evaluate("n => { const cy = document.getElementById('cy')._cyreg.cy; cy.nodes().filter(x => x.data('label') === n)[0].emit('tap'); }", nome)
    pg.wait_for_timeout(1800)


@pytest.mark.parametrize("tema", ["light", "dark"])
def test_celular_fluxo_longo_vira_coluna_legivel_com_o_primeiro_passo_a_vista(navegador, site, tema):
    """Item 12: 10 passos no celular não viram um grafo de 3 px: coluna única, zoom legível, começo à vista, resto arrastando."""
    ctx, pg, erros = abrir(navegador, site / "explorador" / "index.html", 375, 812, tema, True)
    _pronto(pg)
    _abrir_visao(pg, "Fluxo longo")
    pg.wait_for_timeout(500)
    q = _quadro(pg)
    assert q["zoom"] >= 0.85 - 1e-6 and 12 * q["zoom"] >= 10, q["zoom"]                   # texto de 10 px CSS ou mais
    xs = [(n["x1"] + n["x2"]) / 2 for n in q["nos"]]
    assert max(xs) - min(xs) < 20, xs                                                   # uma coluna: o grafo cabe na largura
    t = q["tela"]
    ordem = sorted(q["nos"], key=lambda n: n["y1"])
    assert ordem[0]["nome"] == "Núcleo 01", [n["nome"] for n in ordem]                  # o começo do fluxo é o topo da coluna
    n1 = ordem[0]
    assert n1["x1"] >= t["x1"] - 1 and n1["x2"] <= t["x2"] + 1 and n1["y1"] >= t["y1"] - 1 and n1["y2"] <= t["y2"] + 1, n1
    for nome, c in q["caixas"].items():
        assert not _cobre(n1, c), (n1, nome, c)                                         # livre do título, das ferramentas e da Legenda
    i = _intersecoes(pg)
    assert i["caminho"] == 0, i                                                         # nenhuma ligação passa atrás de um nó
    assert _sem_overflow(pg)
    assert not [e for e in erros if "local.json" not in e and "404" not in e], erros
    ctx.close()


@pytest.mark.parametrize("largura,altura,toque", [(375, 812, True), (1440, 900, False)])
def test_ligacao_que_pularia_um_no_desvia_em_vez_de_passar_por_tras(navegador, site, largura, altura, toque):
    """Item 13: o atalho Núcleo 01 -> Núcleo 04 numa cadeia atravessaria dois nós em linha reta; o desenho precisa desviar."""
    ctx, pg, erros = abrir(navegador, site / "explorador" / "index.html", largura, altura, "dark", toque)
    _pronto(pg)
    _abrir_visao(pg, "Núcleo: componentes")
    pg.wait_for_timeout(500)
    i = _intersecoes(pg)
    assert i["reta"] > 0, i                                                             # sem o desvio, a reta bateria em nós
    assert i["caminho"] == 0, i                                                         # com o desvio, o caminho desenhado não bate
    assert not [e for e in erros if "local.json" not in e and "404" not in e], erros
    ctx.close()


def test_celular_foco_deixa_o_no_focado_e_vizinhos_acima_da_folha(navegador, site):
    """Item 13a: ao abrir a folha de um nó, o enquadre usa só a faixa livre, entre os cartões e o topo da folha."""
    ctx, pg, erros = abrir(navegador, site / "explorador" / "index.html", 375, 812, "dark", True)
    _pronto(pg)
    _abrir_visao(pg, "Hub: adaptadores")
    _toca_no(pg, "Núcleo 01")
    q = _quadro(pg)
    topo = pg.evaluate("document.getElementById('dir').getBoundingClientRect().top")
    foco = pg.evaluate("""(() => { const cy = document.getElementById('cy')._cyreg.cy, base = document.getElementById('cy').getBoundingClientRect();
        const b = n => { const r = n.renderedBoundingBox({ includeLabels: false }); return { x1: r.x1 + base.left, y1: r.y1 + base.top, x2: r.x2 + base.left, y2: r.y2 + base.top }; };
        return { foco: cy.nodes('.foco').map(b), vizinhos: cy.nodes('.vizinho').map(b) }; })()""")
    assert foco["foco"] and foco["vizinhos"], foco
    t = q["tela"]
    f = foco["foco"][0]
    assert f["y2"] <= topo and f["y1"] >= t["y1"] and f["x1"] >= t["x1"] - 1 and f["x2"] <= t["x2"] + 1, (f, topo)   # o focado fica acima da folha
    for nome, c in q["caixas"].items():
        if nome != "legenda":                                                           # a Legenda desce atrás da folha
            assert not _cobre(f, c), (f, nome, c)
    inteiros = [v for v in foco["vizinhos"] if v["y2"] <= topo and v["y1"] >= t["y1"] and v["x1"] >= t["x1"] - 1 and v["x2"] <= t["x2"] + 1]
    assert len(inteiros) >= 3, (len(inteiros), len(foco["vizinhos"]))                   # o máximo que cabe, não só o focado
    assert 12 * q["zoom"] >= 10, q["zoom"]
    assert _sem_overflow(pg)
    ctx.close()


def test_desktop_foco_em_mapa_grande_mantem_rotulos_de_ligacao_de_10px(navegador, site):
    """Item 13c: o rótulo das ligações em foco não encolhe para menos de 10 px nem o nó focado sai da tela."""
    ctx, pg, erros = abrir(navegador, site / "explorador" / "index.html", 1440, 900, "dark")
    _pronto(pg)
    _abrir_visao(pg, "Tudo junto")
    _toca_no(pg, "Núcleo 01")
    r = pg.evaluate("""(() => { const cy = document.getElementById('cy')._cyreg.cy, base = document.getElementById('cy').getBoundingClientRect();
        const e = cy.edges('.vizinho, .caminho')[0], b = cy.nodes('.foco')[0].renderedBoundingBox({ includeLabels: false }), dir = document.getElementById('dir').getBoundingClientRect();
        return { zoom: cy.zoom(), fonteRotulo: e.pstyle('font-size').pfValue * cy.zoom(), x1: b.x1 + base.left, x2: b.x2 + base.left, y1: b.y1 + base.top, y2: b.y2 + base.top,
                 inspetor: dir.left, tela: [base.left, base.top, base.right, base.bottom] }; })()""")
    assert r["fonteRotulo"] >= 10, r
    assert r["x1"] >= r["tela"][0] and r["x2"] <= min(r["tela"][2], r["inspetor"]) and r["y1"] >= r["tela"][1] and r["y2"] <= r["tela"][3], r
    assert not [e for e in erros if "local.json" not in e and "404" not in e], erros
    ctx.close()


def _grafo_do_tempo(pg):
    return pg.evaluate("""(() => { const cy = document.getElementById('tlGrafo')._cyreg.cy, base = document.getElementById('tlGrafo').getBoundingClientRect();
        const so = { includeLabels: false };
        const med = document.createElement('canvas').getContext('2d'); med.font = '12px ' + getComputedStyle(document.body).fontFamily;
        const nos = cy.nodes().map(n => { const b = n.boundingBox(so), r = n.renderedBoundingBox(so);
          return { nome: n.data('label'), forma: n.pstyle('shape').strValue, largura: b.w, altura: b.h,
                   palavra: Math.max(...String(n.data('label')).split(/\\s+/).map(p => med.measureText(p).width)),
                   x1: r.x1 + base.left, y1: r.y1 + base.top, x2: r.x2 + base.left, y2: r.y2 + base.top }; });
        return { zoom: cy.zoom(), nos, tela: { x1: base.left, y1: base.top, x2: base.right, y2: base.bottom },
                 dica: document.getElementById('tlDica').hidden ? '' : document.getElementById('tlDica').textContent }; })()""")


@pytest.mark.parametrize("largura,altura,toque,tema", [(375, 812, True, "light"), (375, 812, True, "dark"), (1440, 900, False, "dark")])
def test_linha_do_tempo_grafo_tem_nos_retangulares_que_cabem_o_texto_e_zoom_legivel(navegador, site, largura, altura, toque, tema):
    """Item 9: dagre, nós retangulares do tamanho do rótulo, zoom mínimo legível, sem ligação atrás de nó."""
    ctx, pg, erros = abrir(navegador, site / "explorador" / "index.html", largura, altura, tema, toque)
    _pronto(pg)
    pg.evaluate("document.getElementById('tlAbrir').click()")
    pg.wait_for_selector("#tlTrilho button")
    pg.wait_for_timeout(1200)
    g = _grafo_do_tempo(pg)
    assert len(g["nos"]) >= 4, g["nos"]
    assert all("rectangle" in n["forma"] for n in g["nos"]), [n["forma"] for n in g["nos"]]
    assert all(n["largura"] >= min(150, n["palavra"]) for n in g["nos"]), g["nos"]      # largura por rótulo: nada de texto vazando do nó
    assert 12 * g["zoom"] >= 10 - 1e-6, g["zoom"]                                       # texto de 10 px CSS ou mais
    t = g["tela"]
    visiveis = [n for n in g["nos"] if n["x1"] >= t["x1"] - 1 and n["x2"] <= t["x2"] + 1 and n["y1"] >= t["y1"] - 1 and n["y2"] <= t["y2"] + 1]
    assert visiveis, (t, g["nos"])                                                      # o enquadre mostra nós inteiros, não uma janela em branco
    if len(visiveis) < len(g["nos"]):
        assert "mínimo legível" in g["dica"], g["dica"]                                 # o recorte avisa que o resto se alcança arrastando
    assert _intersecoes(pg, "tlGrafo")["caminho"] == 0
    assert _sem_overflow(pg)
    assert not [e for e in erros if "local.json" not in e and "404" not in e], erros
    ctx.close()


@pytest.mark.parametrize("largura,altura,toque,kbd,legenda", [(700, 900, False, False, None), (1024, 768, True, False, 44), (1440, 900, False, True, None)])
def test_atalho_ctrl_k_some_em_toque_ou_janela_estreita_e_a_legenda_tem_44px_no_toque(navegador, site, largura, altura, toque, kbd, legenda):
    """Item 14: nada de "Ctrl K" onde não há teclado nem espaço; a Legenda tem alvo de 44 px no toque, mesmo em tablet."""
    ctx, pg, erros = abrir(navegador, site / "explorador" / "index.html", largura, altura, "light", toque)
    _pronto(pg)
    assert pg.is_visible("#kbdPaleta") is kbd
    assert pg.is_visible("#btnPaleta")
    if legenda:
        assert pg.evaluate("document.querySelector('#legendaCaixa summary').getBoundingClientRect().height") >= legenda
    assert _sem_overflow(pg)
    ctx.close()


_ALTURAS_NAV = "[...document.querySelectorAll('.nav-item')].filter(e => e.offsetParent).map(e => e.getBoundingClientRect().height)"


def test_leitor_itens_da_navegacao_tem_44px_no_toque_e_continuam_compactos_no_mouse(navegador, site):
    ctx, pg, erros = abrir(navegador, site / "leitor" / "index.html", 1024, 768, "light", True)
    pg.wait_for_selector(".nav-item")
    alturas = pg.evaluate(_ALTURAS_NAV)
    assert alturas and min(alturas) >= 44 - 0.5, alturas
    ctx.close()
    ctx, pg, _ = abrir(navegador, site / "leitor" / "index.html", 1440, 900, "light")
    pg.wait_for_selector(".nav-item")
    desktop = pg.evaluate(_ALTURAS_NAV)
    assert desktop and min(desktop) < 44, desktop                                       # no mouse a lista continua compacta
    ctx.close()


# Textos em português que o painel da linha do tempo e a Saúde não podem mostrar quando a página está em inglês.
_PT = ("Linha do tempo", "Saúde dos componentes", "Histórico do componente", "Voltar ao mapa", "Sem histórico", "Enquadrar")


@pytest.mark.parametrize("largura,altura,toque", [(1440, 900, False), (375, 812, True)])
def test_lang_en_traduz_linha_do_tempo_saude_e_painel_do_no(navegador, site, largura, altura, toque):
    """Item 19: com ?lang=en o botão, a Saúde e o painel do componente da linha do tempo saem em inglês."""
    ctx, pg, erros = abrir(navegador, site / "explorador" / "index.html", largura, altura, "dark", toque)
    pg.goto((site / "explorador" / "index.html").as_uri() + "?lang=en")
    _pronto(pg)
    if toque:
        pg.tap("#btnPainel")
        pg.wait_for_timeout(400)
    assert pg.inner_text("#tlAbrir") == "Timeline"
    assert pg.inner_text("[data-i18n=saudeBotao]").strip() != "Saúde dos componentes"
    pg.evaluate("document.getElementById('tlAbrir').click()")
    pg.wait_for_selector("#tlTrilho button")
    pg.wait_for_timeout(900)
    pg.evaluate("(() => { const cy = document.getElementById('tlGrafo')._cyreg.cy; cy.nodes()[0].emit('tap'); })()")
    pg.wait_for_function("document.getElementById('tlInspetor').innerText.includes('Component history')")
    texto = pg.evaluate("document.body.innerText")
    achados = [p for p in _PT if p in texto]
    assert not achados, achados
    assert "Back to the map" in texto
    assert not [e for e in erros if "local.json" not in e and "404" not in e], erros
    ctx.close()


def _leque_centralizado(ws: dict) -> None:
    """Fluxo como o do axios: uma cadeia de 6 nós em pé, centralizada sobre um leque de 6 nós de nome longo; em pé é o
    melhor encaixe e ainda assim não cabe na tela do desktop no zoom mínimo."""
    plugins = ws["model"]["softwareSystems"][0]["containers"][2]["components"]
    rid = iter(range(9000, 9100))

    def liga(a, b):
        r = {"id": str(next(rid)), "sourceId": a["id"], "destinationId": b["id"], "description": "chama", "technology": "chamada",
             "tags": "Relationship"}
        a["relationships"].append(r)
        return r["id"]

    cadeia, fileira = plugins[0:6], plugins[6:12]
    rels = [liga(a, b) for a, b in zip(cadeia, cadeia[1:])] + [liga(cadeia[-1], f) for f in fileira]
    ws["views"]["dynamicViews"].append({"key": "FluxoLeque", "title": "Fluxo leque", "description": "Percurso em leque.",
                                        "elements": [{"id": e["id"]} for e in cadeia + fileira],
                                        "relationships": [{"id": r, "order": str(i + 1), "description": f"passo {i + 1}"}
                                                          for i, r in enumerate(rels)]})


@pytest.fixture(scope="module")
def site_leque(tmp_path_factory):
    from _ui_site import construir
    return construir(tmp_path_factory.mktemp("site-leque"), ajuste=_leque_centralizado)


@pytest.mark.parametrize("largura,altura", [(1440, 900), (1280, 800)])
def test_desktop_fluxo_largo_nao_corta_no_na_borda_esquerda(navegador, site_leque, largura, altura):
    """Fluxo mais largo que a tela no zoom mínimo: a janela começa num nó inteiro, não no meio de um, e o passo 1 fica à vista."""
    ctx, pg, erros = abrir(navegador, site_leque / "explorador" / "index.html", largura, altura, "dark")
    _pronto(pg)
    _abrir_visao(pg, "Fluxo leque")
    q = _quadro(pg)
    t = q["tela"]
    assert q["zoom"] <= 0.751, q["zoom"]                                     # o caso: parou no zoom mínimo, não cabe
    na_faixa = [n for n in q["nos"] if n["y2"] > t["y1"] and n["y1"] < t["y2"]]
    cortados = [n["nome"] for n in na_faixa if n["x1"] < t["x1"] - 1 < n["x2"] - 2]
    assert not cortados, (q["zoom"], cortados)
    topo = next(n for n in q["nos"] if n["nome"].startswith("Plugin 01"))
    assert topo["x1"] >= t["x1"] - 1 and topo["x2"] <= t["x2"] + 1, topo
    assert not [e for e in erros if "local.json" not in e and "404" not in e], erros
    ctx.close()
