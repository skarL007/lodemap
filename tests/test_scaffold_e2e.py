"""Mapa novo de ponta a ponta: novo_mapa.py num repositório descartável e os testes que ele mesmo entrega.

Os testes de templates/tests só rodam no repositório de destino; sem este teste a CI do Lodemap não veria uma
regressão no leitor, no explorador, nos geradores ou no gate de cobertura.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from lodemap import RAIZ

COBERTURA = "tests/test_arquitetura_cobertura.py::test_todo_modulo_esta_no_modelo"


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "-C", str(repo), *args],
                   check=True, capture_output=True)


@pytest.fixture(scope="module")
def projeto(tmp_path_factory):
    r = tmp_path_factory.mktemp("amostra")
    (r / "app").mkdir()
    (r / "app" / "api.py").write_text("from app import store\n\n\ndef rota():\n    return store.ler()\n", encoding="utf-8")
    (r / "app" / "store.py").write_text("def ler():\n    return 1\n", encoding="utf-8")
    _git(r, "init", "-q")
    _git(r, "add", "-A")
    _git(r, "commit", "-q", "-m", "inicio")
    novo = subprocess.run([sys.executable, str(RAIZ / "scripts" / "novo_mapa.py"), "--repo", str(r),
                           "--projeto", "Amostra"], capture_output=True, text=True, encoding="utf-8")
    assert novo.returncode == 0, novo.stdout + novo.stderr
    return r


def _pytest(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-m", "pytest", "tests", "-q", "-p", "no:cacheprovider",
                           "--basetemp", str(repo / ".pyt"), *args],
                          cwd=repo, capture_output=True, text=True, encoding="utf-8", errors="replace")


def test_o_mapa_novo_entrega_a_pagina_do_leitor_com_mermaid_embutido(projeto):
    arq = projeto / "docs" / "architecture" / "structurizr"
    for rel in ("leitor/index.html", "leitor/vendor/mermaid.tiny.js", "leitor/vendor/LICENSE-mermaid.txt",
                "explorador/vendor/cytoscape.min.js", "lodemap.json"):
        assert (arq / rel).is_file(), rel
    assert "{{" not in (arq / "lodemap.json").read_text(encoding="utf-8"), "marcador sem trocar"


def test_os_testes_entregues_passam_menos_o_gate_de_cobertura(projeto):
    r = _pytest(projeto, "--deselect", COBERTURA)
    assert r.returncode == 0, r.stdout[-2500:] + r.stderr[-800:]


def test_o_gate_de_cobertura_esta_vivo_e_aponta_os_modulos_fora_do_modelo(projeto):
    r = _pytest(projeto, COBERTURA.split("::")[0], "-k", "todo_modulo_esta_no_modelo")
    assert r.returncode == 1, "um mapa novo, sem modelagem, deve reprovar o gate"
    assert "app/api.py" in r.stdout and "app/store.py" in r.stdout


def test_o_mapa_novo_traz_so_mapa_documentacao_e_decisoes(projeto):
    arq = projeto / "docs" / "architecture" / "structurizr"
    assert not (arq / "agentes").exists() and not (arq / "scripts" / "gerar_agentes.py").exists()
    assert "agentes" not in (arq / "lodemap.json").read_text(encoding="utf-8")
    barra = (arq / "explorador" / "index.html").read_text(encoding="utf-8")
    assert 'data-lm="mapa"' in barra and 'data-lm="docs"' in barra and 'data-lm="decisoes"' in barra
    assert 'data-lm="agentes"' not in barra
