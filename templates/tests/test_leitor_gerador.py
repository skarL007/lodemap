"""Leitor de documentação ({{ARQ_REL}}/leitor): âncoras estáveis, Markdown sem dependência e zero requisição externa.

Confere:
  1. o renderizador de Markdown (títulos, listas, tabelas, código, links, ênfase) e a reescrita de links entre
     documentos (.md -> #doc-<arquivo>, ADR -> #adr-<id>) e de identificadores do modelo para o mapa;
  2. que todo documento de docs/ ganha a âncora #doc-<arquivo sem .md> e todo ADR a âncora #adr-<id de 4 dígitos>
     (o explorador e as notas apontam para elas);
  3. que leitor/index.html não carrega nada de fora (sem CDN, fonte ou imagem remota) e traz os tokens do design.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
ARQ = ROOT / "{{ARQ_REL}}"
sys.path.insert(0, str(ARQ / "scripts"))
import gerar_leitor as gl  # noqa: E402

INDEX = ARQ / "leitor" / "index.html"
EXPORT = ARQ / ".structurizr" / "export" / "workspace.json"


def _ctx(elementos=None):
    return gl.Contexto({"01-visao-e-como-usar", "30-janela"}, {"0003-fila.md": "0003"},
                       elementos or {"orqEscala": {"nome": "Política de modelos", "tipo": "Componente"}}, "doc-x")


def test_markdown_blocos():
    md = ("# Título\n\nParágrafo com **negrito**, *ênfase* e `código`.\n\n## Seção um\n\n- a\n- b\n  - b1\n\n1. um\n2. dois\n\n"
          "| A | B |\n|---|---:|\n| x \\| y | 2 |\n\n```python\nprint('<oi>')\n```\n\n> citação\n")
    ctx = _ctx()
    h = gl.markdown(md, ctx)
    assert '<h1 id="doc-x--titulo">Título</h1>' in h
    assert '<h2 id="doc-x--secao-um">Seção um</h2>' in h
    assert "<strong>negrito</strong>" in h and "<em>ênfase</em>" in h and "<code>código</code>" in h
    assert re.search(r"<ul><li>a</li><li>b\s*<ul><li>b1</li></ul></li></ul>", h)
    assert "<ol><li>um</li><li>dois</li></ol>" in h
    assert "<td>x | y</td>" in h and '<th class="num">B</th>' in h
    assert "print(&#x27;&lt;oi&gt;&#x27;)" in h and "<script" not in h
    assert "<blockquote><p>citação</p></blockquote>" in h
    assert ctx.toc == [{"id": "doc-x--secao-um", "titulo": "Seção um", "nivel": 2}]


def test_markdown_escapa_html_cru():
    h = gl.markdown("Texto <script>alert(1)</script> e <b>x</b>.", _ctx())
    assert "<script>" not in h and "&lt;script&gt;" in h


def test_links_entre_documentos_e_mapa():
    ctx = _ctx()
    h = gl.markdown("[visão](01-visao-e-como-usar.md), [seção](30-janela.md#por-que), [adr](../adrs/0003-fila.md), "
                    "[mapa](../explorador/index.html#orqEscala), [site](https://exemplo.org) e `orqEscala`.", ctx)
    assert 'href="#doc-01-visao-e-como-usar"' in h
    assert 'href="#doc-30-janela--por-que"' in h
    assert 'href="#adr-0003"' in h
    assert 'href="../explorador/index.html#orqEscala" class="ref-mapa"' in h
    assert 'href="https://exemplo.org" rel="noopener noreferrer" target="_blank" class="externo"' in h
    assert '<a class="ref-mapa" href="../explorador/index.html#orqEscala"' in h


def test_frontmatter_simples():
    meta, corpo = gl.ler_frontmatter('---\nid: "0007"\nelementos: [a, b]\nevidencia:\n  - x.md\n  - "y z"\nsubstitui:\n---\n\n# T\n')
    assert meta == {"id": "0007", "elementos": ["a", "b"], "evidencia": ["x.md", "y z"], "substitui": ""}
    assert corpo.startswith("# T")


def _dados():
    ws = json.loads(EXPORT.read_text(encoding="utf-8-sig")) if EXPORT.is_file() else {}
    cfg_arq = ARQ / "lodemap.json"
    cfg = json.loads(cfg_arq.read_text(encoding="utf-8-sig")) if cfg_arq.is_file() else {}
    return gl.montar(ws, ARQ, cfg)


def test_ancoras_de_docs_e_adrs():
    d = _dados()
    ancoras = {x["ancora"] for x in d["docs"]} | {x["ancora"] for x in d["adrs"]}
    for f in sorted((ARQ / "docs").glob("*.md")):
        if f.stem != gl.INDICE_DECISOES:
            assert f"doc-{f.stem}" in ancoras, f"sem âncora para docs/{f.name}"
    for a in gl.ler_adrs(ARQ / "adrs"):
        assert re.fullmatch(r"\d{4}", a["id"]), a["arquivo"]
        assert f"adr-{a['id']}" in ancoras, f"sem âncora para adrs/{a['arquivo']}"
    secoes = {x["secao"] for x in d["docs"]}
    assert secoes <= {"explicacao", "guia", "referencia"}


def test_links_internos_resolvem():
    """Todo link interno do leitor aponta para uma âncora que existe ou para um arquivo da pasta da arquitetura."""
    d = _dados()
    ids = {"inicio", "decisoes"}
    paginas = d["docs"] + d["adrs"]
    for p in paginas:
        ids.add(p["ancora"])
        ids |= set(re.findall(r' id="([^"]+)"', p["html"]))
    quebrados = []
    for p in paginas:
        for href in re.findall(r'href="([^"]+)"', p["html"]):
            if href.startswith(("http:", "https:", "mailto:")):
                continue
            if href.startswith("#"):
                if href[1:] not in ids:
                    quebrados.append(f"{p['ancora']}: {href}")
                continue
            caminho = href.split("#", 1)[0]
            if caminho and not (ARQ / "leitor" / caminho).resolve().exists():
                quebrados.append(f"{p['ancora']}: {href}")
    assert not quebrados, quebrados


def test_dados_js_gerado_e_legivel():
    dados = ARQ / "leitor" / "dados.js"
    if not dados.is_file():
        pytest.skip("leitor/dados.js ainda não gerado (rode scripts/atualizar.ps1)")
    t = dados.read_text(encoding="utf-8")
    m = re.search(r"window\.LEITOR_DADOS = (\{.*\});\s*$", t, flags=re.S)
    assert m, "formato de dados.js inesperado"
    d = json.loads(m.group(1))
    assert {"docs", "adrs", "busca", "secoes", "avisos"} <= set(d)


def test_index_sem_requisicao_externa():
    t = INDEX.read_text(encoding="utf-8")
    assert not re.search(r'(?:src|href)\s*=\s*["\'](?:https?:)?//', t), "o leitor não pode carregar nada de fora"
    assert not re.search(r"@import|url\(\s*['\"]?(?:https?:)?//", t)
    assert '<script src="dados.js"></script>' in t
    for ancora in ("doc-", "adr-", "?tema=", "claro", "escuro"):
        assert ancora in t


def test_bloco_mermaid_vira_diagrama_com_o_texto_junto():
    h = gl.markdown("```mermaid\nflowchart TD\n  A[\"<Início>\"] --> B\n```\n\n```python\nx = 1\n```\n", _ctx())
    fig_mermaid, fig_python = re.findall(r"<figure.*?</figure>", h, flags=re.S)
    assert 'class="codigo diagrama" data-diagrama="mermaid"' in fig_mermaid
    assert "Diagrama Mermaid</div>" in fig_mermaid and "(texto)" not in fig_mermaid
    assert "A[&quot;&lt;Início&gt;&quot;] --&gt; B" in fig_mermaid and "<Início>" not in fig_mermaid
    assert "data-diagrama" not in fig_python and 'class="codigo"' in fig_python


def test_leitor_desenha_mermaid_com_biblioteca_embutida_e_carregada_sob_demanda():
    t = INDEX.read_text(encoding="utf-8")
    assert 'tiny: "mermaid.tiny.js"' in t and '"vendor/" + ARQ_MERMAID' in t and "<script src=\"vendor/mermaid" not in t, "a biblioteca só carrega quando há diagrama"
    assert 'securityLevel: "strict"' in t and "startOnLoad: false" in t
    assert "figure[data-diagrama]" in t and "lm:tema" in t


def test_mermaid_embutido_com_licenca_e_versao():
    vendor = ARQ / "leitor" / "vendor"
    js = vendor / "mermaid.tiny.js"
    assert js.is_file() and js.stat().st_size > 1_000_000, "falta leitor/vendor/mermaid.tiny.js"
    assert 'version:"12.3.0-tiny"' in js.read_text(encoding="utf-8", errors="replace")
    assert "Permission is hereby granted, free of charge" in (vendor / "LICENSE-mermaid.txt").read_text(encoding="utf-8")
    assert "Apache License" in (vendor / "LICENSE-apache-2.0.txt").read_text(encoding="utf-8")
    assert "12.3.0" in (vendor / "LEIAME.md").read_text(encoding="utf-8")


def test_index_traz_os_tokens_do_design():
    t = INDEX.read_text(encoding="utf-8")
    m = re.search(r"/\* sds:tokens:start \*/\s*(.*?)\s*/\* sds:tokens:end \*/", t, re.S)
    assert m and "--brand" in m.group(1), "faltam os tokens do design entre sds:tokens:start e sds:tokens:end"


def test_adr_resumo_vem_da_decisao_e_aliases_entram_na_busca(tmp_path):
    (tmp_path / "adrs").mkdir()
    (tmp_path / "adrs" / "0001-x.md").write_text(
        "---\nid: \"0001\"\ntitulo: Fila única\nstatus: aceita\ndata: 2026-01-01\ndate: 2026-01-01\ndecisores: [dono]\n"
        "elementos: []\nsubstitui: []\nsubstituida_por: []\naliases: [H-012]\nevidencia: []\n---\n\n# Fila única\n\n"
        "## Contexto\n\nPergunta antiga.\n\n## Decisão\n\nUma fila só para todos os eventos.\n\n## Alternativas\n\nNenhuma.\n\n"
        "## Consequências\n\nNenhuma.\n", encoding="utf-8")
    d = gl.montar({"model": {}}, tmp_path, {})
    a = d["adrs"][0]
    assert a["resumo"] == "Uma fila só para todos os eventos." and a["aliases"] == ["H-012"]
    assert any("H-012" in b["texto"] for b in d["busca"] if b["pagina"] == "adr-0001")

# ------------------------------------------------------------ idioma (pt padrão, en disponível)

def _adr(tmp_path, nome="0001-x.md", status="aceita", secoes=("Contexto", "Decisão", "Alternativas", "Consequências")):
    (tmp_path / "adrs").mkdir(exist_ok=True)
    corpo = "".join(f"## {s}\n\nTexto de {s}.\n\n" for s in secoes)
    (tmp_path / "adrs" / nome).write_text(
        f"---\nid: \"0001\"\ntitulo: Fila\nstatus: {status}\ndata: 2026-01-01\ndate: 2026-01-01\ndecisores: [dono]\n"
        f"elementos: []\nsubstitui: []\nsubstituida_por: []\nevidencia: []\n---\n\n# Fila\n\n{corpo}", encoding="utf-8")


def test_idioma_vai_para_os_dados_pt_por_padrao_e_en_quando_pedido(tmp_path):
    assert gl.montar({"model": {}}, tmp_path, {})["idioma"] == "pt"
    assert gl.montar({"model": {}}, tmp_path, {"idioma": "en"})["idioma"] == "en"
    assert gl.montar({"model": {}}, tmp_path, {"idioma": "fr"})["idioma"] == "pt", "idioma inválido volta ao padrão"


def test_main_le_o_idioma_do_lodemap_json(tmp_path, monkeypatch):
    monkeypatch.delenv("LODEMAP_IDIOMA", raising=False)
    (tmp_path / "lodemap.json").write_text('{"projeto": "X", "idioma": "en"}', encoding="utf-8")
    (tmp_path / "ws.json").write_text('{"name": "X", "model": {}}', encoding="utf-8")
    destino = tmp_path / "leitor"
    assert gl.main(["gerar_leitor.py", str(tmp_path / "ws.json"), str(destino)]) == 0
    d = json.loads(re.search(r"window\.LEITOR_DADOS = (\{.*\});", (destino / "dados.js").read_text(encoding="utf-8"), re.S).group(1))
    assert d["idioma"] == "en" and [s["titulo"] for s in d["secoes"]][:2] == ["Explanation", "Guides"]


def test_secoes_e_rotulos_do_gerador_seguem_o_idioma(tmp_path):
    _adr(tmp_path)
    pt = gl.montar({"model": {}}, tmp_path, {})
    en = gl.montar({"model": {}}, tmp_path, {"idioma": "en"})
    assert [s["titulo"] for s in pt["secoes"]] == ["Explicação", "Guias", "Referência", "Decisões"]
    assert [s["titulo"] for s in en["secoes"]] == ["Explanation", "Guides", "Reference", "Decisions"]
    assert pt["adrs"][0]["statusRotulo"] == "Aceita" and en["adrs"][0]["statusRotulo"] == "Accepted"
    assert pt["adrs"][0]["status"] == en["adrs"][0]["status"] == "aceita", "o valor do frontmatter não muda"
    assert en["busca"][0]["onde"] == "Decisions" and en["busca"][0]["ondeChave"] == "decisoes"
    assert "Accepted" in en["busca"][0]["texto"] and "Aceita" in en["busca"][0]["texto"], "a busca acha o status nos dois idiomas"


def test_aviso_de_mermaid_e_dica_do_mapa_no_idioma(tmp_path):
    md = "```mermaid\nflowchart TD\n  A-->B\n```\n\nVeja `orqEscala`."
    el = {"orqEscala": {"nome": "Política", "tipo": "Componente"}}
    pt = gl.markdown(md, gl.Contexto(set(), {}, el, "doc-x"))
    en = gl.markdown(md, gl.Contexto(set(), {}, el, "doc-x", "en"))
    assert "Diagrama Mermaid</div>" in pt and 'title="Ver Política no mapa"' in pt
    assert "Mermaid diagram</div>" in en and 'title="View Política on the map"' in en


def test_adr_em_ingles_valida_e_normaliza_o_status(tmp_path):
    _adr(tmp_path, status="Accepted", secoes=("Context", "Decision", "Alternatives", "Consequences"))
    adrs = gl.ler_adrs(tmp_path / "adrs")
    assert adrs[0]["status"] == "aceita"
    assert gl.validar_adrs(adrs, None, "en") == []
    d = gl.montar({"model": {}}, tmp_path, {"idioma": "en"})
    assert d["avisos"] == [] and d["adrs"][0]["resumo"] == "Texto de Decision."
    assert gl.STATUS_ADR_EN == {"proposta": "Proposed", "aceita": "Accepted", "substituida": "Superseded", "rejeitada": "Rejected"}


@pytest.mark.parametrize("en,canonica", [("proposed", "proposta"), ("accepted", "aceita"), ("superseded", "substituida"),
                                          ("rejected", "rejeitada"), ("aceita", "aceita")])
def test_status_em_ingles_vira_chave_canonica(tmp_path, en, canonica):
    _adr(tmp_path, status=en)
    assert gl.ler_adrs(tmp_path / "adrs")[0]["status"] == canonica


def test_validacao_continua_exigindo_secoes_e_status(tmp_path):
    _adr(tmp_path, status="aceito", secoes=("Contexto", "Decisão"))
    erros = gl.validar_adrs(gl.ler_adrs(tmp_path / "adrs"), None)
    assert any("status 'aceito' inválido" in e for e in erros) and any("falta a seção '## Alternativas'" in e for e in erros)
    erros_en = gl.validar_adrs(gl.ler_adrs(tmp_path / "adrs"), None, "en")
    assert any("status 'aceito' invalid" in e for e in erros_en) and any("missing section '## Alternatives'" in e for e in erros_en)


def test_lancamento_em_portugues_esconde_o_seletor_de_idioma():
    """Leitor e explorador: seletor PT | EN escondido e escolha guardada ignorada até um lançamento em inglês."""
    explorador = INDEX.parent.parent / "explorador" / "index.html"
    for pagina, ident in ((INDEX, 'id="lmIdioma" hidden'), (explorador, 'id="seletorIdioma" hidden')):
        t = pagina.read_text(encoding="utf-8")
        assert ident in t, pagina
        assert re.search(r"SELETOR_IDIOMA = false;", t), pagina
        assert ".lm-idioma[hidden] { display: none; }" in t, pagina
        assert re.search(r"if \(SELETOR_IDIOMA\) try \{ \w+ = localStorage\.getItem", t) or \
            re.search(r"if \(SELETOR_IDIOMA\) try \{ const g = localStorage\.getItem", t), pagina


def test_leitor_traz_dicionario_pt_en_completo_e_seletor():
    t = INDEX.read_text(encoding="utf-8")
    assert 'CHAVE_IDIOMA = "lodemap-idioma"' in t and 'get("lang")' in t and "D.idioma" in t
    assert 'data-idioma="pt"' in t and 'data-idioma="en"' in t
    assert 'IDIOMA === "en" ? "en" : "pt-BR"' in t
    if not shutil.which("node"):
        pytest.skip("node não instalado: não dá para comparar as chaves do dicionário")
    fonte = re.search(r"var TEXTOS = (\{.*?\n  \});\n  var MESES", t, re.S).group(1)
    r = subprocess.run(["node", "-e", f"const T = {fonte}; console.log(JSON.stringify([Object.keys(T.pt), Object.keys(T.en)]))"],
                       capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, r.stderr
    pt, en = json.loads(r.stdout)
    assert set(pt) == set(en) and len(pt) > 100, sorted(set(pt) ^ set(en))


def test_mindmap_architecture_e_formula_carregam_a_versao_completa_so_quando_precisam():
    t = INDEX.read_text(encoding="utf-8")
    assert 'completo: "mermaid.min.js"' in t and "function pedeCompleto" in t
    assert "mindmap|architecture(-beta)?" in t and '"$$"' in t
    js = ARQ / "leitor" / "vendor" / "mermaid.min.js"
    if js.is_file():  # o dono pode apagar a completa para economizar espaço; o leitor então só avisa
        assert 'version:"12.3.0"' in js.read_text(encoding="utf-8", errors="replace")
