from __future__ import annotations

import json
import os

import pytest

from lodemap import __version__, cli

NOMES = ("git", "claude", "dot", "java", "node")


def _path_falso(tmp_path, monkeypatch, nomes=NOMES):
    b = tmp_path / "bin"
    b.mkdir(exist_ok=True)
    for n in nomes:
        exe = b / (n + (".bat" if os.name == "nt" else ""))
        exe.write_text("@echo off\n" if os.name == "nt" else "#!/bin/sh\n")
        exe.chmod(0o755)
    monkeypatch.setenv("PATH", str(b))
    monkeypatch.setenv("PATHEXT", ".BAT;.EXE")
    monkeypatch.delenv("STRUCTURIZR_CLI", raising=False)
    monkeypatch.delenv("STRUCTURIZR_FERRAMENTAS", raising=False)


def _estados(capsys, *args):
    rc = cli.main(["doctor", "--json", *args])
    dado = json.loads(capsys.readouterr().out)
    return rc, {i["nome"]: i for i in dado["itens"]}


def test_version(capsys):
    with pytest.raises(SystemExit) as e:
        cli.main(["--version"])
    assert e.value.code == 0
    assert capsys.readouterr().out.strip() == f"lodemap {__version__}"


def test_doctor_tudo_presente_sai_0(home, tmp_path, monkeypatch, capsys):
    _path_falso(tmp_path, monkeypatch)
    assert cli.main(["instalar", "--perfil", "minimo", "--aplicar"]) == 0
    capsys.readouterr()
    cli_dir = home / ".structurizr" / "cli"
    cli_dir.mkdir(parents=True)
    (cli_dir / ("structurizr.bat" if os.name == "nt" else "structurizr.sh")).write_text("x")
    rc = cli.main(["doctor"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "0 falha(s), 0 aviso(s)" in out


def test_doctor_sem_git_sai_1(home, tmp_path, monkeypatch, capsys):
    _path_falso(tmp_path, monkeypatch, [n for n in NOMES if n != "git"])
    rc, it = _estados(capsys)
    assert rc == 1
    assert it["git"]["estado"] == "falha"


def test_doctor_sem_claude_aviso_sai_0(home, tmp_path, monkeypatch, capsys):
    _path_falso(tmp_path, monkeypatch, [n for n in NOMES if n != "claude"])
    rc, it = _estados(capsys)
    assert rc == 0
    assert it["claude"]["estado"] == "aviso"
    assert "descrever.py" in it["claude"]["acao"]


def test_doctor_json_valido_e_apelido(home, tmp_path, monkeypatch, capsys):
    _path_falso(tmp_path, monkeypatch)
    rc = cli.main(["diagnostico", "--json"])
    dado = json.loads(capsys.readouterr().out)
    assert rc == 0 and dado["falhas"] == 0
    nomes = {i["nome"] for i in dado["itens"]}
    assert {"python", "git", "claude", "structurizr", "dot", "java", "node", "skill", "agentes"} <= nomes
    assert all(i["estado"] in ("ok", "aviso", "falha") for i in dado["itens"])


def test_skill_nao_instalada_vira_aviso_com_comando(home, tmp_path, monkeypatch, capsys):
    _path_falso(tmp_path, monkeypatch)
    rc, it = _estados(capsys)
    assert rc == 0
    for n in ("skill", "agentes"):
        assert it[n]["estado"] == "aviso"
        assert "python -m lodemap instalar --perfil padrao --aplicar" in it[n]["acao"]


def test_doctor_repo_sem_mapa_nem_consentimento(home, tmp_path, monkeypatch, capsys):
    _path_falso(tmp_path, monkeypatch)
    repo = tmp_path / "proj"
    repo.mkdir()
    rc, it = _estados(capsys, "--repo", str(repo))
    assert rc == 0
    assert it["mapa"]["estado"] == "aviso" and it["consentimento"]["estado"] == "aviso"


def test_dot_na_pasta_de_ferramentas_conta(home, tmp_path, monkeypatch, capsys):
    _path_falso(tmp_path, monkeypatch, [n for n in NOMES if n != "dot"])
    rc, it = _estados(capsys)
    assert it["dot"]["estado"] == "aviso"
    g = home / ".structurizr" / "graphviz" / "bin"
    g.mkdir(parents=True)
    (g / ("dot.exe" if os.name == "nt" else "dot")).write_text("x")
    rc, it = _estados(capsys)
    assert rc == 0 and it["dot"]["estado"] == "ok"
