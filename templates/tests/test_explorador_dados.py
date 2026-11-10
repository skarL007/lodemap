"""gerar_explorador.py: dados de inteligência do explorador (mudanças, saúde, prova, citações e memória)."""
from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "{{ARQ_REL}}" / "scripts" / "gerar_explorador.py"


def _modulo():
    spec = importlib.util.spec_from_file_location("gerar_explorador_teste", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _git(repo: Path, *args: str) -> str:
    r = subprocess.run(["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@t", *args], check=True,
                       capture_output=True, text=True)
    return r.stdout.strip()


def _comp(id_: str, ident: str, codigo: str, rels=()) -> dict:
    return {"id": id_, "name": ident.title(), "tags": "Element,Component",
            "properties": {"structurizr.dsl.identifier": ident, "codigo": codigo},
            "relationships": [{"id": rid, "sourceId": id_, "destinationId": dest, "description": "usa"} for rid, dest in rels]}


def _workspace() -> dict:
    comps = [
        _comp("1", "compA", "src/a.py", [("r1", "2"), ("r2", "3")]),
        _comp("2", "compB", "src/b.py"),
        _comp("3", "compC", "src/c.py"),
    ]
    return {
        "name": "Teste", "description": "",
        "model": {"people": [{"id": "9", "name": "Dono", "tags": "Element,Person", "properties": {"structurizr.dsl.identifier": "dono"},
                              "relationships": [{"id": "r9", "sourceId": "9", "destinationId": "5", "description": "usa"}]}],
                  "softwareSystems": [{"id": "4", "name": "Sis", "tags": "Element", "properties": {},
                                       "containers": [{"id": "5", "name": "App", "tags": "Element,Container",
                                                       "properties": {"structurizr.dsl.identifier": "app"}, "components": comps}]}]},
        "views": {"dynamicViews": [{"key": "Fluxo", "title": "Fluxo", "elements": [{"id": "1"}, {"id": "2"}, {"id": "3"}],
                                    "relationships": [{"id": "r1", "order": "1"}, {"id": "r2", "order": "2"}]}]},
    }


@pytest.fixture
def projeto(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    (repo / "src").mkdir(parents=True)
    for n in "abc":
        (repo / "src" / f"{n}.py").write_text(f"{n} = 1\n")
    arq = repo / "arq"
    (arq / ".structurizr" / "export").mkdir(parents=True)
    (arq / "lodemap.json").write_text(json.dumps({"projeto": "T", "raiz_codigo": "src", "modulos": ["src/*.py"]}))
    (arq / ".structurizr" / "export" / "workspace.json").write_text(json.dumps(_workspace()))
    (arq / "adrs").mkdir()
    (arq / "adrs" / "0002-decisao.md").write_text("# ADR 0002: Decisão\n\nO compB fica isolado.\n", encoding="utf-8")
    (arq / "docs").mkdir()
    (arq / "docs" / "10-guia.md").write_text("# Guia\n\nComo o compA conversa (e não compAx).\n", encoding="utf-8")
    return arq


def _ws(arq: Path) -> Path:
    return arq / ".structurizr" / "export" / "workspace.json"


def test_dados_versionados_nao_levam_o_caminho_absoluto_da_maquina(projeto):
    """O dados.js vai para o git: a raiz local do repositório fica só em .lodemap/local.json, que é ignorado."""
    g = _modulo()
    repo = projeto.parent
    d = g.montar(_ws(projeto), projeto / "explorador", str(repo))
    assert "repo" not in d and d["arqRel"] == "arq"
    assert str(repo).replace("\\", "/") not in json.dumps(d, ensure_ascii=False).replace("\\\\", "/")
    g.gravar_local(projeto, str(repo))
    local = json.loads((projeto / ".lodemap" / "local.json").read_text(encoding="utf-8"))
    assert local == {"repo": str(repo).replace("\\", "/")}
    assert g.montar(_ws(projeto), projeto / "explorador")["arqRel"] is None


def test_sem_arquivos_opcionais_os_blocos_saem_nulos(projeto):
    d = _modulo().montar(_ws(projeto), projeto / "explorador")
    assert d["mudancas"] is None and d["qualidade"] is None and d["prova"] is None and "memoria" not in d
    assert "lite" not in d and d["leitor"] == "../leitor/index.html"


def test_prova_marca_relacao_confirmada_e_so_no_modelo(projeto):
    (projeto / "relacoes-codigo.json").write_text(json.dumps({"fonte": "ast", "pares": [
        # o código vai de B para A (import ao contrário do verbo do modelo): ainda confirma a relação A -> B
        {"de": "compB", "para": "compA", "tipo": "imports", "arestas": 3, "confianca": "media", "noModelo": True},
        {"de": "compC", "para": "compB", "tipo": "calls", "arestas": 1, "confianca": "baixa", "noModelo": False},
    ]}))
    p = _modulo().montar(_ws(projeto), projeto / "explorador")["prova"]
    assert p["porRelacao"]["r1"] == {"estado": "confirmada", "arestas": 3, "confianca": "media", "tipo": "imports"}
    assert p["porRelacao"]["r2"] == {"estado": "modelo"}
    assert "r9" not in p["porRelacao"], "pessoa -> container não é relação entre componentes"
    assert p["resumo"] == {"confirmadas": 1, "soModelo": 1, "faltandoNoModelo": 1}
    assert p["faltandoNoModelo"][0]["de"] == "compC"


def test_saude_vem_do_estado(projeto):
    (projeto / ".lodemap").mkdir()
    (projeto / ".lodemap" / "estado.json").write_text(json.dumps(
        {"geradoEm": "2026-11-05T10:00:00-03:00", "qualidade": {"total": 81.5, "aprovado": False, "rodadas": 2, "pendencias": ["falta ADR"]}}))
    q = _modulo().montar(_ws(projeto), projeto / "explorador")["qualidade"]
    assert q == {"total": 81.5, "aprovado": False, "rodadas": 2, "pendencias": ["falta ADR"], "geradoEm": "2026-11-05T10:00:00-03:00"}


@pytest.mark.skipif(not shutil.which("git"), reason="precisa do git")
def test_mudancas_desde_o_ultimo_commit(projeto):
    repo = projeto.parent
    _git(repo, "init", "-q")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "base")
    (projeto / ".lodemap").mkdir()
    (projeto / ".lodemap" / "estado.json").write_text(json.dumps({"ultimoCommit": _git(repo, "rev-parse", "HEAD")}))
    (repo / "src" / "a.py").write_text("a = 2\n")
    (repo / "src" / "novo.py").write_text("n = 1\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "muda a e cria novo")
    m = _modulo().montar(_ws(projeto), projeto / "explorador")["mudancas"]
    assert m["modo"] == "incremental"
    assert [c["id"] for c in m["componentesAfetados"]] == ["compA"]
    assert m["modulosNovos"] == ["src/novo.py"] and m["semComponente"] == ["src/novo.py"]


def test_mudancas_sem_git_nao_quebra(projeto):
    (projeto / ".lodemap").mkdir()
    (projeto / ".lodemap" / "estado.json").write_text(json.dumps({"ultimoCommit": "abc123"}))
    m = _modulo().montar(_ws(projeto), projeto / "explorador")["mudancas"]
    assert m["modo"] in ("completo", "indisponivel")


def test_adrs_e_documentos_citam_pelo_identificador(projeto):
    d = _modulo().montar(_ws(projeto), projeto / "explorador")
    adr = d["adrs"][0]
    assert adr["ancora"] == "adr-0002" and adr["elementos"] == ["2"]
    doc = d["documentos"][0]
    assert doc["ancora"] == "doc-10-guia" and doc["elementos"] == ["1"], "compAx não pode contar como compA"


def test_main_grava_dados_js(projeto, monkeypatch):
    mod = _modulo()
    monkeypatch.setattr("sys.argv", ["gerar_explorador.py", str(_ws(projeto)), str(projeto / "explorador")])
    mod.main()
    texto = (projeto / "explorador" / "dados.js").read_text(encoding="utf-8")
    dados = json.loads(texto[texto.index("=") + 1:].strip().rstrip(";"))
    assert dados["visoes"][0]["tipo"] == "dinamica" and len(dados["visoes"][0]["fluxo"]) == 2


@pytest.mark.parametrize("config,esperado", [({}, "pt"), ({"idioma": "pt"}, "pt"), ({"idioma": "en"}, "en"), ({"idioma": "xx"}, "pt")])
def test_dados_gravam_o_idioma(projeto, monkeypatch, config, esperado):
    monkeypatch.delenv("LODEMAP_IDIOMA", raising=False)
    cfg = json.loads((projeto / "lodemap.json").read_text())
    (projeto / "lodemap.json").write_text(json.dumps({**cfg, **config}))
    assert _modulo().montar(_ws(projeto), projeto / "explorador")["idioma"] == esperado
