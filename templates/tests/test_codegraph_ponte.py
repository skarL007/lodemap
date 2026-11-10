"""codegraph_ponte.py: fonte ast (Python e JS num mini repositório), fonte codegraph (db mínimo), confiança e impacto."""
from __future__ import annotations

import importlib.util
import json
import os
import sqlite3
import sys
from collections import Counter
from pathlib import Path

import pytest


def _scripts() -> Path | None:
    for c in (os.environ.get("LODEMAP_SKILL"), Path(__file__).resolve().parents[2],
              Path.home() / ".claude" / "skills" / "lodemap"):
        if c and (Path(c) / "scripts" / "codegraph_ponte.py").is_file():
            return Path(c) / "scripts"
    return None


SCRIPTS = _scripts()
pytestmark = pytest.mark.skipif(SCRIPTS is None, reason="scripts/codegraph_ponte.py da skill não encontrado")


@pytest.fixture(scope="module")
def p():
    sys.path.insert(0, str(SCRIPTS))
    spec = importlib.util.spec_from_file_location("codegraph_ponte", SCRIPTS / "codegraph_ponte.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def mini(tmp_path):
    """Python em app/ (imports absolutos, relativos e from-pacote-import-submódulo) e JS em web/."""
    repo = tmp_path / "repo"
    (repo / "app" / "pac").mkdir(parents=True)
    (repo / "web" / "lib").mkdir(parents=True)
    (repo / "node_modules" / "x").mkdir(parents=True)
    (repo / "app" / "__init__.py").write_text("")
    (repo / "app" / "main.py").write_text('"""Entrada."""\nimport util\nfrom pac import motor\nfrom .util import f\nimport os\n')
    (repo / "app" / "util.py").write_text("def f():\n    pass\n")
    (repo / "app" / "pac" / "__init__.py").write_text("")
    (repo / "app" / "pac" / "motor.py").write_text('"""Motor."""\nfrom ..util import f\n')
    (repo / "web" / "app.js").write_text("import { a } from './lib/a.js';\nconst b = require('./lib/b');\n"
                                         "import('./lib').then(() => 0);\nimport x from 'react';\n")
    (repo / "web" / "lib" / "a.js").write_text("export const a = 1;\n")
    (repo / "web" / "lib" / "b.ts").write_text("export const b = 2;\n")
    (repo / "web" / "lib" / "index.js").write_text("export default 3;\n")
    (repo / "node_modules" / "x" / "i.js").write_text("import './y';\n")
    return repo


def test_ast_python_e_js(p, mini):
    arestas, fonte = p.carregar_arestas(mini, "auto")
    assert fonte == "ast"  # sem .codegraph/codegraph.db
    assert arestas[("app/main.py", "app/util.py")]["imports"] == 2   # import util e from .util import f
    assert ("app/main.py", "app/pac/motor.py") in arestas             # from pac import motor (submódulo)
    assert ("app/pac/motor.py", "app/util.py") in arestas             # from ..util import f
    assert not any(b.startswith("os") for _, b in arestas)             # biblioteca padrão fica de fora
    assert ("web/app.js", "web/lib/a.js") in arestas
    assert ("web/app.js", "web/lib/b.ts") in arestas                   # require sem extensão
    assert ("web/app.js", "web/lib/index.js") in arestas               # import('./lib') -> index.js
    assert not any(a.startswith("node_modules") for a, _ in arestas)
    assert all(set(t) == {"imports"} for t in arestas.values())         # ast só vê imports


def test_confianca(p):
    assert p.confianca(Counter(calls=3)) == "alta"
    assert p.confianca(Counter(calls=2)) == "media"
    assert p.confianca(Counter(imports=5)) == "media"
    assert p.confianca(Counter(calls=1)) == "baixa"
    assert p.confianca(Counter(imports=1)) == "baixa"
    assert p.confianca(Counter(imports=1), "ast") == "media"      # no ast o import é fato, não palpite


def _ws(repo: Path):
    def comp(i, ident, codigo):
        return {"id": str(i), "name": ident, "properties": {"structurizr.dsl.identifier": ident, "codigo": codigo}}

    ws = {"model": {"softwareSystems": [{"id": "1", "name": "S", "containers": [{"id": "2", "name": "C", "components": [
        comp(10, "cMain", "app/main.py"), comp(11, "cUtil", "app/util.py"), comp(12, "cPac", "app/pac/"),
        comp(13, "cWeb", "web/")]}]}]}}
    arq = repo / "arq"
    arq.mkdir()
    (arq / "workspace.json").write_text(json.dumps(ws))
    (arq / "lodemap.json").write_text(json.dumps({"raiz_codigo": "app"}))
    return arq


def test_relacoes_e_impacto_com_ast(p, mini):
    arq = _ws(mini)
    info = p.analisar(arq, mini, "ast")
    rel = p.relatorio_relacoes(info)
    par = {(x["de"], x["para"]): x for x in rel["pares"]}
    assert par[("cMain", "cUtil")]["arestas"] == 2 and par[("cMain", "cUtil")]["confianca"] == "media"
    assert par[("cMain", "cPac")]["confianca"] == "media" and not par[("cMain", "cPac")]["noModelo"]
    assert rel["fonte"] == "ast"
    imp = p.impacto(info, "app/util.py", profundidade=2)
    assert imp["componenteDono"] == ["cUtil"]
    assert {a["componente"]: a["distancia"] for a in imp["afetados"]} == {"cMain": 1, "cPac": 1}


def test_arquivo_ambiguo_fica_fora(p):
    comps = [{"ident": n, "props": {"codigo": "app/server.py"}} for n in ("x1", "x2")]
    comps.append({"ident": "x3", "props": {"codigo": "app/"}})
    mapa, amb, sem = p.mapear_arquivos(["app/server.py", "app/outro.py", "lib/z.py"], comps, "")
    assert amb == {"app/server.py"} and mapa == {"app/outro.py": "x3"} and sem == {"lib/z.py"}


def _db(caminho: Path):
    con = sqlite3.connect(caminho)
    con.executescript("""
        CREATE TABLE nodes (id TEXT PRIMARY KEY, kind TEXT NOT NULL, name TEXT NOT NULL, qualified_name TEXT NOT NULL,
            file_path TEXT NOT NULL, language TEXT NOT NULL, start_line INTEGER NOT NULL, end_line INTEGER NOT NULL,
            docstring TEXT, signature TEXT);
        CREATE TABLE edges (id INTEGER PRIMARY KEY AUTOINCREMENT, source TEXT NOT NULL, target TEXT NOT NULL,
            kind TEXT NOT NULL, metadata TEXT, line INTEGER, col INTEGER, provenance TEXT);
        CREATE TABLE files (path TEXT PRIMARY KEY, language TEXT NOT NULL, node_count INTEGER DEFAULT 0,
            generated INTEGER NOT NULL DEFAULT 0);
    """)
    con.executemany("INSERT INTO files (path, language) VALUES (?, 'python')", [("app/main.py",), ("app/util.py",)])
    con.executemany("INSERT INTO nodes VALUES (?,?,?,?,?,?,?,?,?,?)", [
        ("file:app/main.py", "file", "main.py", "app/main.py", "app/main.py", "python", 1, 20, "Entrada do app.", None),
        ("fn:main", "function", "main", "main", "app/main.py", "python", 3, 9, "Roda o app.\nMais.", None),
        ("fn:f", "function", "f", "f", "app/util.py", "python", 1, 4, None, None)])
    con.executemany("INSERT INTO edges (source, target, kind) VALUES (?,?,?)",
                    [("fn:main", "fn:f", "calls")] * 3 + [("fn:main", "fn:f", "instantiates"),
                                                          ("fn:main", "fn:f", "references")])
    con.commit()
    con.close()


def test_fonte_codegraph_e_inventario(p, mini):
    (mini / ".codegraph").mkdir()
    _db(mini / ".codegraph" / "codegraph.db")
    arestas, fonte = p.carregar_arestas(mini, "auto")
    assert fonte == "codegraph"
    assert arestas[("app/main.py", "app/util.py")] == Counter(calls=4)  # calls + instantiates; references fica de fora
    inv = p.rascunho_inventario(mini, None)
    main = next(a for a in inv["arquivos"] if a["caminho"] == "app/main.py")
    assert inv["fonte"] == "codegraph" and main["docstringModulo"] == "Entrada do app."
    assert main["docstringPrimeiro"] == "Roda o app." and main["simbolos"][0]["nome"] == "main"


def test_codegraph_forcado_sem_indice_falha(p, mini):
    with pytest.raises(SystemExit):
        p.carregar_arestas(mini, "codegraph")
    assert not (mini / ".codegraph").exists()  # a skill nunca cria o índice sozinha


def test_inventario_ast(p, mini):
    inv = p.rascunho_inventario(mini, None, "ast")
    main = next(a for a in inv["arquivos"] if a["caminho"] == "app/main.py")
    assert inv["fonte"] == "ast" and main["docstringModulo"] == "Entrada."
    assert any(a["caminho"] == "web/lib/a.js" for a in inv["arquivos"])
