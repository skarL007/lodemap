"""`ignorar` do lodemap.json: o candidato a módulo que casa um glob dela não é módulo em lugar nenhum.

Go guarda o teste ao lado do código (`mux_test.go` junto de `mux.go`); sem a lista, o glob `*.go` transformava
cada teste em módulo e o gate de cobertura exigia todos no modelo. Todo ponto que transforma os globs de "modulos"
em módulos precisa concordar: o teste de cobertura entregue, o `arq_comum` (fora_do_modelo), o diff incremental, o
gancho do git, o esqueleto, a ponte do CodeGraph, o inventário, a qualidade e a contagem do plano de permissão.
"""
from __future__ import annotations

import importlib.util
import itertools
import json
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path

import pytest

from lodemap import RAIZ, permissao

SCRIPTS = RAIZ / "templates" / "structurizr" / "scripts"
TESTE_COBERTURA = RAIZ / "templates" / "tests" / "test_arquitetura_cobertura.py"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(RAIZ / "scripts"))
import arq_comum  # noqa: E402
import codegraph_ponte as cp  # noqa: E402
import esqueleto  # noqa: E402
import inventario  # noqa: E402
import lodemap_diff  # noqa: E402
import novo_mapa  # noqa: E402
import qualidade  # noqa: E402

pytestmark = pytest.mark.skipif(not shutil.which("git"), reason="precisa do git")

GO_GLOBS = ["*.go", "sub/*.go"]
IGNORAR_GO = ["**/*_test.go"]
DOIS = ["a.go", "sub/b.go"]
QUATRO = ["a.go", "a_test.go", "sub/b.go", "sub/b_test.go"]


def _git(repo: Path, *args: str) -> str:
    r = subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "-C", str(repo), *args],
                       check=True, capture_output=True, text=True, encoding="utf-8")
    return r.stdout.strip()


def _commitar(repo: Path, msg: str = "mudanca") -> None:
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", msg)


def _escrever(repo: Path, arquivos: dict[str, str]) -> None:
    for rel, texto in arquivos.items():
        f = repo / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(texto, encoding="utf-8")


DSL_A = ('sistema = softwareSystem "S" {\n    app = container "App" "d" "Go" {\n'
         '        compA = component "A" "d" "Go" "Pronto" {\n            properties {\n'
         '                "status" "Pronto"\n                "codigo" "a.go"\n            }\n        }\n    }\n}\n')


def _repo(tmp_path: Path, arquivos: dict[str, str], modulos: list[str], ignorar: list[str] | None,
          raiz_codigo: str = "") -> tuple[Path, Path]:
    """Repositório git com os arquivos dados, um mapa mínimo (lodemap.json, modelo, scripts) e o teste de cobertura
    instanciado em tests/. `ignorar=None` omite a chave (mapa antigo)."""
    repo = tmp_path / "repo"
    arq = repo / "arq"
    _escrever(repo, arquivos)
    (arq / "model").mkdir(parents=True)
    (arq / "scripts").mkdir()
    cfg = {"projeto": "T", "raiz_codigo": raiz_codigo, "modulos": modulos}
    if ignorar is not None:
        cfg["ignorar"] = ignorar
    (arq / "lodemap.json").write_text(json.dumps(cfg), encoding="utf-8")
    (arq / "model" / "componentes.dsl").write_text(DSL_A, encoding="utf-8")
    for nome in ("arq_comum.py", "lodemap_diff.py", "lodemap_decidir.py", "lodemap_gancho.py"):
        shutil.copy2(SCRIPTS / nome, arq / "scripts" / nome)
    (repo / "tests").mkdir()
    (repo / "tests" / "test_arquitetura_cobertura.py").write_text(
        TESTE_COBERTURA.read_text(encoding="utf-8").replace("{{ARQ_REL}}", "arq"), encoding="utf-8")
    (repo / ".gitignore").write_text(".lodemap/\n__pycache__/\n", encoding="utf-8")
    _git(repo, "init", "-q")
    _commitar(repo, "base")
    return repo, arq


def _go(tmp_path: Path, ignorar: list[str] | None = IGNORAR_GO) -> tuple[Path, Path]:
    arquivos = {nome: "package x\n" for nome in QUATRO}
    return _repo(tmp_path, arquivos, GO_GLOBS, ignorar)


def _teste_instanciado(repo: Path, nome: str = "cobertura_ignorar_t"):
    spec = importlib.util.spec_from_file_location(nome, repo / "tests" / "test_arquitetura_cobertura.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _carregar_gancho(arq: Path):
    spec = importlib.util.spec_from_file_location("lodemap_gancho_ignorar_t", arq / "scripts" / "lodemap_gancho.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    m.ARQ = arq
    return m


def _por_ponto(repo: Path, arq: Path, tmp_path: Path) -> dict[str, list[str]]:
    """Os módulos que cada ponto de enumeração enxerga (pastas com a barra final, como o teste de cobertura)."""
    cfg = json.loads((arq / "lodemap.json").read_text(encoding="utf-8"))
    globs = cfg["modulos"]
    j =tmp_path / "inventario.json"
    inventario.main(["--repo", str(repo), "--arq", "arq", "--json", str(j)])
    inv = [m["caminho"] for m in json.loads(j.read_text(encoding="utf-8"))["modulos"]]
    return {
        "cobertura": _teste_instanciado(repo).alvos(),
        "arq_comum": arq_comum.modulos_do_repo(arq, repo),
        "esqueleto.modulos_dos_globs": esqueleto.modulos_dos_globs(repo, globs, cp._globs_ignorar(arq)),
        "esqueleto.sugerir": sorted(c["modulo"] for c in esqueleto.sugerir(repo, arq, fonte="ast")["componentes"]),
        "inventario": sorted(inv),
        "qualidade": qualidade._alvos(repo, globs, qualidade.ponte._ignorar_da_config(cfg)),
        "permissao": permissao.contar_modulos(repo, "arq")["modulos"],  # só a contagem
    }


def _concordam(pontos: dict, esperado: list[str]) -> None:
    for ponto, lista in pontos.items():
        if ponto == "permissao":
            assert lista == len(esperado), f"{ponto}: {lista} módulos"
        else:
            assert lista == esperado, ponto


# ------------------------------------------------------------------------------------------------ fixture Go

def test_com_ignorar_todo_ponto_enxerga_exatamente_2_modulos(tmp_path):
    repo, arq = _go(tmp_path)
    _concordam(_por_ponto(repo, arq, tmp_path), DOIS)


def test_sem_ignorar_o_comportamento_nao_muda_e_sao_4_modulos(tmp_path):
    for ignorar in (None, []):
        pasta = tmp_path / ("ausente" if ignorar is None else "vazia")
        pasta.mkdir()
        repo, arq = _go(pasta, ignorar)
        _concordam(_por_ponto(repo, arq, pasta), QUATRO)


def test_fora_do_modelo_nao_exige_o_teste_do_go(tmp_path):
    repo, arq = _go(tmp_path)
    assert arq_comum.fora_do_modelo(arq, repo) == ["sub/b.go"], "a.go está no modelo; a_test.go e b_test.go não contam"
    teste = _teste_instanciado(repo)
    pares = teste.caminhos_dos_componentes()
    assert [a for a in teste.alvos() if teste.quem_cobre(a, pares) is None] == ["sub/b.go"]


def test_sem_ignorar_os_testes_voltam_a_ser_cobrados(tmp_path):
    repo, arq = _go(tmp_path, None)
    assert arq_comum.fora_do_modelo(arq, repo) == ["a_test.go", "sub/b.go", "sub/b_test.go"]


def test_sugerir_nao_cria_componente_nem_relacao_para_teste(tmp_path):
    repo, arq = _go(tmp_path)
    s = esqueleto.sugerir(repo, arq, fonte="ast")
    assert sorted(c["modulo"] for c in s["componentes"]) == DOIS
    d = esqueleto.rascunho(repo, arq, fonte="ast", gravar=False)
    assert sorted(c["modulo"] for c in d["componentes"]) == DOIS


def test_rascunho_de_inventario_da_ponte_nao_traz_o_teste(tmp_path):
    repo, arq = _go(tmp_path)
    itens = cp.rascunho_inventario(repo, arq, fonte="ast")["arquivos"]
    assert sorted(i["caminho"] for i in itens) == DOIS
    assert {i["modulo"] for i in itens} == set(DOIS)


def test_diff_de_commit_so_de_teste_nao_tem_modulo_mudado_e_nao_e_relevante(tmp_path):
    repo, arq = _go(tmp_path)
    lodemap_diff.marcar(arq)
    _escrever(repo, {"a_test.go": "package x\n// mais um caso\n"})
    _commitar(repo)
    d = lodemap_diff.diff(arq)
    assert d["modo"] == "incremental"
    assert d["modulosNovos"] == d["modulosMudados"] == d["modulosRemovidos"] == []
    assert lodemap_diff.relevante(arq) is False
    # um teste novo e um teste apagado também não aparecem
    _escrever(repo, {"sub/c_test.go": "package x\n"})
    (repo / "sub" / "b_test.go").unlink()
    _commitar(repo)
    d = lodemap_diff.diff(arq)
    assert d["modulosNovos"] == d["modulosMudados"] == d["modulosRemovidos"] == []
    assert lodemap_diff.relevante(arq) is False
    # código de verdade segue sendo visto
    _escrever(repo, {"a.go": "package x\n// mudou\n"})
    _commitar(repo)
    assert lodemap_diff.diff(arq)["modulosMudados"] == ["a.go"]
    assert lodemap_diff.relevante(arq) is True


def test_diff_sem_ignorar_ve_o_teste_como_modulo(tmp_path):
    repo, arq = _go(tmp_path, None)
    lodemap_diff.marcar(arq)
    _escrever(repo, {"a_test.go": "package x\n// mais um caso\n"})
    _commitar(repo)
    assert lodemap_diff.diff(arq)["modulosMudados"] == ["a_test.go"]
    assert lodemap_diff.relevante(arq) is True


def test_gancho_commit_so_de_teste_nao_toca_a_arquitetura(tmp_path):
    repo, arq = _go(tmp_path)
    m = _carregar_gancho(arq)
    _escrever(repo, {"sub/b_test.go": "package x\n// caso\n"})
    _commitar(repo)
    assert m.commit_toca_arquitetura() is False
    _escrever(repo, {"sub/b.go": "package x\n// mudou\n"})
    _commitar(repo)
    assert m.commit_toca_arquitetura() is True


def test_gancho_sem_ignorar_commit_de_teste_toca(tmp_path):
    repo, arq = _go(tmp_path, None)
    m = _carregar_gancho(arq)
    _escrever(repo, {"sub/b_test.go": "package x\n// caso\n"})
    _commitar(repo)
    assert m.commit_toca_arquitetura() is True


def test_relacoes_e_impacto_da_ponte_ignoram_o_teste(tmp_path, monkeypatch):
    repo, arq = _go(tmp_path)
    ws = {"model": {"softwareSystems": [{"containers": [{"id": "1", "name": "App", "components": [
        {"id": "2", "name": "A", "properties": {"structurizr.dsl.identifier": "compA", "codigo": "a.go, a_test.go"}},
        {"id": "3", "name": "B", "properties": {"structurizr.dsl.identifier": "compB", "codigo": "sub/"}}]}]}]}}
    (arq / "workspace.json").write_text(json.dumps(ws), encoding="utf-8")
    arestas = {("a_test.go", "sub/b.go"): Counter(calls=1), ("a.go", "sub/b.go"): Counter(imports=1)}
    monkeypatch.setattr(cp, "carregar_arestas", lambda *a, **k: (dict(arestas), "ast"))
    info = cp.analisar(arq, repo, "ast")
    assert set(info["arestas"]) == {("a.go", "sub/b.go")}
    assert "a_test.go" not in info["mapa"] and "a_test.go" not in info["sem"]
    assert cp.impacto(info, "sub/b.go")["afetados"][0]["arquivos"] == ["a.go"]
    # sem a lista, o teste entra nas contas como antes
    cfg = json.loads((arq / "lodemap.json").read_text(encoding="utf-8"))
    del cfg["ignorar"]
    (arq / "lodemap.json").write_text(json.dumps(cfg), encoding="utf-8")
    assert set(cp.analisar(arq, repo, "ast")["arestas"]) == set(arestas)


def test_plano_sem_mapa_de_repositorio_go_nao_conta_os_testes(tmp_path):
    repo = tmp_path / "go"
    _escrever(repo, {f"src/{n}": "package x\n" for n in ("mux.go", "mux_test.go", "tree.go", "tree_test.go")})
    m = permissao.contar_modulos(repo)
    assert m["modulos"] == 2 and m["ignorar"] == ["**/*_test.go", "**/_*/**", "**/testdata/**"]


def test_plano_com_mapa_usa_o_ignorar_do_mapa(tmp_path):
    repo, arq = _go(tmp_path)
    m = permissao.contar_modulos(repo, "arq")
    assert m["fonte"] == "inventario.py" and m["modulos"] == 2 and m["ignorar"] == IGNORAR_GO
    sem = tmp_path / "sem"
    sem.mkdir()
    repo2, _ = _go(sem, None)
    m2 = permissao.contar_modulos(repo2, "arq")
    assert m2["modulos"] == 4 and "ignorar" not in m2


# ------------------------------------------------------------------------------------------------ pasta-módulo

@pytest.mark.parametrize("ignorar", [["pkg/testdata"], ["pkg/testdata/"], ["pkg/test*"], ["**/testdata"]])
def test_modulo_de_pasta_e_ignorado_pelo_caminho_sem_a_barra(tmp_path, ignorar):
    arquivos = {"pkg/a/x.go": "package a\n", "pkg/b/y.go": "package b\n", "pkg/testdata/z.go": "package t\n"}
    repo, arq = _repo(tmp_path, arquivos, ["pkg/*/"], ignorar)
    _concordam(_por_ponto(repo, arq, tmp_path), ["pkg/a/", "pkg/b/"])
    assert lodemap_diff.modulo_de("pkg/testdata/z.go", ["pkg/*/"], ignorar) is None
    assert cp._modulo_de("pkg/testdata/z.go", ["pkg/*/"], ignorar) is None
    assert lodemap_diff.modulo_de("pkg/a/x.go", ["pkg/*/"], ignorar) == "pkg/a/"
    assert cp._modulo_de("pkg/a/x.go", ["pkg/*/"], ignorar) == "pkg/a/"


def test_pasta_sem_ignorar_continua_modulo(tmp_path):
    arquivos = {"pkg/a/x.go": "package a\n", "pkg/testdata/z.go": "package t\n"}
    repo, arq = _repo(tmp_path, arquivos, ["pkg/*/"], None)
    _concordam(_por_ponto(repo, arq, tmp_path), ["pkg/a/", "pkg/testdata/"])


def test_gancho_com_pasta_ignorada(tmp_path):
    arquivos = {"pkg/a/x.go": "package a\n", "pkg/testdata/z.go": "package t\n"}
    repo, arq = _repo(tmp_path, arquivos, ["pkg/*/"], ["pkg/testdata"])
    m = _carregar_gancho(arq)
    _escrever(repo, {"pkg/testdata/z.go": "package t\n// mudou\n"})
    _commitar(repo)
    assert m.commit_toca_arquitetura() is False
    _escrever(repo, {"pkg/a/x.go": "package a\n// mudou\n"})
    _commitar(repo)
    assert m.commit_toca_arquitetura() is True


def test_o_glob_seguinte_ainda_pode_casar_o_arquivo_ignorado_por_outro():
    """Ignorar é por candidato: `sub/*.go` ignorado não impede um glob de pasta de casar o arquivo."""
    globs = ["sub/*.go", "sub/"]
    assert lodemap_diff.modulo_de("sub/b.go", globs, ["sub/*.go"]) == "sub/"
    assert cp._modulo_de("sub/b.go", globs, ["sub/*.go"]) == "sub/"
    assert lodemap_diff.modulo_de("sub/b.go", globs) == "sub/b.go"


# ------------------------------------------------------------------------------------------------ paridade

PADROES = ["**/*_test.go", "*.go", "sub/*.go", "**/test_*.py", "**/conftest.py", "**/*.test.*", "**/*.spec.*", "pkg/testdata",
           "pkg/*", "a?.go", "[ab].go", "src/**/x", "**"]
CAMINHOS = ["a.go", "a_test.go", "sub/b.go", "sub/b_test.go", "x/y/z_test.go", "test_a.py", "src/test_a.py", "conftest.py",
            "pkg/conftest.py", "app.test.js", "lib/app.spec.ts", "lib/app.test.json", "pkg/testdata", "pkg/testdata/z.go",
            "pkg/b", "ab.go", "a.go.bak", "src/x", "src/y/x", "sub/deep/c.go"]


def test_matchers_dao_o_mesmo_resultado_nas_tres_copias(tmp_path):
    """arq_comum.glob_regex, codegraph_ponte._glob_regex e a cópia mínima do teste de cobertura não podem divergir."""
    repo, _ = _go(tmp_path)
    teste = _teste_instanciado(repo)
    for g, c in itertools.product(PADROES, CAMINHOS):
        ref = bool(arq_comum.glob_regex(g).fullmatch(c))
        assert bool(cp._glob_regex(g).fullmatch(c)) is ref, (g, c)
        assert bool(teste._glob_regex(g).fullmatch(c)) is ref, (g, c)
    for g, c in itertools.product(PADROES, CAMINHOS):
        ref = arq_comum.modulo_ignorado(c, [g])
        assert cp._ignorado(c, [g]) is ref, (g, c)


def test_normalizacao_da_lista_e_igual_nos_tres_lugares(tmp_path):
    brutos = [None, [], "x/*.go", ["a/", " b ", "", 3, None], ["**/*_test.go"]]
    for bruto in brutos:
        cfg = {} if bruto is None else {"ignorar": bruto}
        repo, _ = _go(tmp_path / f"n{brutos.index(bruto)}")
        teste = _teste_instanciado(repo)
        teste.CONFIG.clear()
        teste.CONFIG.update(cfg)
        assert arq_comum.globs_ignorar(cfg) == cp._ignorar_da_config(cfg) == teste._globs_ignorar(), bruto


def test_lista_de_modulos_do_teste_de_cobertura_e_do_arq_comum_batem_com_ignorar(tmp_path):
    arquivos = {**{n: "package x\n" for n in QUATRO}, "sub/deep/c.go": "package x\n", "sub/deep/c_test.go": "package x\n",
                "pkg/a/x.go": "package a\n", "pkg/testdata/z.go": "package t\n", "pkg/conftest.py": "x = 1\n"}
    modulos = ["**/*.go", "pkg/*/", "pkg/*.py"]
    for i, ignorar in enumerate([None, [], IGNORAR_GO, ["pkg/testdata", "**/*_test.go"], ["sub"], ["pkg/**"]]):
        pasta = tmp_path / f"p{i}"
        pasta.mkdir()
        repo, arq = _repo(pasta, arquivos, modulos, ignorar)
        assert _teste_instanciado(repo, f"cob{i}").alvos() == arq_comum.modulos_do_repo(arq, repo), ignorar


# ------------------------------------------------------------------------------------------------ novo_mapa.py

def _novo(repo: Path, *extra: str) -> dict:
    r = subprocess.run([sys.executable, str(RAIZ / "scripts" / "novo_mapa.py"), "--repo", str(repo), "--projeto", "P", *extra],
                       capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, r.stdout + r.stderr
    texto = (repo / "docs" / "architecture" / "structurizr" / "lodemap.json").read_text(encoding="utf-8")
    assert "{{" not in texto
    return json.loads(texto)


def _amostra(tmp_path: Path, nome: str, arquivos: list[str]) -> Path:
    repo = tmp_path / nome
    _escrever(repo, {a: "x\n" for a in arquivos})
    return repo


def test_novo_mapa_go_escreve_o_ignorar_dos_testes(tmp_path):
    repo = _amostra(tmp_path, "go", ["src/mux.go", "src/mux_test.go"])
    cfg = _novo(repo)
    assert cfg["modulos"] == ["src/**/*.go"]
    assert cfg["ignorar"] == ["**/*_test.go", "**/_*/**", "**/testdata/**"]
    # o teste de cobertura entregue já nasce sem os testes do Go
    assert _teste_instanciado_em(repo).alvos() == ["src/mux.go"]


def _teste_instanciado_em(repo: Path):
    spec = importlib.util.spec_from_file_location("cobertura_scaffold_t", repo / "tests" / "test_arquitetura_cobertura.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_novo_mapa_python_escreve_os_tres_globs_de_teste(tmp_path):
    repo = _amostra(tmp_path, "py", ["src/a.py", "src/test_a.py", "src/b_test.py", "src/conftest.py"])
    cfg = _novo(repo)
    assert cfg["modulos"] == ["src/*.py", "src/*/"]
    assert cfg["ignorar"] == ["**/test_*.py", "**/*_test.py", "**/conftest.py"]
    assert _teste_instanciado_em(repo).alvos() == ["src/a.py"]


def test_novo_mapa_javascript_escreve_test_e_spec(tmp_path):
    repo = _amostra(tmp_path, "js", ["lib/a.js", "lib/a.test.js", "lib/b.spec.ts", "lib/c.ts"])
    cfg = _novo(repo)
    assert cfg["ignorar"] == ["**/*.test.*", "**/*.spec.*"]
    assert _teste_instanciado_em(repo).alvos() == ["lib/a.js", "lib/c.ts"]


def test_novo_mapa_linguagem_sem_padrao_escreve_lista_vazia(tmp_path):
    repo = _amostra(tmp_path, "rs", ["src/lib.rs", "src/util.rs"])
    cfg = _novo(repo)
    assert cfg["modulos"] == ["src/**/*.rs"] and cfg["ignorar"] == [], "a chave existe, vazia e editável"


def test_novo_mapa_ignorar_da_linha_de_comando_substitui_o_padrao(tmp_path):
    repo = _amostra(tmp_path, "go", ["src/mux.go", "src/mux_test.go", "src/mux.gen.go"])
    assert _novo(repo, "--ignorar", "**/*.gen.go, src/x")["ignorar"] == ["**/*.gen.go", "src/x"]
    outro = _amostra(tmp_path, "go2", ["src/mux.go", "src/mux_test.go"])
    assert _novo(outro, "--ignorar", "")["ignorar"] == [], "vazio = nenhum, sem o padrão da linguagem"


def test_novo_mapa_com_modulos_explicitos_nao_ganha_ignorar_escondido(tmp_path):
    repo = _amostra(tmp_path, "py2", ["src/a.py", "tests/test_a.py"])
    cfg = _novo(repo, "--modulos", "tests/*.py")
    assert cfg["modulos"] == ["tests/*.py"] and cfg["ignorar"] == [], "quem escolhe os módulos escolhe o que ignorar"
    assert _novo(_amostra(tmp_path, "py3", ["src/a.py"]), "--modulos", "src/*.py", "--ignorar",
                 "src/x.py")["ignorar"] == ["src/x.py"]


def test_globs_e_ignorar_padrao_vem_da_mesma_varredura(tmp_path):
    repo = _amostra(tmp_path, "go3", ["src/mux.go", "src/mux_test.go"])
    assert novo_mapa.padroes_da_linguagem(repo, "src") == (novo_mapa.globs_padrao(repo, "src"),
                                                           novo_mapa.ignorar_padrao(repo, "src"))
