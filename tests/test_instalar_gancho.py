"""instalar_gancho.py: instala, respeita gancho alheio e core.hooksPath, remove só o que é nosso. Sempre em repo git temporário."""
from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from lodemap import RAIZ

SCRIPTS_REAIS = RAIZ / "templates" / "structurizr" / "scripts"
NOMES = ("instalar_gancho.py", "lodemap_gancho_lanca.py", "lodemap_gancho.py")


def _carregar(onde: Path, nome: str):
    spec = importlib.util.spec_from_file_location(nome, onde)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


@pytest.fixture(autouse=True)
def git_isolado(monkeypatch, tmp_path):
    """Nenhuma configuração global/de sistema do git do usuário (por exemplo core.hooksPath) entra nos testes."""
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "home"))


def _git(repo: Path, *args: str) -> str:
    r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=True)
    return r.stdout.strip()


@pytest.fixture
def cenario(tmp_path):
    """repo/ (git) com a arquitetura em repo/arq e uma cópia dos scripts em repo/arq/scripts."""
    repo = tmp_path / "repo"
    scripts = repo / "arq" / "scripts"
    scripts.mkdir(parents=True)
    for n in NOMES:
        shutil.copyfile(SCRIPTS_REAIS / n, scripts / n)
    _git(repo, "init", "-q")
    inst = _carregar(scripts / "instalar_gancho.py", "instalar_gancho_t")
    return inst, repo, repo / "arq", scripts


def _rodar(inst, arq, scripts, *flags, ferramentas=None):
    ferr = str(arq.parent / "ferr") if ferramentas is None else ferramentas
    return inst.main(["--python", sys.executable, "--ferramentas", ferr, *flags], scripts=scripts)


def _hooks(repo: Path) -> Path:
    return repo / ".git" / "hooks"


def test_instala_os_dois_ganchos_com_lf_marca_e_comando(cenario, capsys):
    inst, repo, arq, scripts = cenario
    assert _rodar(inst, arq, scripts) == 0
    hooks = _hooks(repo)
    for tipo in ("post-commit", "post-merge"):
        bruto = (hooks / tipo).read_bytes()
        assert b"\r" not in bruto, "o sh do git não lê CRLF"
        linhas = bruto.decode("utf-8").splitlines()
        assert linhas[0] == "#!/bin/sh" and linhas[1].startswith("# lodemap")
        assert tipo in linhas[2] and "lodemap_gancho_lanca.py" in linhas[2] and "--ferramentas" in linhas[2]
        assert linhas[2].endswith(">/dev/null 2>&1 || true") and linhas[3] == "exit 0"
        if os.name != "nt":
            assert os.access(hooks / tipo, os.X_OK), "em POSIX o gancho precisa de chmod +x"
    assert "instalado:" in capsys.readouterr().out


def test_copia_o_lancador_e_aprova_o_hash_dos_scripts(cenario):
    inst, repo, arq, scripts = cenario
    _rodar(inst, arq, scripts)
    hooks = _hooks(repo)
    assert (hooks / "lodemap_gancho_lanca.py").read_bytes() == (scripts / "lodemap_gancho_lanca.py").read_bytes()
    pin = json.loads((hooks / "lodemap-gancho.pin.json").read_text(encoding="utf-8"))
    lanca = _carregar(hooks / "lodemap_gancho_lanca.py", "lanca_t")
    assert pin["scripts"] == str(scripts.resolve()) and pin["sha256"] == lanca.digest(scripts)


def test_nao_sobrescreve_gancho_alheio_e_avisa(cenario, capsys):
    inst, repo, arq, scripts = cenario
    hooks = _hooks(repo)
    hooks.mkdir(exist_ok=True)
    (hooks / "post-commit").write_text("#!/bin/sh\necho do outro time\n", encoding="utf-8")
    assert _rodar(inst, arq, scripts) == 0
    assert "do outro time" in (hooks / "post-commit").read_text(encoding="utf-8")
    assert "# lodemap" in (hooks / "post-merge").read_text(encoding="utf-8"), "o outro gancho é instalado normalmente"
    assert "--forcar" in capsys.readouterr().err


def test_forcar_troca_o_gancho_alheio(cenario):
    inst, repo, arq, scripts = cenario
    hooks = _hooks(repo)
    hooks.mkdir(exist_ok=True)
    (hooks / "post-commit").write_text("#!/bin/sh\necho do outro time\n", encoding="utf-8")
    assert _rodar(inst, arq, scripts, "--forcar") == 0
    texto = (hooks / "post-commit").read_text(encoding="utf-8")
    assert "do outro time" not in texto and "# lodemap" in texto


def test_reinstalar_atualiza_o_nosso_sem_precisar_de_forcar(cenario):
    inst, repo, arq, scripts = cenario
    _rodar(inst, arq, scripts, ferramentas="/primeira")
    _rodar(inst, arq, scripts, ferramentas="/segunda")
    texto = (_hooks(repo) / "post-merge").read_text(encoding="utf-8")
    assert "/segunda" in texto and "/primeira" not in texto


def test_remover_tira_so_os_nossos_e_limpa_lancador_e_pin(cenario):
    inst, repo, arq, scripts = cenario
    hooks = _hooks(repo)
    hooks.mkdir(exist_ok=True)
    (hooks / "post-commit").write_text("#!/bin/sh\necho do outro time\n", encoding="utf-8")
    _rodar(inst, arq, scripts)  # post-commit alheio fica; post-merge é nosso
    assert _rodar(inst, arq, scripts, "--remover") == 0
    assert (hooks / "post-commit").is_file() and "do outro time" in (hooks / "post-commit").read_text(encoding="utf-8")
    assert not (hooks / "post-merge").exists()
    assert not (hooks / "lodemap_gancho_lanca.py").exists() and not (hooks / "lodemap-gancho.pin.json").exists()


def test_remover_sem_instalar_nao_falha(cenario):
    inst, repo, arq, scripts = cenario
    assert _rodar(inst, arq, scripts, "--remover") == 0


def test_respeita_core_hookspath_absoluto(cenario, tmp_path):
    inst, repo, arq, scripts = cenario
    alvo = tmp_path / "ganchos-do-time"
    _git(repo, "config", "core.hooksPath", str(alvo))
    assert _rodar(inst, arq, scripts) == 0
    assert (alvo / "post-commit").is_file() and (alvo / "lodemap-gancho.pin.json").is_file()
    assert not (_hooks(repo) / "post-commit").exists()


def test_respeita_core_hookspath_relativo_a_raiz_do_repositorio(cenario):
    inst, repo, arq, scripts = cenario
    _git(repo, "config", "core.hooksPath", ".githooks")
    assert _rodar(inst, arq, scripts) == 0
    assert (repo / ".githooks" / "post-commit").is_file(), "caminho relativo vale a partir da raiz do repo, como no git"
    assert not (arq / ".githooks").exists()


def test_fora_de_repositorio_git_sai_com_1_e_nao_cria_nada(tmp_path, monkeypatch, capsys):
    scripts = tmp_path / "sem-git" / "arq" / "scripts"
    scripts.mkdir(parents=True)
    for n in NOMES:
        shutil.copyfile(SCRIPTS_REAIS / n, scripts / n)
    inst = _carregar(scripts / "instalar_gancho.py", "instalar_gancho_sem_git")
    # o teto impede o git de achar um repositório num diretório acima do tmp_path
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path))
    assert inst.main(["--python", sys.executable], scripts=scripts) == 1
    assert "repositório git" in capsys.readouterr().err
    assert not (scripts.parent / ".git").exists()


def test_executado_como_script_de_ponta_a_ponta(cenario):
    """O arquivo copiado funciona sozinho, chamado como `python instalar_gancho.py` (o que o .ps1 faz)."""
    inst, repo, arq, scripts = cenario
    r = subprocess.run([sys.executable, str(scripts / "instalar_gancho.py"), "--python", sys.executable,
                        "--ferramentas", str(arq.parent / "ferr")], capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, r.stderr
    assert (_hooks(repo) / "post-commit").is_file()
    r = subprocess.run([sys.executable, str(scripts / "instalar_gancho.py"), "--remover"],
                       capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0 and not (_hooks(repo) / "post-commit").exists()


def test_caminhos_com_espaco_e_aspas_saem_citados_para_o_sh(cenario):
    inst, *_ = cenario
    corpo = inst.corpo_do_gancho("post-commit", "/usr/bin/meu python", Path("/tmp/a b/lanca.py"), "/tmp/it's here")
    assert "'/usr/bin/meu python'" in corpo and "'/tmp/a b/lanca.py'" in corpo
    assert "'\"'\"'" in corpo, "aspa simples no caminho é escapada"
