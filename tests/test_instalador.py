"""Instalador em HOME temporário: os 3 perfis com plano sem efeito, aplicar, idempotência, reverter e conflitos."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from lodemap import RAIZ, cli, instalador

PY = "python"
SETTINGS_ORIGINAL = {
    "hooks": {"Stop": [{"hooks": [{"type": "command", "command": "synapse hook review-nudge"}]}],
              "SessionStart": [{"matcher": "", "hooks": [{"type": "command", "command": "synapse hook session-start"}]}]},
    "env": {"OUTRA": "1"},
    "theme": "dark",
}
CLAUDE_MD = "# Minhas regras\n\nResponda curto.\n"


def _foto(home: Path) -> dict[str, bytes]:
    return {p.relative_to(home).as_posix(): p.read_bytes() for p in sorted(home.rglob("*")) if p.is_file()}


def _preparar(home: Path) -> None:
    c = home / ".claude"
    (c / "settings.json").write_text(json.dumps(SETTINGS_ORIGINAL, indent=2), encoding="utf-8")
    (c / "CLAUDE.md").write_text(CLAUDE_MD, encoding="utf-8")


@pytest.mark.parametrize("perfil", ["minimo", "padrao"])
def test_ciclo_completo_por_perfil(home, perfil):
    _preparar(home)
    antes = _foto(home)
    plano = instalador.planejar(perfil, home, python=PY)
    assert plano["ops"] and not plano["conflitos"]
    assert _foto(home) == antes, "plano não pode escrever nada"

    man = instalador.aplicar(plano)
    skill = home / ".claude" / "skills" / "lodemap"
    assert instalador._mesmo(skill, RAIZ)
    novo = json.loads((home / ".claude" / "settings.json").read_text(encoding="utf-8"))
    assert novo["hooks"]["Stop"] == SETTINGS_ORIGINAL["hooks"]["Stop"], "hook de outro dono intocado"
    assert novo["env"] == {"OUTRA": "1"} and novo["theme"] == "dark"
    assert "modelSettings" not in novo and set(novo["hooks"]) == {"Stop", "SessionStart"}
    agentes = home / ".claude" / "agents"
    assert sorted(p.name for p in agentes.glob("*.md")) == sorted(p.name for p in (RAIZ / "agents").glob("lodemap-*.md"))
    avisos = [h["command"] for g in novo["hooks"]["SessionStart"] for h in g["hooks"] if "aviso_lodemap.py" in h["command"]]
    assert bool(avisos) == (perfil == "padrao")
    assert (home / ".claude" / "CLAUDE.md").read_text(encoding="utf-8") == CLAUDE_MD

    segundo = instalador.planejar(perfil, home, python=PY)
    assert segundo["ops"] == [] and segundo["conflitos"] == [], "idempotente: segundo plano = 0 operações"
    assert instalador.aplicar(segundo) is None

    instalador.reverter(man)
    depois = _foto(home)
    depois = {k: v for k, v in depois.items() if not k.startswith(".claude/.lodemap-instalador/")}
    assert depois == antes, "reverter restaura os bytes"
    assert not skill.exists()


def test_opcoes_desligaveis(home):
    p = instalador.planejar("padrao", home, python=PY, sem=["aviso"])
    assert "aviso" not in p["opcoes"] and not any(o["opcao"] == "aviso" for o in p["ops"])
    assert "aviso" in instalador.planejar("minimo", home, python=PY, com=["aviso"])["opcoes"]
    with pytest.raises(ValueError):
        instalador.planejar("padrao", home, python=PY, sem=["nao-existe"])


def test_conflitos_recusados_sem_forcar(home):
    c = home / ".claude"
    (c / "agents").mkdir()
    (c / "agents" / "lodemap-gerador.md").write_text("agente de outra pessoa", encoding="utf-8")
    (c / "skills" / "lodemap").mkdir(parents=True)
    (c / "skills" / "lodemap" / "SKILL.md").write_text("outra skill", encoding="utf-8")
    antes = _foto(home)
    plano = instalador.planejar("padrao", home, python=PY)
    assert len(plano["conflitos"]) == 2, plano["conflitos"]
    with pytest.raises(SystemExit):
        instalador.aplicar(plano)
    assert _foto(home) == antes
    forcado = instalador.planejar("padrao", home, python=PY, forcar=True)
    assert not forcado["conflitos"]
    man = instalador.aplicar(forcado)
    assert instalador._mesmo(c / "skills" / "lodemap", RAIZ)
    instalador.reverter(man)
    assert {k: v for k, v in _foto(home).items() if ".lodemap-instalador" not in k} == antes


def test_reverter_recusa_arquivo_mudado(home):
    _preparar(home)
    man = instalador.aplicar(instalador.planejar("padrao", home, python=PY))
    (home / ".claude" / "settings.json").write_text("{}", encoding="utf-8")
    with pytest.raises(SystemExit):
        instalador.reverter(man)


def test_cli_plano_nao_escreve(home, capsys):
    _preparar(home)
    antes = _foto(home)
    assert cli.main(["instalar", "--perfil", "padrao", "--home", str(home), "--python", PY]) == 0
    out = capsys.readouterr().out
    assert "plano (nada é escrito" in out and "[aviso]" in out
    assert _foto(home) == antes
    assert cli.main(["instalar", "--perfil", "padrao", "--aplicar", "--home", str(home), "--python", PY]) == 0
    assert cli.main(["reverter", "--home", str(home)]) == 0
    assert {k: v for k, v in _foto(home).items() if ".lodemap-instalador" not in k} == antes


def test_a_skill_traz_os_seus_seis_agentes_do_mapa_ate_no_perfil_minimo(home):
    esperados = sorted(p.name for p in (RAIZ / "agents").glob("lodemap-*.md"))
    assert len(esperados) == 6
    p = instalador.planejar("minimo", home, python=PY)
    assert not p["conflitos"]
    alvos = sorted(Path(t["alvo"]).name for t in p["textos"] if "agents" in Path(t["alvo"]).parts)
    assert alvos == esperados
    man = instalador.aplicar(p)
    for nome in esperados:
        assert (home / ".claude" / "agents" / nome).is_file()
    instalador.reverter(man) if hasattr(instalador, "reverter") else None


def test_agente_alheio_com_o_mesmo_nome_do_mapa_vira_conflito(home):
    pasta = home / ".claude" / "agents"
    pasta.mkdir(parents=True)
    (pasta / "lodemap-gerador.md").write_text("---\nname: outra-coisa\n---\nnao e do Lodemap\n", encoding="utf-8")
    p = instalador.planejar("minimo", home, python=PY)
    assert any("lodemap-gerador.md" in c for c in p["conflitos"])


def test_reverter_manifesto_inexistente_falha_com_mensagem(home):
    with pytest.raises(SystemExit, match="manifesto não encontrado"):
        instalador.reverter(home / "nao-existe" / "manifesto.json")


def test_reverter_marca_o_manifesto_e_o_ultimo_passa_para_o_anterior(home):
    p1 = instalador.planejar("minimo", home, python=PY)
    m1 = instalador.aplicar(p1)
    p2 = instalador.planejar("padrao", home, python=PY)
    m2 = instalador.aplicar(p2)
    assert instalador.ultimo_manifesto(home) == m2
    instalador.reverter(m2)
    assert instalador.ultimo_manifesto(home) == m1, "o manifesto já revertido não é o último"
    with pytest.raises(SystemExit, match="já foi revertido"):
        instalador.reverter(m2)
    instalador.reverter(m1)
    assert instalador.ultimo_manifesto(home) is None


def test_recusa_de_arquivo_criado_pela_instalacao_manda_apagar_e_nao_cita_none(home):
    p = instalador.planejar("padrao", home, python=PY)
    man = instalador.aplicar(p)
    criado = next(Path(t["alvo"]) for t in json.loads(man.read_text(encoding="utf-8"))["arquivos"]
                  if t["backup"] is None)
    criado.write_text(criado.read_text(encoding="utf-8") + "\nedicao do dono\n", encoding="utf-8")
    with pytest.raises(SystemExit) as e:
        instalador.reverter(man)
    msg = str(e.value)
    assert "None" not in msg and "apague" in msg and str(criado) in msg


def test_settings_invalido_diz_qual_arquivo_esta_quebrado(home, capsys):
    (home / ".claude" / "settings.json").write_text("{ isso nao e json", encoding="utf-8")
    rc = cli.main(["instalar", "--perfil", "padrao", "--home", str(home), "--python", PY])
    saida = capsys.readouterr().out
    assert rc == 2 and "settings.json" in saida and "JSON inválido" in saida


def test_reverter_remove_as_pastas_que_a_instalacao_deixou_vazias(home):
    man = instalador.aplicar(instalador.planejar("padrao", home, python=PY))
    assert (home / ".claude" / "agents").is_dir()
    instalador.reverter(man)
    assert not (home / ".claude" / "agents").exists() and not (home / ".claude" / "skills").exists()
    assert (home / ".claude").is_dir(), "a pasta .claude do usuário fica"


def test_reverter_nao_apaga_pasta_com_arquivo_do_usuario(home):
    man = instalador.aplicar(instalador.planejar("padrao", home, python=PY))
    meu = home / ".claude" / "agents" / "meu-agente.md"
    meu.write_text("meu", encoding="utf-8")
    instalador.reverter(man)
    assert meu.read_text(encoding="utf-8") == "meu"


def test_status_diz_qual_home_esta_olhando(home, capsys):
    cli.main(["status", "--home", str(home), "--python", PY])
    assert f"HOME alvo: {home}" in capsys.readouterr().out


def test_o_pacote_nao_traz_o_workflow_do_synapse(home):
    """O Lodemap é o mapa e a documentação; os agentes padrão, os hooks de segurança e a telemetria são do Synapse."""
    rastreados = subprocess.run(
        ["git", "-C", str(RAIZ), "ls-files", "harness", "lodemap/agentes.py", "templates/structurizr/agentes",
         "templates/structurizr/scripts/gerar_agentes.py"], capture_output=True, text=True, encoding="utf-8")
    assert rastreados.returncode == 0 and rastreados.stdout.strip() == "", rastreados.stdout + rastreados.stderr
    assert sorted(instalador.PERFIS) == ["minimo", "padrao"]
    assert set(instalador.OPCOES) == {"skill", "aviso"}
    with pytest.raises(SystemExit):
        cli.main(["agentes", "listar"])
