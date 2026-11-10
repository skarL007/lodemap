"""Terminal em inglês: a regra de idioma, os apelidos dos comandos e das opções, e as mensagens dos scripts.

Nenhum teste depende do idioma da máquina: LODEMAP_IDIOMA é posto explicitamente (o conftest já põe pt por padrão).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest

from lodemap import RAIZ, cli, idioma

PY = sys.executable


# ---------- a regra de idioma ----------

def _mapa(tmp_path, valor):
    arq = tmp_path / "arq"
    arq.mkdir(exist_ok=True)
    (arq / "lodemap.json").write_text(json.dumps({"idioma": valor}), encoding="utf-8")
    return arq


def _sem_sistema(monkeypatch, codigo=""):
    monkeypatch.setattr(idioma, "_codigo_do_sistema", lambda: codigo)


def test_env_vence_o_mapa_e_o_sistema(tmp_path, monkeypatch):
    _sem_sistema(monkeypatch, "pt_BR")
    monkeypatch.setenv("LODEMAP_IDIOMA", "en")
    assert idioma.idioma(_mapa(tmp_path, "pt")) == "en"
    monkeypatch.setenv("LODEMAP_IDIOMA", "PT")  # maiúsculas e espaços não atrapalham
    assert idioma.idioma(_mapa(tmp_path, "en")) == "pt"


def test_mapa_vence_o_sistema(tmp_path, monkeypatch):
    monkeypatch.delenv("LODEMAP_IDIOMA")
    _sem_sistema(monkeypatch, "pt_BR")
    assert idioma.idioma(_mapa(tmp_path, "en")) == "en"
    _sem_sistema(monkeypatch, "en_US")
    assert idioma.idioma(_mapa(tmp_path, "pt")) == "pt"


def test_usar_mapa_vale_para_as_chamadas_seguintes(tmp_path, monkeypatch):
    monkeypatch.delenv("LODEMAP_IDIOMA")
    _sem_sistema(monkeypatch, "pt_BR")
    idioma.usar_mapa(_mapa(tmp_path, "en"))
    assert idioma.idioma() == "en"
    assert idioma.t("olá", "hello") == "hello"
    idioma.usar_mapa(None)
    assert idioma.idioma() == "pt"


@pytest.mark.parametrize("codigo,esperado", [("pt_BR", "pt"), ("pt-PT", "pt"), ("PT_BR.UTF-8", "pt"),
                                             ("en_US", "en"), ("de_DE", "en"), ("fr", "en")])
def test_sistema_pt_vira_pt_o_resto_vira_en(monkeypatch, codigo, esperado):
    monkeypatch.delenv("LODEMAP_IDIOMA")
    _sem_sistema(monkeypatch, codigo)
    assert idioma.idioma() == esperado


def test_sem_nada_o_padrao_e_ingles(monkeypatch):
    monkeypatch.delenv("LODEMAP_IDIOMA")
    _sem_sistema(monkeypatch, "")
    assert idioma.idioma() == "en"


@pytest.mark.parametrize("ruim", ["", "fr", "xx", "português"])
def test_valor_invalido_e_ignorado(tmp_path, monkeypatch, ruim):
    _sem_sistema(monkeypatch, "pt_BR")
    monkeypatch.setenv("LODEMAP_IDIOMA", ruim)
    assert idioma.idioma(_mapa(tmp_path, ruim or "zz")) == "pt"  # cai no sistema
    monkeypatch.setenv("LODEMAP_IDIOMA", ruim)
    _sem_sistema(monkeypatch, "")
    assert idioma.idioma(_mapa(tmp_path, "en")) == "en"  # cai no mapa


def test_mapa_ilegivel_nao_derruba(tmp_path, monkeypatch):
    monkeypatch.delenv("LODEMAP_IDIOMA")
    _sem_sistema(monkeypatch, "en_US")
    arq = tmp_path / "arq"
    arq.mkdir()
    (arq / "lodemap.json").write_text("{não é json", encoding="utf-8")
    assert idioma.idioma(arq) == "en"
    assert idioma.idioma(tmp_path / "nao-existe") == "en"


def test_codigo_do_sistema_le_as_variaveis_de_locale(monkeypatch):
    for n in ("LC_ALL", "LC_MESSAGES", "LANGUAGE", "LANG"):
        monkeypatch.delenv(n, raising=False)
    monkeypatch.setenv("LANG", "pt_BR.UTF-8")
    assert idioma._codigo_do_sistema() == "pt_BR.UTF-8"
    monkeypatch.setenv("LC_ALL", "en_US.UTF-8")  # LC_ALL vem antes de LANG
    assert idioma._codigo_do_sistema() == "en_US.UTF-8"


def test_opcao_poe_o_nome_do_idioma_ativo_primeiro(monkeypatch):
    monkeypatch.setenv("LODEMAP_IDIOMA", "en")
    assert idioma.opcao("--profile", "--perfil") == ("--profile", "--perfil")
    monkeypatch.setenv("LODEMAP_IDIOMA", "pt")
    assert idioma.opcao("--profile", "--perfil") == ("--perfil", "--profile")


# ---------- a CLI do pacote ----------

def _ajuda(capsys, *args):
    with pytest.raises(SystemExit) as e:
        cli.main([*args, "--help"])
    assert e.value.code == 0
    return capsys.readouterr().out


def test_help_geral_em_ingles(monkeypatch, capsys):
    monkeypatch.setenv("LODEMAP_IDIOMA", "en")
    out = _ajuda(capsys)
    assert "living architecture map" in out
    assert "{install,revert,status,plan,consent,revoke,check,doctor}" in out
    assert "commands" in out
    assert "show the install state" in out
    for pt in ("mostra o estado", "comandos", "grava o consentimento"):
        assert pt not in out


def test_help_geral_em_portugues(capsys):
    out = _ajuda(capsys)
    assert "mapa de arquitetura vivo" in out
    assert "{instalar,reverter,status,plano,consentir,revogar,verificar,doctor}" in out


@pytest.mark.parametrize("cmd,trecho", [
    ("install", "install profile"),
    ("revert", "manifest to revert"),
    ("status", "target HOME"),
    ("doctor", "also check this repository"),
    ("plan", "list every file"),
    ("consent", "monthly cap in US$"),
    ("revoke", "scopes to revoke"),
    ("check", "scope to check"),
])
def test_help_de_cada_subcomando_em_ingles(monkeypatch, capsys, cmd, trecho):
    monkeypatch.setenv("LODEMAP_IDIOMA", "en")
    out = _ajuda(capsys, cmd)
    assert trecho in out
    assert "padrão" not in out and "Python dos hooks" not in out


def test_opcoes_em_ingles_vem_primeiro_na_ajuda(monkeypatch, capsys):
    monkeypatch.setenv("LODEMAP_IDIOMA", "en")
    out = _ajuda(capsys, "install")
    assert "--profile {" in out and "--perfil" in out
    assert out.index("--profile") < out.index("--perfil")
    monkeypatch.setenv("LODEMAP_IDIOMA", "pt")
    out = _ajuda(capsys, "install")
    assert out.index("--perfil") < out.index("--profile")


_EXTRA = {"consent": ["--scopes", "gerar"], "check": ["--scope", "gerar"]}


@pytest.mark.parametrize("en,pt", [("install", "instalar"), ("revert", "reverter"), ("plan", "plano"),
                                   ("consent", "consentir"), ("revoke", "revogar"), ("check", "verificar"),
                                   ("doctor", "diagnostico"), ("status", "status")])
def test_nomes_de_comando_nos_dois_idiomas_valem(en, pt):
    p = cli.parser()
    extra = _EXTRA.get(en, [])
    assert p.parse_args([en, *extra]).f is p.parse_args([pt, *extra]).f


def test_opcoes_em_ingles_e_em_portugues_dao_o_mesmo_dest():
    p = cli.parser()
    a = p.parse_args(["install", "--profile", "minimo", "--apply", "--without", "aviso", "--with", "x", "--force"])
    b = p.parse_args(["instalar", "--perfil", "minimo", "--aplicar", "--sem", "aviso", "--com", "x", "--forcar"])
    assert (a.perfil, a.aplicar, a.sem, a.com, a.forcar) == (b.perfil, b.aplicar, b.sem, b.com, b.forcar) == \
           ("minimo", True, "aviso", "x", True)
    a = p.parse_args(["consent", "--scopes", "gerar", "--monthly-budget", "5", "--arch", "x"])
    b = p.parse_args(["consentir", "--escopos", "gerar", "--orcamento-mensal", "5", "--arq", "x"])
    assert (a.escopos, a.orcamento_mensal, a.arq) == (b.escopos, b.orcamento_mensal, b.arq) == ("gerar", 5.0, "x")
    a = p.parse_args(["check", "--scope", "modelo", "--cost", "1.5"])
    b = p.parse_args(["verificar", "--escopo", "modelo", "--custo", "1.5"])
    assert (a.escopo, a.custo) == (b.escopo, b.custo) == ("modelo", 1.5)
    a = p.parse_args(["revert", "--manifest", "m.json"])
    assert a.manifesto == "m.json"
    assert p.parse_args(["plan", "--all"]).todos is True


def test_valores_de_escopo_continuam_em_portugues(monkeypatch, capsys):
    monkeypatch.setenv("LODEMAP_IDIOMA", "en")
    with pytest.raises(SystemExit):
        cli.main(["check", "--scope", "generate"])
    assert "gerar" in capsys.readouterr().err


def test_install_plan_em_ingles(home, monkeypatch, capsys):
    monkeypatch.setenv("LODEMAP_IDIOMA", "en")
    assert cli.main(["install", "--profile", "minimo", "--home", str(home), "--python", PY]) == 0
    out = capsys.readouterr().out
    assert "profile: minimo" in out
    assert "plan (nothing is written; use --apply)" in out
    assert "operation(s)" in out and "conflict(s)" in out
    assert "operação" not in out and "conflito" not in out
    assert '"acao": "create"' in out  # só a exibição muda; os nomes de chave seguem em português


def test_install_aplicar_e_reverter_em_ingles(home, monkeypatch, capsys):
    monkeypatch.setenv("LODEMAP_IDIOMA", "en")
    assert cli.main(["install", "--profile", "minimo", "--apply", "--home", str(home), "--python", PY]) == 0
    out = capsys.readouterr().out
    assert "applied; manifest:" in out and "to revert: python -m lodemap revert --manifest" in out
    assert cli.main(["install", "--profile", "minimo", "--apply", "--home", str(home), "--python", PY]) == 0
    assert "nothing to change" in capsys.readouterr().out
    assert cli.main(["revert", "--home", str(home)]) == 0
    assert "restored:" in capsys.readouterr().out


def test_install_em_portugues_segue_igual(home, capsys):
    assert cli.main(["install", "--profile", "minimo", "--home", str(home), "--python", PY]) == 0
    out = capsys.readouterr().out
    assert "nada é escrito; use --aplicar" in out
    assert '"acao": "cria"' in out


def test_status_e_revert_sem_manifesto_em_ingles(home, monkeypatch, capsys):
    monkeypatch.setenv("LODEMAP_IDIOMA", "en")
    assert cli.main(["status", "--home", str(home), "--python", PY]) == 0
    out = capsys.readouterr().out
    assert "target HOME:" in out and "repository:" in out and "last manifest: none" in out
    assert cli.main(["revert", "--home", str(home)]) == 1
    assert "no manifest found" in capsys.readouterr().out


def _repo(tmp_path):
    repo = tmp_path / "repo"
    (repo / "pkg").mkdir(parents=True)
    (repo / "pkg" / "a.py").write_text("x = 1\n", encoding="utf-8")
    return repo


def test_plan_consent_check_revoke_em_ingles(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LODEMAP_IDIOMA", "en")
    repo = _repo(tmp_path)
    assert cli.main(["plan", "--repo", str(repo)]) == 0
    out = capsys.readouterr().out
    assert "estimated cost of the 1st generation" in out and "this plan spent 0 tokens" in out
    assert "python -m lodemap consent --scopes" in out
    assert "consent: none" in out
    assert cli.main(["check", "--scope", "gerar", "--repo", str(repo)]) == 3
    assert "gerar" in capsys.readouterr().out
    assert cli.main(["consent", "--scopes", "gerar", "--repo", str(repo)]) == 0
    assert "consent recorded:" in capsys.readouterr().out
    assert cli.main(["check", "--scope", "gerar", "--repo", str(repo)]) == 0
    assert cli.main(["revoke", "--scopes", "gerar", "--repo", str(repo)]) == 0
    assert "consent revoked" in capsys.readouterr().out
    assert cli.main(["revoke", "--repo", str(repo)]) == 0
    assert "nothing to revoke" in capsys.readouterr().out


def test_erro_de_valor_em_ingles(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LODEMAP_IDIOMA", "en")
    rc = cli.main(["consent", "--scopes", "inexistente", "--repo", str(_repo(tmp_path))])
    assert rc == 2
    out = capsys.readouterr().out
    assert out.startswith("error:")
    assert "inexistente" in out


def test_doctor_em_ingles(home, monkeypatch, capsys):
    monkeypatch.setenv("LODEMAP_IDIOMA", "en")
    monkeypatch.setenv("PATH", "")
    rc = cli.main(["doctor", "--home", str(home)])
    out = capsys.readouterr().out
    assert rc == 1
    assert "failure(s)" in out and "This diagnosis spent 0 tokens." in out
    assert "what to do:" in out
    assert "falha" not in out and "o que fazer" not in out


def test_doctor_json_mantem_as_chaves_em_portugues(home, monkeypatch, capsys):
    monkeypatch.setenv("LODEMAP_IDIOMA", "en")
    cli.main(["doctor", "--json", "--home", str(home)])
    dado = json.loads(capsys.readouterr().out)
    assert set(dado) == {"itens", "falhas"}
    assert {i["estado"] for i in dado["itens"]} <= {"ok", "aviso", "falha"}


def test_idioma_do_mapa_vale_para_o_comando_que_aponta_o_repo(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("LODEMAP_IDIOMA")
    _sem_sistema(monkeypatch, "pt_BR")
    repo = _repo(tmp_path)
    arq = repo / "docs" / "architecture" / "structurizr"
    arq.mkdir(parents=True)
    (arq / "lodemap.json").write_text(json.dumps({"idioma": "en"}), encoding="utf-8")
    assert cli.main(["plan", "--repo", str(repo)]) == 0
    assert "this plan spent 0 tokens" in capsys.readouterr().out
    assert cli.main(["plano", "--repo", str(_repo(tmp_path / "outro"))]) == 0  # sem mapa: cai no sistema (pt)
    assert "este plano gastou 0 tokens" in capsys.readouterr().out


def test_instalador_conflito_em_ingles(home, monkeypatch):
    from lodemap import instalador
    monkeypatch.setenv("LODEMAP_IDIOMA", "en")
    with pytest.raises(ValueError) as e:
        instalador.planejar("inexistente", home)
    assert "profile" in str(e.value).lower()
    monkeypatch.setenv("LODEMAP_IDIOMA", "pt")
    with pytest.raises(ValueError) as e:
        instalador.planejar("inexistente", home)
    assert "perfil" in str(e.value).lower()


# ---------- scripts/ e scripts do template: --help e mensagens ----------

def _rodar(script, *args, idioma_="en", cwd=None):
    env = dict(os.environ, LODEMAP_IDIOMA=idioma_, PYTHONIOENCODING="utf-8")
    return subprocess.run([PY, str(RAIZ / script), *args], capture_output=True, text=True, encoding="utf-8",
                          env=env, cwd=cwd, timeout=60)


@pytest.mark.parametrize("script,trecho", [
    ("scripts/esqueleto.py", "draft"),
    ("scripts/qualidade.py", "quality rubric"),
    ("scripts/codegraph_ponte.py", "CodeGraph"),
    ("scripts/verificar.py", "usage"),
    ("scripts/inventario.py", "usage"),
    ("scripts/novo_mapa.py", "usage"),
    ("scripts/medir_ast.py", "usage"),
    ("scripts/migrar_para_lodemap.py", "usage"),
    ("templates/structurizr/scripts/atualizar.py", "Regenerates the architecture map"),
    ("templates/structurizr/scripts/ver_arquitetura.py", "usage"),
    ("templates/structurizr/scripts/instalar_gancho.py", "usage"),
    ("templates/structurizr/scripts/lodemap_diff.py", "usage"),
    ("templates/structurizr/scripts/lodemap_decidir.py", "usage"),
    ("templates/structurizr/scripts/lodemap_gancho.py", "usage"),
])
def test_scripts_help_em_ingles(script, trecho):
    r = _rodar(script, "--help")
    assert r.returncode == 0, r.stderr
    assert trecho.lower() in r.stdout.lower(), r.stdout
    for pt in ("padrão", "pasta do", "caminho do", "obrigatório"):
        assert pt not in r.stdout, (pt, r.stdout)


def test_esqueleto_em_ingles_e_aliases(tmp_path):
    repo = tmp_path / "r"
    repo.mkdir()
    r = _rodar("scripts/esqueleto.py", "draft", "--help")
    assert r.returncode == 0, r.stderr
    assert "--source" in r.stdout and "--fonte" in r.stdout
    assert r.stdout.index("--source") < r.stdout.index("--fonte")
    r = _rodar("scripts/esqueleto.py", "rascunho", "--help", idioma_="pt")
    assert r.returncode == 0, r.stderr
    assert r.stdout.index("--fonte") < r.stdout.index("--source")


def test_qualidade_sem_workspace_em_ingles(tmp_path):
    arq = tmp_path / "arq"
    arq.mkdir()
    r = _rodar("scripts/qualidade.py", "--arch", str(arq))
    assert r.returncode != 0
    assert "no workspace.json" in r.stderr
    r = _rodar("scripts/qualidade.py", "--arq", str(arq), idioma_="pt")
    assert "sem workspace.json" in r.stderr


def test_atualizar_help_segue_o_idioma_do_mapa(tmp_path):
    """O script do template roda dentro do projeto do usuário: o idioma vem do lodemap.json ao lado dele."""
    env = {k: v for k, v in os.environ.items() if k != "LODEMAP_IDIOMA"}
    env["LANG"] = "pt_BR.UTF-8"
    pasta = tmp_path / "structurizr"
    (pasta / "scripts").mkdir(parents=True)
    src = RAIZ / "templates" / "structurizr" / "scripts"
    for n in ("atualizar.py", "arq_comum.py"):
        if (src / n).exists():
            (pasta / "scripts" / n).write_bytes((src / n).read_bytes())
    (pasta / "lodemap.json").write_text(json.dumps({"idioma": "en"}), encoding="utf-8")
    r = subprocess.run([PY, str(pasta / "scripts" / "atualizar.py"), "--help"], capture_output=True, text=True,
                       encoding="utf-8", env=env, timeout=60)
    assert r.returncode == 0, r.stderr
    assert "also export the static site" in r.stdout
