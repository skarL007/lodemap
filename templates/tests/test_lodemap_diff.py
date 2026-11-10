"""lodemap_diff.py (modo incremental da lodemap) num repositório git temporário."""
from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "{{ARQ_REL}}" / "scripts" / "lodemap_diff.py"

pytestmark = pytest.mark.skipif(not shutil.which("git"), reason="precisa do git")


def _modulo():
    spec = importlib.util.spec_from_file_location("lodemap_diff", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@t", *args], check=True,
                   capture_output=True)


def _componente(ident: str, codigo: str) -> dict:
    return {"id": ident, "name": ident.title(), "properties": {"structurizr.dsl.identifier": ident, "codigo": codigo}}


@pytest.fixture
def projeto(tmp_path: Path) -> tuple[Path, Path]:
    repo = tmp_path / "repo"
    (repo / "src" / "pac").mkdir(parents=True)
    (repo / "src" / "a.py").write_text("x = 1\n")
    (repo / "src" / "b.py").write_text("y = 1\n")
    (repo / "src" / "pac" / "u.py").write_text("z = 1\n")
    arq = repo / "arq"
    (arq / ".structurizr" / "export").mkdir(parents=True)
    (arq / "lodemap.json").write_text(json.dumps({"projeto": "T", "raiz_codigo": "src",
                                                          "modulos": ["src/*.py", "src/*/"]}))
    ws = {"model": {"softwareSystems": [{"containers": [{"name": "App", "components": [
        _componente("compA", "src/a.py"), _componente("compB", "src/b.py"), _componente("compPac", "src/pac/")]}]}]}}
    (arq / ".structurizr" / "export" / "workspace.json").write_text(json.dumps(ws))
    _git(repo, "init", "-q")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "base")
    return repo, arq


def test_sem_ultimo_commit_e_completo(projeto):
    _, arq = projeto
    assert _modulo().diff(arq)["modo"] == "completo"


def test_mudanca_aponta_so_o_componente_afetado(projeto):
    repo, arq = projeto
    sd = _modulo()
    sd.marcar(arq)
    estado = json.loads((arq / ".lodemap" / "estado.json").read_text(encoding="utf-8-sig"))
    assert estado["ultimoCommit"] and estado["geradoEm"] and set(estado["passos"]) >= {"modelador", "gerador"}
    (repo / "src" / "a.py").write_text("x = 2\n")
    (repo / "src" / "pac" / "u.py").write_text("z = 2\n")
    (repo / "src" / "c.py").write_text("novo\n")
    (repo / "src" / "b.py").unlink()
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "mudanca")
    d = sd.diff(arq)
    assert d["modo"] == "incremental"
    assert d["modulosMudados"] == ["src/a.py", "src/pac/"]
    assert d["modulosNovos"] == ["src/c.py"]
    assert d["modulosRemovidos"] == ["src/b.py"]
    assert [c["id"] for c in d["componentesAfetados"]] == ["compA", "compB", "compPac"]
    assert d["semComponente"] == ["src/c.py"]


def test_arquivo_fora_dos_globs_e_ignorado(projeto):
    repo, arq = projeto
    sd = _modulo()
    sd.marcar(arq)
    (repo / "LEIAME.md").write_text("doc\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "doc")
    d = sd.diff(arq)
    assert d["modo"] == "incremental" and not d["componentesAfetados"] and not d["modulosNovos"]
