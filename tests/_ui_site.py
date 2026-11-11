"""Site de teste para os testes de interface (Playwright): um mapa sintético gerado pelos geradores reais.

Monta, em uma pasta temporária, `explorador/` e `leitor/` com os arquivos dos templates, o `dados.js` produzido por
`gerar_explorador.py` e `gerar_leitor.py` a partir de um workspace.json pequeno (sem Java nem Structurizr) e, quando
pedido, uma `linha-do-tempo.js` mínima. Os testes abrem as páginas por `file://`, o caminho de uso sem servidor.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
MODELO = RAIZ / "templates" / "structurizr"

ADR = """---
id: "0001"
titulo: Camadas do núcleo
status: aceita
data: 2026-11-09
date: 2026-11-09
decisores: [dono]
elementos: [nucleo03]
substitui: []
substituida_por: []
evidencia:
  - docs/01-visao.md
---

# Camadas do núcleo

## Contexto

O núcleo cresceu sem fronteiras claras.

## Decisão

O núcleo fica em camadas e cada camada só depende da de baixo.

## Alternativas

- Um bloco só.

## Consequências

Mudanças ficam locais.
"""

DOC = "# Visão\n\nEsta é a visão geral do mapa de teste.\n\n## Como abrir\n\nAbra o explorador.\n"


def _no(i: int, nome: str, ident: str, props: dict | None = None) -> dict:
    p = {"structurizr.dsl.identifier": ident, "status": "Pronto"}
    p.update(props or {})
    return {"id": str(i), "name": nome, "description": f"Descrição de {nome}.", "technology": "JavaScript",
            "tags": "Element,Component", "properties": p, "relationships": []}


def workspace(grande: int = 60) -> dict:
    """Pessoa, sistema, três containers (10, 6 e `grande` componentes) e dois fluxos."""
    rid = [1000]
    nucleo = [_no(100 + i, f"Núcleo {i + 1:02d}", f"nucleo{i + 1:02d}") for i in range(10)]
    adaptadores = [_no(200 + i, f"Adaptador {i + 1}", f"adapt{i + 1}") for i in range(6)]
    plugins = [_no(300 + i, f"Plugin {i + 1:02d} com nome comprido de teste", f"plug{i + 1:02d}") for i in range(grande)]

    def liga(origem: dict, destino: dict, desc: str) -> dict:
        rid[0] += 1
        origem["relationships"].append({"id": str(rid[0]), "sourceId": origem["id"], "destinationId": destino["id"],
                                        "description": desc, "technology": "chamada", "tags": "Relationship"})
        return {"id": str(rid[0])}

    rels_nucleo = [liga(nucleo[i], nucleo[i + 1], f"passa para {i + 2}") for i in range(9)]
    rels_adapt = [liga(adaptadores[i], nucleo[i], "usa") for i in range(6)]
    rels_plug = [liga(plugins[i], plugins[i + 1], "encadeia") for i in range(grande - 1)] + \
                [liga(plugins[i], nucleo[i % 10], "usa") for i in range(0, grande, 3)]
    pessoa = {"id": "1", "name": "Pessoa", "description": "Quem usa.", "tags": "Element,Person",
              "properties": {"structurizr.dsl.identifier": "pessoa"}, "relationships": []}
    r_usa = liga(pessoa, adaptadores[0], "usa")
    sistema = {"id": "2", "name": "Sistema de teste", "description": "O sistema.", "tags": "Element,Software System",
               "properties": {"structurizr.dsl.identifier": "sistema"}, "relationships": [],
               "containers": [
                   {"id": "10", "name": "Núcleo", "tags": "Element,Container", "description": "Regras.",
                    "properties": {"structurizr.dsl.identifier": "k1"}, "relationships": [], "components": nucleo},
                   {"id": "20", "name": "Adaptadores", "tags": "Element,Container", "description": "Bordas.",
                    "properties": {"structurizr.dsl.identifier": "k2"}, "relationships": [], "components": adaptadores},
                   {"id": "30", "name": "Plugins", "tags": "Element,Container", "description": "Extensões.",
                    "properties": {"structurizr.dsl.identifier": "k3"}, "relationships": [], "components": plugins}]}

    def ids(*grupos) -> list[dict]:
        return [{"id": e["id"]} for g in grupos for e in g]

    todos = nucleo + adaptadores + plugins
    fluxo = lambda chave, titulo, rels: {"key": chave, "title": titulo, "description": f"Percurso {titulo}.",
                                         "elements": ids(nucleo[:6]),
                                         "relationships": [{"id": r["id"], "order": str(i + 1), "description": f"passo {i + 1}"}
                                                           for i, r in enumerate(rels)]}
    return {"name": "Mapa de teste", "model": {"people": [pessoa], "softwareSystems": [sistema]}, "views": {
        "systemContextViews": [{"key": "Contexto", "title": "Contexto", "elements": ids([pessoa, sistema]),
                                "relationships": [r_usa]}],
        "containerViews": [{"key": "Containers", "title": "Containers", "elements": ids([pessoa], sistema["containers"]),
                            "relationships": []}],
        "componentViews": [
            {"key": "Nucleo", "title": "Núcleo: componentes", "elements": ids(nucleo), "relationships": rels_nucleo},
            {"key": "Plugins", "title": "Plugins: componentes", "elements": ids(plugins, nucleo),
             "relationships": rels_plug},
            {"key": "Tudo", "title": "Tudo junto", "elements": ids(todos), "relationships": rels_nucleo + rels_adapt + rels_plug}],
        "dynamicViews": [fluxo("FluxoA", "Fluxo A", rels_nucleo[:5]), fluxo("FluxoB", "Fluxo B", rels_nucleo[4:8])]}}


def _snapshot(ws: dict, ate: int) -> dict:
    """Foto do modelo com os `ate` primeiros componentes do núcleo (as versões antigas têm menos)."""
    sis = ws["model"]["softwareSystems"][0]
    elementos, ident_de = {}, {}
    for e in ws["model"]["people"] + [sis]:
        ident = e["properties"]["structurizr.dsl.identifier"]
        ident_de[e["id"]] = ident
        elementos[ident] = {"ident": ident, "nome": e["name"], "tipo": "Pessoa" if e in ws["model"]["people"] else "Sistema",
                            "container": None, "area": None, "status": "Pronto", "desc": e["description"], "tech": None,
                            "codigo": None}
    for c in sis["containers"]:
        ident_de[c["id"]] = c["properties"]["structurizr.dsl.identifier"]
        elementos[ident_de[c["id"]]] = {"ident": ident_de[c["id"]], "nome": c["name"], "tipo": "Container", "container": None,
                                        "area": None, "status": "Pronto", "desc": c["description"], "tech": None, "codigo": None}
        for k in c["components"][: ate if c["name"] == "Núcleo" else 0]:
            ident_de[k["id"]] = k["properties"]["structurizr.dsl.identifier"]
            elementos[ident_de[k["id"]]] = {"ident": ident_de[k["id"]], "nome": k["name"], "tipo": "Componente",
                                            "container": c["name"], "area": None, "status": "Pronto", "desc": k["description"],
                                            "tech": k["technology"], "codigo": None}
    relacoes = []
    for e in ws["model"]["people"] + [sis] + [k for c in sis["containers"] for k in [c] + c["components"]]:
        for r in e.get("relationships", []):
            de, para = ident_de.get(r["sourceId"]), ident_de.get(r["destinationId"])
            if de in elementos and para in elementos:
                relacoes.append({"de": de, "para": para, "de_nome": elementos[de]["nome"], "para_nome": elementos[para]["nome"],
                                 "desc": r["description"], "tech": r["technology"]})
    nucleo = [i for i, e in elementos.items() if e["container"] == "Núcleo"]
    visoes = [{"chave": "Nucleo", "tipo": "estatica", "titulo": "Núcleo: componentes", "desc": "", "elementos": nucleo,
               "relacoes": [r for r in relacoes if r["de"] in nucleo and r["para"] in nucleo]}]
    return {"elementos": elementos, "relacoes": relacoes, "fluxos": {}, "visoes": visoes}


def linha_do_tempo_js(ws: dict) -> str:
    """`linha-do-tempo.js` mínimo: três versões em que o núcleo cresce de 4 para 6 e depois 10 componentes."""
    marcos = [(4, "2026-11-01", "v0.1"), (6, "2026-11-05", "v0.2"), (10, "2026-11-09", "v0.3")]
    versoes, antes = [], None
    for i, (n, data, tag) in enumerate(marcos):
        snap = _snapshot(ws, n)
        novos = [e for k, e in snap["elementos"].items() if antes is None or k not in antes["elementos"]]
        novas = [r for r in snap["relacoes"] if antes is None or r not in antes["relacoes"]]
        versoes.append({"sha": f"a{i}bcdef", "sha_completo": f"a{i}bcdef" + "0" * 33, "data": data, "assunto": f"versão {tag}",
                        "tag": tag, "tag_distancia": 0, "commitado": True, "dados": True, "erro": None, "inicial": antes is None,
                        "base": versoes[-1]["sha"] if versoes else "", "idioma": "pt", "mudou_idioma": None,
                        "componentes": {"adicionados": novos, "removidos": [], "alterados": []},
                        "relacoes": {"novas": novas, "removidas": []}, "fluxos": {"adicionados": [], "removidos": [], "alterados": []},
                        "resumo": {"total": len(novos) + len(novas)}, "snapshot": snap, "registro": [], "indice": i + 1})
        antes = snap
    dados = {"formato": 1, "mapa": {"nome": "Mapa de teste", "pasta": ".", "rev": "a2bcdef"}, "total_versoes": len(versoes),
             "total_commits": len(versoes), "truncado": False, "versoes": versoes}
    return "window.LODEMAP_LINHA_DO_TEMPO = " + json.dumps(dados, ensure_ascii=False) + ";\n"


def construir(destino: Path, grande: int = 60) -> Path:
    """Gera `destino/{explorador,leitor}` e devolve `destino`."""
    destino.mkdir(parents=True, exist_ok=True)
    (destino / "lodemap.json").write_text(json.dumps({"projeto": "Mapa de teste", "idioma": "pt"}), encoding="utf-8")
    (destino / "adrs").mkdir(exist_ok=True)
    (destino / "docs").mkdir(exist_ok=True)
    (destino / "adrs" / "0001-camadas-do-nucleo.md").write_text(ADR, encoding="utf-8")
    (destino / "docs" / "01-visao.md").write_text(DOC, encoding="utf-8")
    ws = destino / "workspace.json"
    ws.write_text(json.dumps(workspace(grande)), encoding="utf-8")
    env = {k: v for k, v in os.environ.items() if k != "LODEMAP_IDIOMA"}
    for pasta, gerador in (("explorador", "gerar_explorador.py"), ("leitor", "gerar_leitor.py")):
        shutil.copytree(MODELO / pasta, destino / pasta, dirs_exist_ok=True)
        r = subprocess.run([sys.executable, str(MODELO / "scripts" / gerador), str(ws), str(destino / pasta)],
                           capture_output=True, text=True, encoding="utf-8", env=env)
        assert r.returncode == 0, r.stdout + r.stderr
    evid = {"referencia": {"data": "2026-11-09", "commit": "a2bcdef", "arvore_de_trabalho": "nao_verificada"},
            "componentes": {"nucleo01": {"testes": {"estado": "medido", "arquivos": ["tests/t.py"]}, "cobertura": {"estado": "ausente"},
                                         "junit": {"estado": "ausente"}, "git": {"commits_30_dias": 1, "commits_90_dias": 2}}}}
    (destino / "explorador" / "evidencias.js").write_text("window.LODEMAP_EVIDENCIAS = " + json.dumps(evid) + ";\n", encoding="utf-8")
    (destino / "explorador" / "linha-do-tempo.js").write_text(linha_do_tempo_js(json.loads(ws.read_text(encoding="utf-8"))),
                                                              encoding="utf-8")
    return destino


@pytest.fixture(scope="session")
def navegador():
    """Chromium do Playwright; sem o pacote ou sem o navegador instalado, os testes de interface são pulados."""
    sync = pytest.importorskip("playwright.sync_api")
    with sync.sync_playwright() as p:
        try:
            b = p.chromium.launch()
        except Exception as e:  # navegador não instalado
            pytest.skip(f"Chromium do Playwright indisponível: {str(e)[:80]}")
        yield b
        b.close()


@pytest.fixture(scope="module")
def site(tmp_path_factory):
    return construir(tmp_path_factory.mktemp("site-ui"))


def abrir(navegador, caminho: Path, largura: int, altura: int, tema: str = "dark", toque: bool = False):
    """Página nova no viewport pedido; devolve (contexto, página, lista de erros do console)."""
    ctx = navegador.new_context(viewport={"width": largura, "height": altura}, color_scheme=tema, has_touch=toque,
                                is_mobile=toque)
    pg = ctx.new_page()
    erros: list[str] = []
    pg.on("console", lambda m: erros.append(m.text) if m.type == "error" else None)
    pg.on("pageerror", lambda e: erros.append(str(e)))
    pg.goto(caminho.as_uri())
    return ctx, pg, erros
