"""Raiz do código detectada pelo `novo_mapa.py` quando o dono não passa `--raiz-codigo`.

Achado ao mapear um repositório Go (go-chi/chi): os arquivos moram na raiz do repositório, não existe `src/`, e o mapa
nascia com `"raiz_codigo": "src"` e os globs de Python (`src/*.py`, `src/*/`), que não casavam arquivo nenhum.
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

from lodemap import RAIZ, permissao

sys.path.insert(0, str(RAIZ / "scripts"))
import novo_mapa  # noqa: E402


def _repo(tmp_path: Path, nome: str, arquivos: list[str]) -> Path:
    repo = tmp_path / nome
    for rel in arquivos:
        f = repo / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text("x\n", encoding="utf-8")
    return repo


def _novo(repo: Path, *extra: str) -> dict:
    r = subprocess.run([sys.executable, str(RAIZ / "scripts" / "novo_mapa.py"), "--repo", str(repo), "--projeto", "P", *extra],
                       capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, r.stdout + r.stderr
    return json.loads((repo / "docs" / "architecture" / "structurizr" / "lodemap.json").read_text(encoding="utf-8"))


def _alvos(repo: Path) -> list[str]:
    spec = importlib.util.spec_from_file_location("cobertura_raiz_t", repo / "tests" / "test_arquitetura_cobertura.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m.alvos()


GO_NA_RAIZ = ["go.mod", "mux.go", "mux_test.go", "tree.go", "middleware/logger.go", "middleware/logger_test.go",
              "_examples/rest/main.go", "testdata/cert.go", "middleware/testdata/fixture.go", "README.md"]


def test_go_na_raiz_do_repositorio_vira_raiz_vazia_e_globs_sem_prefixo(tmp_path):
    repo = _repo(tmp_path, "go", GO_NA_RAIZ)
    assert novo_mapa.detectar_raiz(repo) == ""
    cfg = _novo(repo)
    assert cfg["raiz_codigo"] == "" and cfg["modulos"] == ["**/*.go"]
    assert cfg["ignorar"] == ["**/*_test.go", "**/_*/**", "**/testdata/**"]
    # testes, exemplos em pasta "_x" e testdata (o que o `go build` ignora) não viram módulo
    assert _alvos(repo) == ["middleware/logger.go", "mux.go", "tree.go"]


def test_refazer_o_mapa_nao_troca_a_linguagem_pelos_scripts_do_proprio_mapa(tmp_path):
    repo = _repo(tmp_path, "go2", ["go.mod", "mux.go", "tree.go"])
    _novo(repo)  # entrega mais de dez .py em docs/architecture/structurizr/scripts e em tests/
    assert _novo(repo, "--forcar")["modulos"] == ["**/*.go"], "os .py do mapa não contam na varredura da raiz"


def test_pasta_convencional_sem_codigo_nao_esconde_o_codigo_da_raiz(tmp_path):
    repo = _repo(tmp_path, "lib", ["lib/README.md", "main.go", "go.mod"])
    assert novo_mapa.detectar_raiz(repo) == ""
    repo2 = _repo(tmp_path, "lib2", ["lib/a.js", "main.go"])
    assert novo_mapa.detectar_raiz(repo2) == "lib", "pasta convencional com código continua vencendo"


def test_repositorio_sem_codigo_continua_com_src(tmp_path):
    repo = _repo(tmp_path, "vazio", ["README.md", "node_modules/x/index.js", ".venv/lib/a.py"])
    assert novo_mapa.detectar_raiz(repo) == "src"
    assert _novo(repo)["modulos"] == ["src/*.py", "src/*/"]


def test_python_na_raiz_nao_transforma_docs_e_tests_em_modulo(tmp_path):
    repo = _repo(tmp_path, "py", ["setup.py", "pacote/__init__.py", "pacote/nucleo.py", "docs/conf.py",
                                  "tests/test_nucleo.py", "examples/demo.py"])
    cfg = _novo(repo)
    assert cfg["raiz_codigo"] == "" and cfg["modulos"] == ["*.py", "*/"]
    assert cfg["ignorar"] == ["**/test_*.py", "**/*_test.py", "**/conftest.py", "docs", "tests", "test", "examples"]
    assert _alvos(repo) == ["pacote/", "setup.py"]


def test_raiz_explicita_ponto_ou_vazia_e_a_raiz_do_repositorio(tmp_path):
    repo = _repo(tmp_path, "ponto", ["src/a.js", "cmd.go", "go.mod", "outro.go"])
    assert _novo(repo, "--raiz-codigo", ".")["modulos"] == ["**/*.go"]
    repo2 = _repo(tmp_path, "vazia", ["src/a.js", "cmd.go", "go.mod", "outro.go"])
    cfg = _novo(repo2, "--raiz-codigo", "")
    assert cfg["raiz_codigo"] == "" and cfg["modulos"] == ["**/*.go"]


def test_o_plano_de_permissao_conta_os_mesmos_modulos_antes_do_mapa_existir(tmp_path):
    repo = _repo(tmp_path, "plano", GO_NA_RAIZ)
    m = permissao.contar_modulos(repo)
    assert m["globs"] == ["**/*.go"] and m["modulos"] == 3
