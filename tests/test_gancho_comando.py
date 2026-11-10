"""lodemap_gancho.py: a atualização em segundo plano chama atualizar.py com o mesmo Python, sem PowerShell."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from lodemap import RAIZ

PASTA = RAIZ / "templates" / "structurizr" / "scripts"
GANCHO = PASTA / "lodemap_gancho.py"


def _carregar(arquivo: Path = GANCHO):
    spec = importlib.util.spec_from_file_location("lodemap_gancho_t", arquivo)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_comando_chama_atualizar_py_com_o_mesmo_python_e_as_flags_incrementais():
    m = _carregar()
    cmd = m.comando_atualizar("post-commit abc123: ação ç", "/ferr")
    assert cmd[0] == sys.executable and Path(cmd[1]).name == "atualizar.py"
    assert Path(cmd[1]).parent == m.SCRIPTS
    assert "--incremental" in cmd and "--sem-site" in cmd
    assert cmd[cmd.index("--checkpoint") + 1] == "post-commit abc123: ação ç"
    assert cmd[cmd.index("--python") + 1] == sys.executable
    assert cmd[cmd.index("--ferramentas") + 1] == "/ferr"
    assert "--ferramentas" not in m.comando_atualizar("x")


def test_flags_do_comando_existem_no_parser_do_atualizar_py():
    spec = importlib.util.spec_from_file_location("lodemap_atualizar_t", PASTA / "atualizar.py")
    at = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(at)
    cmd = _carregar().comando_atualizar("rótulo", "/ferr")
    a = at.parse_args(cmd[2:], env={})
    assert a.incremental and a.sem_site and a.checkpoint == "rótulo" and a.ferramentas == "/ferr"
    assert a.python == sys.executable


def test_gancho_nao_menciona_powershell():
    texto = GANCHO.read_text(encoding="utf-8")
    assert "powershell" not in texto.lower() and "pwsh" not in texto.lower() and ".ps1" not in texto
    assert not hasattr(_carregar(), "_powershell")


def _isolar(m, monkeypatch, tmp_path, atualizar_py: str):
    scripts = tmp_path / "arq" / "scripts"
    scripts.mkdir(parents=True)
    (scripts / "atualizar.py").write_text(atualizar_py, encoding="utf-8")
    smap = tmp_path / "arq" / ".lodemap"
    monkeypatch.setattr(m, "SCRIPTS", scripts)
    monkeypatch.setattr(m, "ARQ", tmp_path / "arq")
    monkeypatch.setattr(m, "SMAP", smap)
    monkeypatch.setattr(m, "TRAVA", smap / "atualizar.lock")
    monkeypatch.setattr(m, "LOG", smap / "ultimo-atualizar.log")
    return scripts, smap


def test_executar_roda_o_atualizar_py_de_verdade_grava_log_e_solta_a_trava(tmp_path, monkeypatch):
    m = _carregar()
    marca = tmp_path / "argv.txt"
    _, smap = _isolar(m, monkeypatch, tmp_path,
                      f"import sys, pathlib\npathlib.Path({str(marca)!r}).write_text('\\n'.join(sys.argv[1:]), encoding='utf-8')\n"
                      "print('atualizou')\nsys.exit(3)\n")
    assert m.executar("post-merge deadbee: pós", "/ferr") == 3
    assert marca.read_text(encoding="utf-8").splitlines() == [
        "--incremental", "--sem-site", "--checkpoint", "post-merge deadbee: pós", "--python", sys.executable,
        "--ferramentas", "/ferr"]
    log = (smap / "ultimo-atualizar.log").read_text(encoding="utf-8")
    assert "checkpoint: post-merge deadbee: pós" in log and "atualizou" in log and "fim, código 3" in log
    assert not (smap / "atualizar.lock").exists()


def test_trava_recente_faz_pular_sem_rodar(tmp_path, monkeypatch):
    m = _carregar()
    marca = tmp_path / "rodou.txt"
    _, smap = _isolar(m, monkeypatch, tmp_path, f"open({str(marca)!r}, 'w').write('x')\n")
    smap.mkdir()
    (smap / "atualizar.lock").write_text("1", encoding="utf-8")
    assert m.executar("x") == 0
    assert not marca.exists()
    assert "outra atualização em curso" in (smap / "ultimo-atualizar.log").read_text(encoding="utf-8")


def test_main_nunca_derruba_o_git_mesmo_com_erro(tmp_path, monkeypatch):
    m = _carregar()
    _isolar(m, monkeypatch, tmp_path, "")

    def quebrado(*a):
        raise RuntimeError("git quebrado")

    monkeypatch.setattr(m, "git", quebrado)
    assert m.main(["post-commit"]) == 0
    assert "gancho falhou" in (tmp_path / "arq" / ".lodemap" / "ultimo-atualizar.log").read_text(encoding="utf-8")
