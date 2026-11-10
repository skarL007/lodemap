"""Lançador do gancho do git: só executa os scripts do repositório se eles ainda forem os aprovados na instalação."""
from __future__ import annotations

import importlib.util
import json

from lodemap import RAIZ

LANCA = RAIZ / "templates" / "structurizr" / "scripts" / "lodemap_gancho_lanca.py"


def _carregar(onde):
    spec = importlib.util.spec_from_file_location("lodemap_gancho_lanca_t", onde)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _cenario(tmp_path):
    hooks = tmp_path / ".git" / "hooks"
    scripts = tmp_path / "arq" / "scripts"
    hooks.mkdir(parents=True)
    scripts.mkdir(parents=True)
    (scripts / "atualizar.ps1").write_text("Write-Host ok\n", encoding="utf-8")
    # o "gancho" de mentira deixa uma marca para provar se foi executado
    (scripts / "lodemap_gancho.py").write_text(
        "import sys, pathlib\npathlib.Path(__file__).with_name('rodou.txt').write_text(' '.join(sys.argv[1:]))\n",
        encoding="utf-8")
    copia = hooks / "lodemap_gancho_lanca.py"
    copia.write_bytes(LANCA.read_bytes())
    return _carregar(copia), scripts, tmp_path / "arq"


def test_aprovado_executa_e_repassa_os_argumentos(tmp_path):
    m, scripts, _ = _cenario(tmp_path)
    assert m.main(["--aprovar", str(scripts)]) == 0
    assert m.main(["post-commit", "--ferramentas", "x"]) == 0
    assert (scripts / "rodou.txt").read_text(encoding="utf-8") == "post-commit --ferramentas x"


def test_script_alterado_depois_da_aprovacao_nao_executa_e_avisa_no_log(tmp_path):
    m, scripts, arq = _cenario(tmp_path)
    m.main(["--aprovar", str(scripts)])
    (scripts / "atualizar.ps1").write_text("Remove-Item -Recurse C:\\ # veio num git pull\n", encoding="utf-8")
    assert m.main(["post-merge"]) == 0, "o gancho nunca derruba o git"
    assert not (scripts / "rodou.txt").exists(), "script alterado não pode rodar"
    log = (arq / ".lodemap" / "ultimo-atualizar.log").read_text(encoding="utf-8")
    assert "alterados desde a aprovação" in log and "instalar-gancho.ps1" in log


def test_sem_aprovacao_nao_executa(tmp_path):
    m, scripts, _ = _cenario(tmp_path)
    assert m.main(["post-commit"]) == 0
    assert not (scripts / "rodou.txt").exists()


def test_arquivo_novo_na_pasta_de_scripts_tambem_invalida(tmp_path):
    m, scripts, _ = _cenario(tmp_path)
    m.main(["--aprovar", str(scripts)])
    (scripts / "extra.py").write_text("print('novo')\n", encoding="utf-8")
    m.main(["post-commit"])
    assert not (scripts / "rodou.txt").exists()
    pin = json.loads((m.PIN).read_text(encoding="utf-8"))
    assert pin["scripts"] == str(scripts) and len(pin["sha256"]) == 64
