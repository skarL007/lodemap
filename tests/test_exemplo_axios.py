"""The example map in `exemplos/axios`: always checked for consistency, and regenerated end to end when possible.

The consistency checks run everywhere. The pipeline checks need two things:
- an axios checkout at v1.21.1, given in `LODEMAP_EXEMPLO_AXIOS`;
- the Structurizr CLI, found the same way `atualizar.py` finds it.

The pipeline checks then build a disposable copy:
1. `novo_mapa.py` scaffolds the map;
2. the example's sources are laid over it;
3. `atualizar.py` runs the full pipeline: validate, export, docs, reader, explorer;
4. the tests the map delivers to the project run, including the coverage gate;
5. the quality gate runs.

Without the checkout or the CLI they are skipped, unless `LODEMAP_EXIGIR_PIPELINE=1`. CI sets that, so a missing
tool fails the build instead of passing quietly.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import io
from pathlib import Path

import pytest

from lodemap import RAIZ

EXEMPLO = RAIZ / "exemplos" / "axios"
TEMPLATE = RAIZ / "templates" / "structurizr"
EXIGIR = os.environ.get("LODEMAP_EXIGIR_PIPELINE") == "1"
PRIVADO = re.compile(r"(?i:zpka2|machuca|\baxon\b|synapse|fabrica|uacr)|(?<![A-Za-z])[A-Z]:[\\/]")


def _rodar(cmd, cwd=None, env=None, timeout=900):
    e = dict(os.environ, LODEMAP_IDIOMA="en", **(env or {}))
    return subprocess.run(cmd, cwd=cwd, env=e, capture_output=True, text=True, encoding="utf-8", errors="replace",
                          timeout=timeout)


# ---------- consistency (always) ----------

def test_o_exemplo_e_um_mapa_em_ingles_do_axios():
    cfg = json.loads((EXEMPLO / "lodemap.json").read_text(encoding="utf-8"))
    assert cfg["projeto"] == "axios"
    assert cfg["idioma"] == "en"
    assert cfg["modulos"] == ["lib/**/*.js"]
    assert (EXEMPLO / "workspace.dsl").is_file()
    assert (EXEMPLO / ".lodemap" / "decisoes-modelo.json").is_file()


def test_o_exemplo_nao_traz_saida_gerada_nem_dado_local():
    for gerado in ("explorador", "leitor", "scripts", ".structurizr"):
        assert not (EXEMPLO / gerado).exists(), f"{gerado}/ is generated; it does not belong in the example"
    for f in ("consentimento.json", "local.json"):
        assert not (EXEMPLO / ".lodemap" / f).exists()
    achados = [str(p.relative_to(EXEMPLO)) for p in EXEMPLO.rglob("*")
               if p.is_file() and PRIVADO.search(p.read_text(encoding="utf-8", errors="replace"))]
    assert achados == [], achados


def test_os_estilos_do_exemplo_sao_os_do_template():
    assert (EXEMPLO / "views" / "estilos.dsl").read_bytes() == (TEMPLATE / "views" / "estilos.dsl").read_bytes()


def test_o_exemplo_tem_um_componente_por_modulo_do_axios_v1_21_1():
    dsl = (EXEMPLO / "model" / "componentes-axiosLib.dsl").read_text(encoding="utf-8")
    codigos = set(re.findall(r'"codigo"\s+"(lib/[^"]+\.js)"', dsl))
    inv = json.loads((EXEMPLO / "inventario.json").read_text(encoding="utf-8"))
    assert len(codigos) == 72, len(codigos)
    assert inv, "inventory is empty"


# ---------- pipeline (needs axios v1.21.1 and the Structurizr CLI) ----------

def _cli_disponivel() -> str | None:
    sys.path.insert(0, str(TEMPLATE / "scripts"))
    try:
        import atualizar  # type: ignore
    finally:
        sys.path.pop(0)
    ferr = os.environ.get("STRUCTURIZR_FERRAMENTAS") or str(Path.home() / ".structurizr")
    try:
        return str(atualizar.localizar_cli(ferr, env=os.environ))
    except Exception:  # noqa: BLE001 - any failure means "not available"
        return None


@pytest.fixture(scope="module")
def projeto(tmp_path_factory):
    origem = os.environ.get("LODEMAP_EXEMPLO_AXIOS")
    faltando = []
    if not origem or not (Path(origem) / "lib" / "axios.js").is_file():
        faltando.append("LODEMAP_EXEMPLO_AXIOS (an axios v1.21.1 checkout)")
    if shutil.which("java") is None:
        faltando.append("java")
    if _cli_disponivel() is None:
        faltando.append("Structurizr CLI")
    if faltando:
        if EXIGIR:
            pytest.fail("pipeline required but missing: " + ", ".join(faltando))
        pytest.skip("missing: " + ", ".join(faltando))
    r = tmp_path_factory.mktemp("axios")
    arq = subprocess.run(["git", "-C", origem, "archive", "--format=tar", "HEAD"], capture_output=True, check=True)
    with tarfile.open(fileobj=io.BytesIO(arq.stdout)) as t:
        t.extractall(r, filter="data")
    for c in (["init", "-q"], ["add", "-A"], ["commit", "-q", "-m", "axios v1.21.1"]):
        subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *c], cwd=r, check=True,
                       capture_output=True)
    novo = _rodar([sys.executable, str(RAIZ / "scripts" / "novo_mapa.py"), "--repo", str(r), "--project", "axios",
                   "--language", "en", "--code-root", "lib", "--modules", "lib/**/*.js",
                   "--github", "https://github.com/axios/axios"])
    assert novo.returncode == 0, novo.stdout + novo.stderr
    destino = r / "docs" / "architecture" / "structurizr"
    shutil.copytree(EXEMPLO, destino, dirs_exist_ok=True)
    return r


@pytest.fixture(scope="module")
def atualizado(projeto):
    arq = projeto / "docs" / "architecture" / "structurizr"
    p = _rodar([sys.executable, str(arq / "scripts" / "atualizar.py")], cwd=projeto)
    assert p.returncode == 0, p.stdout[-3000:] + p.stderr[-3000:]
    return projeto, p.stdout


def test_o_pipeline_completo_valida_exporta_e_gera_tudo(atualizado):
    projeto, saida = atualizado
    arq = projeto / "docs" / "architecture" / "structurizr"
    for passo in ("1/7", "2/7", "3/7", "4/7", "5/7"):
        assert passo in saida, saida[-2000:]
    assert (arq / ".structurizr" / "export" / "workspace.json").is_file()
    dados = (arq / "explorador" / "dados.js").read_text(encoding="utf-8")
    assert '"idioma": "en"' in dados and '"nome": "axios"' in dados
    componentes = len(re.findall(r'"tipo":\s*"Componente"', dados))
    assert componentes == 72, componentes
    assert (arq / "leitor" / "dados.js").is_file()
    assert (arq / "docs" / "02-mapa-de-status.md").is_file()


def test_o_js_gerado_e_valido(atualizado):
    if shutil.which("node") is None:
        if EXIGIR:
            pytest.fail("node required but missing")
        pytest.skip("node missing")
    projeto, _ = atualizado
    arq = projeto / "docs" / "architecture" / "structurizr"
    for f in (arq / "explorador" / "dados.js", arq / "leitor" / "dados.js"):
        p = subprocess.run(["node", "--check", str(f)], capture_output=True, text=True)
        assert p.returncode == 0, p.stderr


def test_os_testes_entregues_passam_inclusive_o_gate_de_cobertura(atualizado):
    projeto, _ = atualizado
    p = _rodar([sys.executable, "-m", "pytest", "tests", "-q", "-p", "no:cacheprovider",
                "--basetemp", str(projeto / ".pyt")], cwd=projeto)
    assert p.returncode == 0, p.stdout[-3000:]
    assert "failed" not in p.stdout.splitlines()[-1]


def test_o_gate_de_qualidade_aprova_o_exemplo(atualizado):
    projeto, _ = atualizado
    arq = projeto / "docs" / "architecture" / "structurizr"
    p = _rodar([sys.executable, str(RAIZ / "scripts" / "qualidade.py"), "--arq", str(arq), "--repo", str(projeto)])
    res = json.loads(p.stdout)
    assert p.returncode == 0 and res["gate"]["aprovado"], res.get("gate")
