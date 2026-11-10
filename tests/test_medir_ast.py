"""Precisão e recall do modo ast da ponte (scripts/codegraph_ponte.py), medidos por scripts/medir_ast.py.

Camada A (gabarito rotulado à mão, tests/fixtures/ast_precisao/<linguagem>/gabarito.json): o piso abaixo vale para TODA
linguagem. Pisos escolhidos: precisão >= 0,95 e recall >= 0,90. Medido hoje: 1,000 / 1,000 em todas as oito linguagens,
então o piso tem folga e só cai com regressão real. O gabarito foi escrito já conhecendo o extrator (ver
references/precisao-ast.md): ele prova que um erro corrigido não volta, não que o extrator acerta em código desconhecido.

Cada bug que a medição achou tem um teste unitário `test_bug_*` aqui, com um mini-repositório em tmp_path; ele FALHA na
ponte original (85fc0a6) e passa na corrigida. Os `test_guarda_*` passam nas duas: travam o excesso da correção (por
exemplo, a regra da stdlib não pode engolir um irmão com nome próprio)."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from lodemap import RAIZ

sys.path.insert(0, str(RAIZ / "scripts"))
import codegraph_ponte as cp  # noqa: E402
import medir_ast  # noqa: E402

PISO_PRECISAO = 0.95
PISO_RECALL = 0.90
LINGUAGENS = ["c", "csharp", "go", "java", "javascript", "kotlin", "python", "rust"]


def _escrever(raiz: Path, arquivos: dict[str, str]) -> Path:
    for rel, texto in arquivos.items():
        p = raiz / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(texto, encoding="utf-8", newline="\n")
    return raiz


def _pares(raiz: Path) -> set[tuple[str, str]]:
    return {par for par in cp.arestas_ast(raiz)}


# ------------------------------------------------------------------ camada A: o piso

@pytest.fixture(scope="module")
def camada_a():
    return medir_ast.medir_camada_a()


def test_camada_a_cobre_as_oito_linguagens(camada_a):
    assert sorted(camada_a) == LINGUAGENS


@pytest.mark.parametrize("linguagem", LINGUAGENS)
def test_camada_a_piso_de_precisao_e_recall(camada_a, linguagem):
    r = camada_a[linguagem]
    assert r["arestasGabarito"] > 0, "gabarito vazio não mede nada"
    assert r["precisao"] >= PISO_PRECISAO, (linguagem, r["precisao"], r["erros"]["fp"])
    assert r["recall"] >= PISO_RECALL, (linguagem, r["recall"], r["erros"]["fn"])


@pytest.mark.parametrize("linguagem", LINGUAGENS)
def test_camada_a_nenhum_limite_conhecido_foi_superado_em_silencio(camada_a, linguagem):
    # Um limite que o extrator já acerta ("superado") tem de sair do gabarito, senão o texto de limites mente.
    assert camada_a[linguagem]["limitesConhecidos"]["superados"] == []


def test_gabaritos_apontam_para_arquivos_que_existem():
    for pasta in sorted(medir_ast.FIXTURES.iterdir()):
        if not (pasta / "gabarito.json").is_file():
            continue
        gab = json.loads((pasta / "gabarito.json").read_text(encoding="utf-8"))
        for a, b in gab["arestas"]:
            assert (pasta / a).is_file() and (pasta / b).is_file(), (pasta.name, a, b)


def test_limite_conhecido_fica_fora_da_conta_e_e_reportado(tmp_path):
    # `a.py` importa `b.py`: o extrator acha a aresta. O gabarito só lista a aresta de `c.py` e declara (a, b) como
    # FP conhecido: o par some da conta e aparece em fpConhecidos.
    _escrever(tmp_path, {"a.py": "import b\n", "b.py": "X = 1\n", "c.py": "import b\n",
                         "gabarito.json": json.dumps({"linguagem": "python", "arestas": [["c.py", "b.py"]],
                                                      "limites": [{"par": ["a.py", "b.py"], "tipo": "fp", "motivo": "teste"}]})})
    r = medir_ast.medir_fixture(tmp_path, cp)
    assert (r["tp"], r["fp"], r["fn"]) == (1, 0, 0)
    assert r["limitesConhecidos"]["fpConhecidos"] == [["a.py", "b.py"]]


def test_erro_real_sem_limite_conta_como_fp_e_fn(tmp_path):
    _escrever(tmp_path, {"a.py": "import b\n", "b.py": "X = 1\n", "c.py": "X = 1\n",
                         "gabarito.json": json.dumps({"linguagem": "python", "arestas": [["a.py", "c.py"]]})})
    r = medir_ast.medir_fixture(tmp_path, cp)
    assert (r["tp"], r["fp"], r["fn"]) == (0, 1, 1)
    assert r["precisao"] == 0.0 and r["recall"] == 0.0


def test_ponte_alternativa_e_carregada_por_caminho(tmp_path):
    copia = tmp_path / "ponte_copia.py"
    copia.write_text((RAIZ / "scripts" / "codegraph_ponte.py").read_text(encoding="utf-8"), encoding="utf-8")
    ponte = medir_ast.carregar_ponte(copia)
    assert ponte is not cp and hasattr(ponte, "arestas_ast")
    assert medir_ast.medir_camada_a(ponte=ponte, so="go")["go"]["precisao"] == 1.0


# ------------------------------------------------------------------ camada B (índice fictício do CodeGraph)

def _indice(db: Path, arquivos: list[str], arestas: list[tuple[str, str, str]]) -> None:
    import sqlite3
    con = sqlite3.connect(str(db))
    con.execute("CREATE TABLE files (path TEXT)")
    con.execute("CREATE TABLE nodes (id INTEGER PRIMARY KEY, file_path TEXT)")
    con.execute("CREATE TABLE edges (source INTEGER, target INTEGER, kind TEXT)")
    ids = {}
    for i, f in enumerate(arquivos, 1):
        con.execute("INSERT INTO files VALUES (?)", (f,))
        con.execute("INSERT INTO nodes VALUES (?, ?)", (i, f))
        ids[f] = i
    for a, b, k in arestas:
        con.execute("INSERT INTO edges VALUES (?, ?, ?)", (ids[a], ids[b], k))
    con.commit()
    con.close()


def test_camada_b_separa_tp_fp_duro_fp_corroborado_e_fn(tmp_path):
    _escrever(tmp_path, {"a.py": "import b\nimport c\nimport d\n", "b.py": "X = 1\n", "c.py": "X = 1\n",
                         "d.py": "X = 1\n", "e.py": "import b\n"})
    db = tmp_path / "idx.db"
    _indice(db, ["a.py", "b.py", "c.py", "d.py", "e.py"],
            [("a.py", "b.py", "imports"),      # TP
             ("a.py", "c.py", "calls"),        # extrator acha, índice só tem chamada: FP corroborado
             ("e.py", "d.py", "imports")])     # índice acha, extrator não: FN
    r = medir_ast.medir_repo(tmp_path, cp, db)["linguagens"]["python"]
    assert (r["tp"], r["fpCorroborado"], r["fn"]) == (1, 1, 1)
    # a->d e e->b: o extrator acha, o índice não tem aresta nenhuma
    assert r["fpDuro"] == 2
    assert r["precisaoImports"] == round(1 / 4, 4) and r["precisaoAmpla"] == round(2 / 4, 4)
    assert r["recall"] == round(1 / 2, 4)


def test_camada_b_sem_indice_diz_que_nao_tem(tmp_path):
    assert "erro" in medir_ast.medir_repo(tmp_path, cp, tmp_path / "nao_existe.db")


def test_camada_b_so_le_o_indice(tmp_path):
    db = tmp_path / "idx.db"
    _indice(db, ["a.py"], [])
    antes = db.read_bytes()
    medir_ast.referencia_codegraph(db)
    assert db.read_bytes() == antes


# ------------------------------------------------------------------ CLI

def test_cli_imprime_tabela_e_grava_json(tmp_path):
    saida = tmp_path / "medida.json"
    p = subprocess.run([sys.executable, "-I", str(RAIZ / "scripts" / "medir_ast.py"), "--saida", str(saida)],
                       capture_output=True, text=True, encoding="utf-8", timeout=120)
    assert p.returncode == 0, p.stderr
    for lg in LINGUAGENS:
        assert lg in p.stdout
    dados = json.loads(saida.read_text(encoding="utf-8"))
    assert sorted(dados["camadaA"]) == LINGUAGENS
    assert dados["camadaA"]["rust"]["precisao"] >= PISO_PRECISAO


def test_pytest_nao_varre_as_fixtures():
    # Fixtures são código-alvo, não testes: nenhum arquivo delas pode ser coletável pelo pytest.
    coletaveis = [p for p in medir_ast.FIXTURES.rglob("*.py")
                  if p.name.startswith("test_") or p.name.endswith("_test.py") or p.name == "conftest.py"]
    assert coletaveis == []


# ------------------------------------------------------------------ um teste por bug corrigido

def test_bug_js_import_em_comentario_string_e_template_nao_e_aresta(tmp_path):
    _escrever(tmp_path, {
        "a.js": ("// import x from './fantasma'\n/* require('./fantasma') */\n"
                 "const s = \"import y from './fantasma'\";\nconst t = `\nimport z from './fantasma'\n`;\n"
                 "import real from './real';\n"),
        "real.js": "export default 1;\n",
        "fantasma.js": "export default 2;\n",
    })
    assert _pares(tmp_path) == {("a.js", "real.js")}


def test_guarda_js_import_de_verdade_depois_de_string_com_aspas_continua_sendo_aresta(tmp_path):
    _escrever(tmp_path, {"a.js": "const a = \"it's\";\nimport r from './r';\nconst b = 'x\"y';\nimport q from './q';\n",
                         "r.js": "export default 1;\n", "q.js": "export default 2;\n"})
    assert _pares(tmp_path) == {("a.js", "r.js"), ("a.js", "q.js")}


def test_bug_ts_esm_com_extensao_js_aponta_para_o_ts(tmp_path):
    _escrever(tmp_path, {
        "src/a.ts": "import { b } from './b.js';\nimport { c } from './c.js';\nimport { d } from './d.js';\n",
        "src/b.ts": "export const b = 1;\n",
        "src/c.tsx": "export const c = 1;\n",
        "src/d.mts": "export const d = 1;\n",
    })
    assert _pares(tmp_path) == {("src/a.ts", "src/b.ts"), ("src/a.ts", "src/c.tsx")}


def test_bug_ts_mjs_aponta_para_mts(tmp_path):
    _escrever(tmp_path, {"a.mts": "import { d } from './d.mjs';\n", "d.mts": "export const d = 1;\n"})
    assert _pares(tmp_path) == {("a.mts", "d.mts")}


def test_guarda_ts_js_real_tem_prioridade_sobre_o_ts(tmp_path):
    _escrever(tmp_path, {"a.ts": "import { b } from './b.js';\n", "b.js": "exports.b = 1;\n", "b.ts": "export const b = 1;\n"})
    assert _pares(tmp_path) == {("a.ts", "b.js")}


def test_bug_java_import_explicito_oculta_homonimo_do_curinga(tmp_path):
    _escrever(tmp_path, {
        "src/a/Main.java": ("package a;\nimport b.*;\nimport c.Lista;\n\nclass Main { Lista l; }\n"),
        "src/b/Lista.java": "package b;\npublic class Lista {}\n",
        "src/c/Lista.java": "package c;\npublic class Lista {}\n",
    })
    assert _pares(tmp_path) == {("src/a/Main.java", "src/c/Lista.java")}


def test_bug_java_curinga_continua_valendo_para_o_que_o_import_explicito_nao_cobre(tmp_path):
    _escrever(tmp_path, {
        "src/a/Main.java": "package a;\nimport b.*;\nimport c.Lista;\n\nclass Main { Lista l; Mapa m; }\n",
        "src/b/Lista.java": "package b;\npublic class Lista {}\n",
        "src/b/Mapa.java": "package b;\npublic class Mapa {}\n",
        "src/c/Lista.java": "package c;\npublic class Lista {}\n",
    })
    assert _pares(tmp_path) == {("src/a/Main.java", "src/c/Lista.java"), ("src/a/Main.java", "src/b/Mapa.java")}


def test_guarda_kotlin_import_com_alias_nao_oculta_o_curinga(tmp_path):
    _escrever(tmp_path, {
        "src/a/Main.kt": "package a\nimport b.*\nimport c.Lista as Outra\n\nclass Main { val l: Lista? = null; val o: Outra? = null }\n",
        "src/b/Lista.kt": "package b\nclass Lista\n",
        "src/c/Lista.kt": "package c\nclass Lista\n",
    })
    assert _pares(tmp_path) == {("src/a/Main.kt", "src/b/Lista.kt"), ("src/a/Main.kt", "src/c/Lista.kt")}


def test_bug_python_import_da_stdlib_dentro_de_pacote_nao_pega_homonimo_local(tmp_path):
    _escrever(tmp_path, {
        "app/__init__.py": "",
        "app/logging.py": "Z = 1\n",
        "app/util.py": "import logging\nimport os.path\n",
        "app/types.py": "X = 1\n",
    })
    assert _pares(tmp_path) == set()


def test_guarda_python_irmao_com_nome_proprio_continua_resolvendo_dentro_de_pacote(tmp_path):
    _escrever(tmp_path, {"app/__init__.py": "", "app/hack.py": "import irmao\n", "app/irmao.py": "W = 1\n"})
    assert _pares(tmp_path) == {("app/hack.py", "app/irmao.py")}


def test_guarda_python_homonimo_da_stdlib_em_pasta_sem_init_continua_resolvendo(tmp_path):
    # pasta sem __init__.py não é pacote: pode estar no sys.path, e o extrator mantém o comportamento (limite documentado)
    _escrever(tmp_path, {"s/a.py": "import json\n", "s/json.py": "Y = 1\n"})
    assert _pares(tmp_path) == {("s/a.py", "s/json.py")}


def test_bug_python_monorepo_pacote_de_topo_unico_resolve_de_outra_raiz(tmp_path):
    _escrever(tmp_path, {
        "libs/core/mylib/__init__.py": "from .service import servir\n",
        "libs/core/mylib/service.py": "def servir():\n    return 1\n",
        "apps/web/run.py": "import mylib\nfrom mylib.service import servir\n",
    })
    assert _pares(tmp_path) == {("libs/core/mylib/__init__.py", "libs/core/mylib/service.py"),
                                ("apps/web/run.py", "libs/core/mylib/__init__.py"),
                                ("apps/web/run.py", "libs/core/mylib/service.py")}


def test_guarda_python_monorepo_nome_de_topo_ambiguo_nao_gera_aresta(tmp_path):
    _escrever(tmp_path, {"libs/a/dup/__init__.py": "A = 1\n", "libs/b/dup/__init__.py": "B = 1\n",
                         "apps/web/run.py": "import dup\n"})
    assert _pares(tmp_path) == set()


def test_guarda_python_monorepo_nome_da_stdlib_nao_vai_para_pacote_de_outra_raiz(tmp_path):
    _escrever(tmp_path, {"libs/x/json/__init__.py": "J = 1\n", "apps/web/run.py": "import json\n"})
    assert _pares(tmp_path) == set()


def test_bug_python_arquivo_com_escape_invalido_nao_polui_o_stderr(tmp_path):
    _escrever(tmp_path, {"a.py": "import b\nR = '\\l'\n", "b.py": "X = 1\n"})
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("error")  # se a ponte deixasse o aviso passar, isto levantaria
        assert _pares(tmp_path) == {("a.py", "b.py")}


RUST_MOD_EM_LINHA = {
    "Cargo.toml": '[package]\nname = "demo"\nversion = "0.1.0"\n',
    "src/lib.rs": "pub mod util;\npub fn f() {}\n",
    "src/util/mod.rs": "pub mod plain;\npub fn fmt() {}\n",
    "src/util/plain.rs": "pub fn p() -> i32 { 1 }\n\n#[cfg(test)]\nmod tests {\n    use super::*;\n    use super::p;\n}\n",
}


def test_bug_rust_use_super_dentro_de_mod_em_linha_aponta_para_o_proprio_arquivo(tmp_path):
    _escrever(tmp_path, RUST_MOD_EM_LINHA)
    # `use super::*` em `mod tests { }` de plain.rs é o próprio plain.rs, nunca util/mod.rs
    assert _pares(tmp_path) == {("src/lib.rs", "src/util/mod.rs"), ("src/util/mod.rs", "src/util/plain.rs")}


def test_guarda_rust_super_fora_de_mod_em_linha_continua_apontando_para_o_pai(tmp_path):
    arqs = dict(RUST_MOD_EM_LINHA)
    arqs["src/util/plain.rs"] = "use super::fmt;\npub fn p() -> i32 { 1 }\n"
    _escrever(tmp_path, arqs)
    assert ("src/util/plain.rs", "src/util/mod.rs") in _pares(tmp_path)


def test_bug_rust_super_super_dentro_de_mod_em_linha_sobe_um_nivel_a_menos(tmp_path):
    arqs = dict(RUST_MOD_EM_LINHA)
    arqs["src/util/plain.rs"] = "pub fn p() -> i32 { 1 }\n\nmod tests {\n    use super::super::fmt;\n}\n"
    _escrever(tmp_path, arqs)
    assert ("src/util/plain.rs", "src/util/mod.rs") in _pares(tmp_path)
