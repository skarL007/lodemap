"""qualidade.py (rubrica do modelo C4 da lodemap) com um workspace.json mínimo e um codegraph.db mínimo.

Roda dentro da skill (templates/tests) ou num projeto: procura scripts/qualidade.py em LODEMAP_SKILL,
na pasta da skill acima deste arquivo ou em ~/.claude/skills/lodemap.
"""
from __future__ import annotations

import importlib.util
import json
import os
import sqlite3
import sys
from pathlib import Path

import pytest


def _scripts() -> Path | None:
    cands = [os.environ.get("LODEMAP_SKILL"), Path(__file__).resolve().parents[2],
             Path.home() / ".claude" / "skills" / "lodemap"]
    for c in cands:
        if c and (Path(c) / "scripts" / "qualidade.py").is_file():
            return Path(c) / "scripts"
    return None


SCRIPTS = _scripts()
pytestmark = pytest.mark.skipif(SCRIPTS is None, reason="scripts/qualidade.py da skill não encontrado")


@pytest.fixture(scope="module")
def q():
    sys.path.insert(0, str(SCRIPTS))
    spec = importlib.util.spec_from_file_location("qualidade", SCRIPTS / "qualidade.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _comp(i, ident, nome, desc, codigo, tags, status, grupo="G", obs=""):
    p = {"structurizr.dsl.identifier": ident, "status": status, "area": "AreaX"}
    if codigo:
        p["codigo"] = codigo
    if obs:
        p["observabilidade"] = obs
    return {"id": str(i), "name": nome, "description": desc, "technology": "Python", "tags": tags, "group": grupo,
            "properties": p}


def _rel(i, a, b, desc="Chama", tech="HTTP"):
    return {"id": f"r{i}", "sourceId": str(a), "destinationId": str(b), "description": desc, "technology": tech}


@pytest.fixture
def projeto(tmp_path):
    repo = tmp_path / "repo"
    (repo / "src").mkdir(parents=True)
    for f in ("a.py", "b.py", "c.py", "solto.py"):
        (repo / "src" / f).write_text("x = 1\n")
    arq = repo / "arq"
    (arq / ".structurizr" / "export").mkdir(parents=True)
    (arq / "lodemap.json").write_text(json.dumps(
        {"projeto": "T", "raiz_codigo": "src", "modulos": ["src/*.py"]}))
    boa = "Recebe o pedido e decide a rota, para que o resto não precise conhecer o formato."
    comps = [
        _comp(10, "compA", "Entrada", boa, "src/a.py", "Element,Component,Pronto", "Pronto", obs="a.req, a.erro"),
        _comp(11, "compB", "Regras", boa, "src/b.py", "Element,Component,EmAndamento", "Em andamento"),
        # ruim em tudo: descrição curta, caminho que não existe, sem grupo, sem tag de status, órfão
        _comp(12, "compC", "Cru", "Cru", "src/c.py, nao_existe.py", "Element,Component", "", grupo=""),
    ]
    comps[2]["properties"].pop("area")
    comps[0]["relationships"] = [_rel(1, 10, 11), _rel(2, 10, 99, desc="", tech="")]
    ws = {"model": {"people": [{"id": "99", "name": "Dono", "properties": {"structurizr.dsl.identifier": "dono"}}],
                    "softwareSystems": [{"id": "1", "name": "S",
                                         "containers": [{"id": "2", "name": "App", "components": comps}]}]},
          "views": {"componentViews": [{"key": "App-Completo", "containerId": "2"}],
                    "dynamicViews": [{"key": "F1", "relationships": [{"id": "r1"}, {"id": "r2"}]}]}}
    (arq / ".structurizr" / "export" / "workspace.json").write_text(json.dumps(ws))
    return repo, arq


def test_notas_por_criterio(q, projeto):
    repo, arq = projeto
    r = q.avaliar(arq, repo, fonte="ast")
    c = r["criterios"]
    assert c["descricao"]["nota"] == pytest.approx(66.7, abs=0.1)   # 2 de 3
    assert c["codigo"]["nota"] == pytest.approx(66.7, abs=0.1)      # compC aponta para arquivo que não existe
    assert c["observabilidade"]["nota"] == pytest.approx(33.3, abs=0.1)
    assert c["orfaos"]["nota"] == pytest.approx(66.7, abs=0.1)      # compC sem relação
    assert c["relacoes_qualificadas"]["nota"] == 50.0               # 1 de 2 com verbo e tecnologia
    assert c["status"]["nota"] == pytest.approx(66.7, abs=0.1)
    assert c["visoes_container"]["nota"] == 100.0
    assert c["fluxos"]["nota"] == pytest.approx(33.3, abs=0.1)      # 1 de 3
    assert c["passos_fluxo"]["nota"] == pytest.approx(33.3, abs=0.1)  # 2 de 6
    assert c["agrupamento"]["nota"] == pytest.approx(66.7, abs=0.1)
    assert c["cobertura"]["nota"] == 75.0                            # só solto.py fica fora
    assert 0 < r["total"] < 100


def test_listar_reprovados(q, projeto):
    repo, arq = projeto
    rep = q.avaliar(arq, repo, fonte="ast", listar=True)["reprovados"]
    assert rep["descricao"] == ["compC"] and rep["codigo"] == ["compC"] and rep["orfaos"] == ["compC"]
    assert rep["status"] == ["compC"] and rep["agrupamento"] == ["compC"]
    assert rep["cobertura"] == ["src/solto.py"]
    assert rep["relacoes_qualificadas"] == ["compA -> dono"]


def test_sem_pares_no_codigo_o_recall_e_nd(q, projeto):
    repo, arq = projeto
    # nenhum import entre os arquivos: não há pares, então o recall é n/d e fica fora da nota
    r = q.avaliar(arq, repo)
    assert r["criterios"]["recall_relacoes"]["nota"] is None


def _db_minimo(caminho: Path, arestas):
    """Mesmo schema do CodeGraph (só as colunas que a ponte lê)."""
    con = sqlite3.connect(caminho)
    con.executescript("""
        CREATE TABLE nodes (id TEXT PRIMARY KEY, kind TEXT NOT NULL, name TEXT NOT NULL, qualified_name TEXT NOT NULL,
            file_path TEXT NOT NULL, language TEXT NOT NULL, start_line INTEGER NOT NULL, end_line INTEGER NOT NULL,
            start_column INTEGER NOT NULL DEFAULT 0, end_column INTEGER NOT NULL DEFAULT 0, docstring TEXT, signature TEXT,
            updated_at INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE edges (id INTEGER PRIMARY KEY AUTOINCREMENT, source TEXT NOT NULL, target TEXT NOT NULL,
            kind TEXT NOT NULL, metadata TEXT, line INTEGER, col INTEGER, provenance TEXT);
        CREATE TABLE files (path TEXT PRIMARY KEY, content_hash TEXT NOT NULL DEFAULT '', language TEXT NOT NULL,
            size INTEGER NOT NULL DEFAULT 0, modified_at INTEGER NOT NULL DEFAULT 0, indexed_at INTEGER NOT NULL DEFAULT 0,
            node_count INTEGER DEFAULT 0, errors TEXT, generated INTEGER NOT NULL DEFAULT 0);
    """)
    for f in ("src/a.py", "src/b.py", "src/c.py"):
        con.execute("INSERT INTO files (path, language) VALUES (?, 'python')", (f,))
        con.execute("INSERT INTO nodes (id, kind, name, qualified_name, file_path, language, start_line, end_line) "
                    "VALUES (?, 'function', 'f', 'f', ?, 'python', 1, 5)", (f"fn:{f}", f))
    for de, para, kind in arestas:
        con.execute("INSERT INTO edges (source, target, kind) VALUES (?, ?, ?)", (f"fn:{de}", f"fn:{para}", kind))
    con.commit()
    con.close()


def test_recall_e_precisao_com_codegraph(q, projeto, tmp_path):
    repo, arq = projeto
    db = tmp_path / "codegraph.db"
    # a -> b: 3 calls (alta, está no modelo); b -> c: 2 imports (media, falta no modelo); a -> c: 1 call (baixa, ignorada)
    _db_minimo(db, [("src/a.py", "src/b.py", "calls")] * 3 + [("src/b.py", "src/c.py", "imports")] * 2
               + [("src/a.py", "src/c.py", "calls")])
    r = q.avaliar(arq, repo, fonte="codegraph", db=db, listar=True)
    c = r["criterios"]
    assert c["recall_relacoes"]["nota"] == 50.0            # 1 de 2 pares de confiança alta ou média
    assert any("compB -> compC" in x and "2 arestas" in x for x in r["reprovados"]["recall_relacoes"])
    # a relação do modelo entre componentes de código (A -> B) tem aresta; a relação A -> pessoa fica de fora
    assert c["precisao_relacoes"]["nota"] == 100.0


def test_gate_baseline_e_nd(q, projeto):
    repo, arq = projeto
    r = q.avaliar(arq, repo, fonte="ast")
    base = {"criterios": {k: 100.0 for k in r["criterios"]}, "pesos": q.PESOS}
    g = q.gate(r, base)
    assert not g["aprovado"] and g["falhas"]
    # baseline igual ao próprio resultado aprova; critério n/d no projeto não entra
    base_igual = {"criterios": {k: c["nota"] for k, c in r["criterios"].items()}, "pesos": q.PESOS}
    assert q.gate(r, base_igual)["aprovado"]
    assert "recall_relacoes" not in g["criteriosComparados"]


def test_observabilidade_conta_no_total_mas_nao_tem_piso(q, projeto):
    """Projeto sem log nem métrica (uma biblioteca) não pode reprovar só por isso, nem ser empurrado a inventar."""
    repo, arq = projeto
    r = q.avaliar(arq, repo, fonte="ast")
    base = {"criterios": {k: c["nota"] for k, c in r["criterios"].items()}, "pesos": q.PESOS}
    base["criterios"]["observabilidade"] = 100.0
    r["criterios"]["observabilidade"]["nota"] = 0.0
    g = q.gate(r, base, minimo_total=0)
    assert g["aprovado"], g["falhas"]
    assert g["semPiso"] == ["observabilidade"]
    # mas continua pesando no total: com o mínimo da própria linha de base, a queda aparece
    assert q.gate(r, base)["totalComparavel"] < q.gate(r, base)["totalBaselineComparavel"]


def test_cli_sai_com_1_quando_reprova(q, projeto, tmp_path, capsys):
    repo, arq = projeto
    base = tmp_path / "base.json"
    base.write_text(json.dumps({"criterios": {"descricao": 100.0, "cobertura": 100.0}, "pesos": q.PESOS}))
    cod = q.main(["--arq", str(arq), "--repo", str(repo), "--fonte", "ast", "--baseline", str(base)])
    assert cod == 1
    assert json.loads(capsys.readouterr().out)["gate"]["aprovado"] is False


# ---------------------------------------------------------------- órfãos e densidade seguem o que o código mostra

def _com_imports(repo, c_importa_a: bool):
    """a importa b (o modelo tem essa relação); c fica sozinho no código, ou importa a."""
    (repo / "src" / "a.py").write_text("from src import b\n", encoding="utf-8")
    (repo / "src" / "c.py").write_text("from src import a\n" if c_importa_a else "x = 1\n", encoding="utf-8")


def test_componente_que_o_codigo_tambem_deixa_sozinho_nao_e_orfao(q, projeto):
    """Achado no go-chi/chi: 16 de 35 middlewares só falam com a biblioteca padrão e o gate reprovava o mapa certo."""
    repo, arq = projeto
    _com_imports(repo, c_importa_a=False)
    r = q.avaliar(arq, repo, fonte="ast", listar=True)
    orf = r["criterios"]["orfaos"]
    assert orf["nota"] == 100.0 and "orfaos" not in r["reprovados"]
    assert "1 sem relação também no código (fonte ast), não contam" in orf["detalhe"]


def test_componente_ligado_no_codigo_e_sem_relacao_no_modelo_continua_orfao(q, projeto):
    repo, arq = projeto
    _com_imports(repo, c_importa_a=True)
    r = q.avaliar(arq, repo, fonte="ast", listar=True)
    assert r["criterios"]["orfaos"]["nota"] == pytest.approx(66.7, abs=0.1)
    assert r["reprovados"]["orfaos"] == ["compC"]


def test_alvo_de_relacoes_acompanha_o_codigo_quando_ele_oferece_menos_que_tres(q, projeto):
    repo, arq = projeto
    _com_imports(repo, c_importa_a=False)          # 1 par no código, 3 componentes: 0,67 por componente; piso 1
    m = q.avaliar(arq, repo, fonte="ast")["criterios"]["relacoes_media"]
    assert m["valor"] == 1.0 and m["nota"] == 100.0  # 3 pontas no modelo (a-b conta duas, a-dono uma) / 3
    assert "alvo 1" in m["detalhe"] and "o código mostra 0.67, teto 3" in m["detalhe"]


def test_sem_par_no_codigo_a_regra_fixa_continua(q, projeto):
    """Com zero pares não dá para distinguir código sem ligação de linguagem que a fonte não lê."""
    repo, arq = projeto
    c = q.avaliar(arq, repo, fonte="ast")["criterios"]
    assert c["orfaos"]["nota"] == pytest.approx(66.7, abs=0.1)
    assert "alvo 3" in c["relacoes_media"]["detalhe"] and c["relacoes_media"]["nota"] == pytest.approx(33.3, abs=0.1)
