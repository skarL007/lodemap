"""lodemap_decidir.py: a política de atualização (nada, scripts, adiar, descrever, modelar, gerar) com 0 tokens.

Tudo roda num repositório git temporário (tmp_path); nada toca as pastas do usuário. O teste de cobertura entregue
ao projeto é instanciado de verdade ({{ARQ_REL}} -> arq) e rodado pelo pytest num subprocesso.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest

from lodemap import RAIZ

SCRIPTS = RAIZ / "templates" / "structurizr" / "scripts"
TESTE_COBERTURA = RAIZ / "templates" / "tests" / "test_arquitetura_cobertura.py"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(RAIZ / "scripts"))
import arq_comum  # noqa: E402
import lodemap_decidir as dec  # noqa: E402
import lodemap_diff  # noqa: E402

pytestmark = pytest.mark.skipif(not shutil.which("git"), reason="precisa do git")

COPIAR = ("arq_comum.py", "lodemap_diff.py", "lodemap_decidir.py", "lodemap_gancho.py")


@pytest.fixture(autouse=True)
def _ambiente(tmp_path, monkeypatch):
    """Sem a skill real do usuário, sem data nem idioma herdados do ambiente."""
    monkeypatch.setenv("LODEMAP_SKILL", str(tmp_path / "sem-skill"))
    monkeypatch.delenv("LODEMAP_HOJE", raising=False)
    monkeypatch.delenv("LODEMAP_IDIOMA", raising=False)


# ------------------------------------------------------------------------------------------------ montagem

def _git(repo: Path, *args: str) -> str:
    r = subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "-C", str(repo), *args],
                       check=True, capture_output=True, text=True, encoding="utf-8")
    return r.stdout.strip()


def _commitar(repo: Path, msg: str = "mudanca") -> None:
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", msg)


def _dsl(comps: dict[str, str], planejados: tuple = ()) -> str:
    linhas = ['sistema = softwareSystem "S" {', '    app = container "App" "d" "Py" {']
    for ident, codigo in comps.items():
        status = "Planejado" if ident in planejados else "Pronto"
        linhas += [f'        {ident} = component "{ident}" "d" "Py" "{status}" {{', "            properties {",
                   f'                "status" "{status}"', f'                "codigo" "{codigo}"', "            }", "        }"]
    return "\n".join(linhas + ["    }", "}"]) + "\n"


def _projeto(tmp_path: Path, politica: dict | None = None, idioma: str = "pt") -> tuple[Path, Path]:
    """Repositório com src/a.py e src/b.py, ambos no modelo, geração marcada em HEAD, scripts e teste instanciados."""
    repo = tmp_path / "repo"
    (repo / "src").mkdir(parents=True)
    (repo / "src" / "a.py").write_text("x = 1\n", encoding="utf-8")
    (repo / "src" / "b.py").write_text("y = 1\n", encoding="utf-8")
    arq = repo / "arq"
    (arq / "model").mkdir(parents=True)
    (arq / "scripts").mkdir()
    cfg = {"projeto": "T", "idioma": idioma, "raiz_codigo": "src", "modulos": ["src/*.py"]}
    if politica is not None:
        cfg["politica"] = politica
    (arq / "lodemap.json").write_text(json.dumps(cfg), encoding="utf-8")
    (arq / "model" / "componentes.dsl").write_text(_dsl({"compA": "src/a.py", "compB": "src/b.py"}), encoding="utf-8")
    for nome in COPIAR:
        shutil.copy2(SCRIPTS / nome, arq / "scripts" / nome)
    (repo / "tests").mkdir()
    texto = TESTE_COBERTURA.read_text(encoding="utf-8").replace("{{ARQ_REL}}", "arq")
    (repo / "tests" / "test_arquitetura_cobertura.py").write_text(texto, encoding="utf-8")
    (repo / ".gitignore").write_text(".lodemap/\n__pycache__/\n.pyt/\n", encoding="utf-8")
    _git(repo, "init", "-q")
    _commitar(repo, "base")
    lodemap_diff.marcar(arq)
    return repo, arq


def _politica(arq: Path, **valores) -> None:
    cfg = json.loads((arq / "lodemap.json").read_text(encoding="utf-8"))
    cfg["politica"] = valores
    (arq / "lodemap.json").write_text(json.dumps(cfg), encoding="utf-8")


def _novo_modulo(repo: Path, nome: str) -> None:
    (repo / "src" / nome).write_text("novo = 1\n", encoding="utf-8")


def _cli(arq: Path, *args: str, hoje: str | None = None) -> subprocess.CompletedProcess:
    env = {**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}
    env.pop("LODEMAP_HOJE", None)
    if hoje:
        env["LODEMAP_HOJE"] = hoje
    return subprocess.run([sys.executable, str(arq / "scripts" / "lodemap_decidir.py"), *args], cwd=arq, env=env,
                          capture_output=True, text=True, encoding="utf-8", errors="replace")


def _skill(tmp_path: Path, dados: dict, codigo: int = 0) -> Path:
    pasta = tmp_path / "skill"
    (pasta / "scripts").mkdir(parents=True)
    (pasta / "scripts" / "esqueleto.py").write_text(
        "import json, sys\nif sys.argv[1:3] != ['pendencias', '--arq']:\n    sys.exit(3)\n"
        f"print(json.dumps({dados!r}))\nsys.exit({codigo})\n", encoding="utf-8")
    return pasta


# ------------------------------------------------------------------------------------------------ política padrão

def test_nada_mudou_e_nada(tmp_path):
    _, arq = _projeto(tmp_path)
    d = dec.decidir(arq, usar_skill=False)
    assert d["acao"] == "nada" and d["usa_modelo"] is False and d["lote"] is None and d["proximo"] == []
    assert d["divida"]["modulos_mudados"] == 0 and d["divida"]["commits_desde"] == 0
    assert d["politica"] == dec.PADROES
    assert any("nada mudou" in m for m in d["motivos"])


def test_mudanca_abaixo_da_cadencia_e_nada_com_o_motivo(tmp_path):
    repo, arq = _projeto(tmp_path)
    (repo / "src" / "a.py").write_text("x = 2\n", encoding="utf-8")
    _commitar(repo)
    d = dec.decidir(arq, usar_skill=False)
    assert d["acao"] == "nada" and d["divida"]["modulos_mudados"] == 1 and d["divida"]["commits_desde"] == 1
    assert d["motivos"][0] == "1 commit(s) desde a última geração; regenera em 10"


def test_cadencia_alcancada_manda_regenerar_por_scripts(tmp_path):
    repo, arq = _projeto(tmp_path, {"commits_para_regenerar": 2})
    for i in (2, 3):
        (repo / "src" / "a.py").write_text(f"x = {i}\n", encoding="utf-8")
        _commitar(repo)
    d = dec.decidir(arq, usar_skill=False)
    assert d["acao"] == "scripts" and d["usa_modelo"] is False
    assert d["divida"]["commits_desde"] == 2
    cmd = d["proximo"][0]
    assert cmd.startswith("python scripts/atualizar.py --incremental --checkpoint \"")


def test_fonte_da_arquitetura_mudada_manda_regenerar_por_scripts(tmp_path):
    repo, arq = _projeto(tmp_path)
    dsl = arq / "model" / "componentes.dsl"
    dsl.write_text("// ajuste\n" + dsl.read_text(encoding="utf-8"), encoding="utf-8")
    _commitar(repo)
    d = dec.decidir(arq, usar_skill=False)
    assert d["acao"] == "scripts" and d["divida"]["modulos_mudados"] == 0
    assert "arquivos-fonte da arquitetura mudaram" in d["motivos"][0]


def test_documento_gerado_nao_conta_como_fonte(tmp_path):
    repo, arq = _projeto(tmp_path)
    (arq / "docs").mkdir()
    (arq / "docs" / "02-mapa-de-status.md").write_text("gerado\n", encoding="utf-8")
    _commitar(repo)
    assert dec.decidir(arq, usar_skill=False)["acao"] == "nada"


def test_modulo_novo_com_tolerancia_zero_pede_modelagem(tmp_path):
    repo, arq = _projeto(tmp_path)
    _novo_modulo(repo, "c.py")
    d = dec.decidir(arq, usar_skill=False)
    assert d["acao"] == "modelar" and d["usa_modelo"] is True
    assert d["divida"]["modulos_fora"] == ["src/c.py"] and "src/c.py" in d["motivos"][0]
    assert d["lote"]["modulos_fora"] == ["src/c.py"]
    assert "uma vez para o lote todo" in d["proximo"][0]


def test_com_tolerancia_o_modulo_novo_e_adiado_e_depois_deixa_de_pedir_modelo(tmp_path):
    repo, arq = _projeto(tmp_path, {"tolerancia_modulos": 2})
    _novo_modulo(repo, "c.py")
    d = dec.decidir(arq, usar_skill=False, data=date(2026, 1, 1))
    assert d["acao"] == "adiar" and d["usa_modelo"] is False
    assert d["proximo"] == ["python scripts/lodemap_decidir.py --adiar"]
    r = _cli(arq, "--adiar", hoje="2026-01-01")
    assert r.returncode == 0, r.stdout + r.stderr
    p = arq / "pendentes.json"
    assert p.is_file()
    bruto = p.read_bytes()
    assert bruto.endswith(b"\n") and b"\r" not in bruto
    dados = json.loads(bruto.decode("utf-8"))
    assert dados == {"versao": 1, "modulos": {"src/c.py": {"desde": "2026-01-01", "commit": _git(repo, "rev-parse", "--short", "HEAD")}}}
    d = dec.decidir(arq, usar_skill=False, data=date(2026, 1, 2))
    assert d["acao"] not in ("modelar", "adiar") and d["acao"] == "scripts", d["motivos"]
    assert d["divida"]["adiados"] == [{"modulo": "src/c.py", "desde": "2026-01-01", "vence": "2026-01-15"}]
    assert any("podem esperar até 2026-01-15" in m for m in d["motivos"])


def test_prazo_vencido_pede_modelagem(tmp_path):
    repo, arq = _projeto(tmp_path, {"tolerancia_modulos": 2})
    _novo_modulo(repo, "c.py")
    assert _cli(arq, "--adiar", hoje="2026-01-01").returncode == 0
    ultimo_dia = dec.decidir(arq, usar_skill=False, data=date(2026, 1, 15))
    assert ultimo_dia["acao"] != "modelar", "no dia do prazo ainda vale"
    d = dec.decidir(arq, usar_skill=False, data=date(2026, 1, 16))
    assert d["acao"] == "modelar" and [v["modulo"] for v in d["divida"]["vencidos"]] == ["src/c.py"]
    assert "venceu em 2026-01-15" in " ".join(d["motivos"])
    # a data também vem do ambiente
    r = _cli(arq, hoje="2026-01-16")
    assert json.loads(r.stdout)["acao"] == "modelar"


def test_tolerancia_dias_vem_da_politica(tmp_path):
    repo, arq = _projeto(tmp_path, {"tolerancia_modulos": 2, "tolerancia_dias": 3})
    _novo_modulo(repo, "c.py")
    assert _cli(arq, "--adiar", hoje="2026-03-01").returncode == 0
    assert dec.decidir(arq, usar_skill=False, data=date(2026, 3, 4))["acao"] != "modelar"
    assert dec.decidir(arq, usar_skill=False, data=date(2026, 3, 5))["acao"] == "modelar"


def test_acima_do_limite_pede_modelagem_e_o_adiar_recusa(tmp_path):
    repo, arq = _projeto(tmp_path, {"tolerancia_modulos": 1})
    _novo_modulo(repo, "c.py")
    _novo_modulo(repo, "d.py")
    d = dec.decidir(arq, usar_skill=False)
    assert d["acao"] == "modelar" and "acima da tolerância de 1" in d["motivos"][0]
    r = _cli(arq, "--adiar")
    assert r.returncode == 1 and "acima da tolerância de 1" in r.stdout
    assert not (arq / "pendentes.json").exists()


def test_caminho_quebrado_pede_modelagem_mas_planejado_e_ramo_nao(tmp_path):
    repo, arq = _projeto(tmp_path)
    dsl = arq / "model" / "componentes.dsl"
    dsl.write_text(_dsl({"compA": "src/a.py", "compB": "src/b.py", "compX": "src/some.py"}), encoding="utf-8")
    d = dec.decidir(arq, usar_skill=False)
    assert d["acao"] == "modelar" and d["divida"]["caminhos_quebrados"] == ["compX: src/some.py"]
    dsl.write_text(_dsl({"compA": "src/a.py", "compB": "src/b.py", "compX": "src/some.py"}, planejados=("compX",)),
                   encoding="utf-8")
    assert dec.decidir(arq, usar_skill=False)["divida"]["caminhos_quebrados"] == []


def test_sem_geracao_anterior(tmp_path):
    repo, arq = _projeto(tmp_path)
    (arq / ".lodemap" / "estado.json").unlink()
    d = dec.decidir(arq, usar_skill=False)
    assert d["acao"] == "scripts" and d["divida"]["commits_desde"] is None and d["divida"]["dias_desde"] is None
    (arq / "model" / "componentes.dsl").write_text('sistema = softwareSystem "S" {\n}\n', encoding="utf-8")
    d = dec.decidir(arq, usar_skill=False)
    assert d["acao"] == "gerar" and d["usa_modelo"] is True


def test_clone_novo_com_modulo_fora_do_modelo_nao_se_esconde_atras_de_scripts(tmp_path):
    """Num clone novo (ou no CI) não há estado.json: módulo fora do modelo continua pedindo modelagem, não só scripts."""
    repo, arq = _projeto(tmp_path)
    (arq / ".lodemap" / "estado.json").unlink()
    _novo_modulo(repo, "c.py")
    d = dec.decidir(arq, usar_skill=False)
    assert d["acao"] == "modelar" and d["divida"]["modulos_fora"] == ["src/c.py"]
    assert any("sem geração anterior" in m for m in d["motivos"]) is False  # o motivo de scripts só entra se for a ação


def test_valores_invalidos_da_politica_caem_no_padrao():
    assert dec.politica({}) == dec.PADROES
    p = dec.politica({"politica": {"tolerancia_modulos": -1, "tolerancia_dias": "7", "revisoes_para_atualizar": True,
                                   "relacoes_para_atualizar": 2.5, "commits_para_regenerar": 0}})
    assert p == {**dec.PADROES, "commits_para_regenerar": 0}
    assert dec.politica({"politica": [1, 2]}) == dec.PADROES


# ------------------------------------------------------------------------------------------------ --adiar

def test_adiar_nao_renova_datas_poda_o_coberto_e_apaga_o_vazio(tmp_path):
    repo, arq = _projeto(tmp_path, {"tolerancia_modulos": 3})
    _novo_modulo(repo, "c.py")
    assert _cli(arq, "--adiar", hoje="2026-01-01").returncode == 0
    _novo_modulo(repo, "d.py")
    assert _cli(arq, "--adiar", hoje="2026-01-09").returncode == 0
    mods = json.loads((arq / "pendentes.json").read_text(encoding="utf-8"))["modulos"]
    assert list(mods) == ["src/c.py", "src/d.py"]
    assert mods["src/c.py"]["desde"] == "2026-01-01", "rodar de novo não estende o prazo"
    assert mods["src/d.py"]["desde"] == "2026-01-09"
    # c.py entra no modelo: a entrada sai; d.py continua
    (arq / "model" / "componentes.dsl").write_text(
        _dsl({"compA": "src/a.py", "compB": "src/b.py", "compC": "src/c.py"}), encoding="utf-8")
    assert _cli(arq, "--adiar", hoje="2026-01-10").returncode == 0
    assert list(json.loads((arq / "pendentes.json").read_text(encoding="utf-8"))["modulos"]) == ["src/d.py"]
    # d.py some do disco: o arquivo vazio é apagado
    (repo / "src" / "d.py").unlink()
    assert _cli(arq, "--adiar", hoje="2026-01-11").returncode == 0
    assert not (arq / "pendentes.json").exists()


def test_adiar_com_tolerancia_zero_recusa_e_nao_grava(tmp_path):
    repo, arq = _projeto(tmp_path)
    _novo_modulo(repo, "c.py")
    r = _cli(arq, "--adiar")
    assert r.returncode == 1 and "tolerancia_modulos" in r.stdout and "nada foi gravado" in r.stdout
    assert not (arq / "pendentes.json").exists()


# ------------------------------------------------------------------------------------------------ sinais da skill

@pytest.mark.parametrize("revisoes,relacoes,esperado", [
    (10, 0, "descrever"), (9, 9, "nada"), (0, 10, "modelar"), (10, 10, "modelar"), (3, 0, "nada")])
def test_sinais_da_skill_nos_limites(tmp_path, revisoes, relacoes, esperado):
    _, arq = _projeto(tmp_path)
    skill = _skill(tmp_path, {"componentes_novos": [], "componentes_revisar": [f"m{i}" for i in range(revisoes)],
                              "relacoes_novas": [f"r{i}" for i in range(relacoes)], "removidos": []})
    d = dec.decidir(arq, skill=skill)
    assert d["acao"] == esperado, d["motivos"]
    assert d["divida"]["revisoes"] == revisoes and d["divida"]["relacoes_novas"] == relacoes
    assert d["usa_modelo"] is (esperado != "nada")
    if esperado != "nada":
        assert d["lote"]["revisoes"] == revisoes and d["lote"]["relacoes_novas"] == relacoes


def test_limites_da_skill_vem_da_politica(tmp_path):
    _, arq = _projeto(tmp_path, {"revisoes_para_atualizar": 3, "relacoes_para_atualizar": 2})
    skill = _skill(tmp_path, {"componentes_revisar": ["a", "b", "c"], "relacoes_novas": ["x"]})
    assert dec.decidir(arq, skill=skill)["acao"] == "descrever"
    skill = _skill(tmp_path / "outra", {"componentes_revisar": [], "relacoes_novas": ["x", "y"]})
    assert dec.decidir(arq, skill=skill)["acao"] == "modelar"


def test_lote_junta_os_modulos_adiados_e_os_sinais_da_skill(tmp_path):
    repo, arq = _projeto(tmp_path, {"tolerancia_modulos": 2, "revisoes_para_atualizar": 1})
    _novo_modulo(repo, "c.py")
    assert _cli(arq, "--adiar", hoje="2026-01-01").returncode == 0
    skill = _skill(tmp_path, {"componentes_revisar": ["a"], "relacoes_novas": []})
    d = dec.decidir(arq, skill=skill, data=date(2026, 1, 2))
    assert d["acao"] == "descrever" and d["lote"]["modulos_fora"] == ["src/c.py"] and d["lote"]["revisoes"] == 1


def test_sem_skill_os_numeros_ficam_nulos_com_motivo_nd(tmp_path):
    _, arq = _projeto(tmp_path)
    d = dec.decidir(arq)  # LODEMAP_SKILL aponta para uma pasta que não existe
    assert d["divida"]["revisoes"] is None and d["divida"]["relacoes_novas"] is None
    assert any(m.startswith("n/d") for m in d["motivos"]) and d["acao"] == "nada"
    assert dec.decidir(arq, skill=tmp_path / "tambem-nao-existe")["divida"]["revisoes"] is None


def test_skill_que_falha_ou_sem_decisoes_nao_inventa_numero(tmp_path):
    _, arq = _projeto(tmp_path)
    quebrada = _skill(tmp_path / "q", {"componentes_revisar": ["a"] * 50}, codigo=1)
    d = dec.decidir(arq, skill=quebrada)
    assert d["divida"]["revisoes"] is None and d["acao"] == "nada" and any(m.startswith("n/d") for m in d["motivos"])
    vazia = _skill(tmp_path / "v", {"componentes_novos": ["a"] * 50, "componentes_revisar": [], "relacoes_novas": ["x"] * 50,
                                    "removidos": [], "sem_decisoes": True})
    d = dec.decidir(arq, skill=vazia)
    assert d["divida"]["revisoes"] is None and d["divida"]["relacoes_novas"] is None and d["acao"] == "nada"


def test_skill_vem_da_env_e_o_argumento_vence(tmp_path, monkeypatch):
    _, arq = _projeto(tmp_path)
    da_env = _skill(tmp_path / "e", {"componentes_revisar": ["a"] * 10, "relacoes_novas": []})
    monkeypatch.setenv("LODEMAP_SKILL", str(da_env))
    assert dec.decidir(arq)["acao"] == "descrever"
    do_arg = _skill(tmp_path / "a", {"componentes_revisar": [], "relacoes_novas": []})
    assert dec.decidir(arq, skill=do_arg)["acao"] == "nada"


# ------------------------------------------------------------------------------------------------ CLI e idioma

def test_cli_json_resumo_e_gancho(tmp_path):
    repo, arq = _projeto(tmp_path, {"commits_para_regenerar": 2})
    j = json.loads(_cli(arq).stdout)
    assert j["acao"] == "nada" and set(j) == {"acao", "usa_modelo", "motivos", "divida", "lote", "politica", "proximo"}
    r = _cli(arq, "--resumo")
    assert r.returncode == 0 and len(r.stdout.splitlines()) == 1 and r.stdout.startswith("Lodemap: nada")
    (repo / "src" / "a.py").write_text("x = 2\n", encoding="utf-8")
    _commitar(repo)
    g = _cli(arq, "--gancho", "post-commit")
    assert g.returncode == 1 and "1 commit(s)" in g.stdout and len(g.stdout.splitlines()) == 1
    assert _cli(arq, "--gancho", "post-merge").returncode == 0, "post-merge mantém a regra de sempre"
    (repo / "src" / "a.py").write_text("x = 3\n", encoding="utf-8")
    _commitar(repo)
    assert _cli(arq, "--gancho", "post-commit").returncode == 0


def test_gancho_post_merge_sai_1_quando_nada_mudou(tmp_path):
    _, arq = _projeto(tmp_path)
    assert _cli(arq, "--gancho", "post-merge").returncode == 1


def test_gancho_post_commit_com_modulo_fora_do_modelo_nao_regenera(tmp_path):
    repo, arq = _projeto(tmp_path)
    _novo_modulo(repo, "c.py")
    r = _cli(arq, "--gancho", "post-commit")
    assert r.returncode == 1 and "modelar" in r.stdout


def test_mapa_em_ingles_responde_em_ingles(tmp_path):
    repo, arq = _projeto(tmp_path, idioma="en")
    _novo_modulo(repo, "c.py")
    r = _cli(arq, "--resumo")
    assert "outside the model" in r.stdout and "fora" not in r.stdout
    assert "module(s) outside the model" in json.loads(_cli(arq).stdout)["motivos"][0]


def test_resumo_diz_o_que_espera(tmp_path):
    repo, arq = _projeto(tmp_path, {"tolerancia_modulos": 2})
    _novo_modulo(repo, "c.py")
    assert _cli(arq, "--adiar", hoje="2026-01-01").returncode == 0
    r = _cli(arq, "--resumo", hoje="2026-01-02")
    assert "esperam: 1 módulo(s) até 2026-01-15" in r.stdout


# ------------------------------------------------------------------------------------------------ teste de cobertura instanciado

def _cobertura(repo: Path, hoje: str | None = None) -> subprocess.CompletedProcess:
    env = {**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}
    env.pop("LODEMAP_HOJE", None)
    if hoje:
        env["LODEMAP_HOJE"] = hoje
    return subprocess.run([sys.executable, "-m", "pytest", "tests/test_arquitetura_cobertura.py", "-q", "-k",
                           "todo_modulo_esta_no_modelo", "-p", "no:cacheprovider", "--basetemp", str(repo.parent / "bt")],
                          cwd=repo, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")


def test_cobertura_sem_politica_mantem_a_mensagem_de_sempre(tmp_path):
    repo, arq = _projeto(tmp_path)
    assert _cobertura(repo).returncode == 0
    _novo_modulo(repo, "c.py")
    r = _cobertura(repo)
    assert r.returncode == 1
    assert "1 módulo(s) fora da arquitetura. Ligue cada um a um componente (propriedade codigo em arq/model/*.dsl) " \
           "ou, com motivo, em EXCECOES:" in r.stdout and "src/c.py" in r.stdout
    # a pendência registrada não vale com tolerância 0
    (arq / "pendentes.json").write_text(json.dumps({"versao": 1, "modulos": {"src/c.py": {"desde": "2026-01-01", "commit": "x"}}}),
                                        encoding="utf-8")
    assert _cobertura(repo, "2026-01-02").returncode == 1


def test_cobertura_dentro_da_tolerancia_passa(tmp_path):
    repo, arq = _projeto(tmp_path, {"tolerancia_modulos": 2})
    assert _cobertura(repo).returncode == 0
    _novo_modulo(repo, "c.py")
    assert _cli(arq, "--adiar", hoje="2026-01-01").returncode == 0
    r = _cobertura(repo, "2026-01-10")
    assert r.returncode == 0, r.stdout[-1500:]


def test_cobertura_acima_do_limite_falha_e_nomeia_os_arquivos(tmp_path):
    repo, arq = _projeto(tmp_path, {"tolerancia_modulos": 1})
    _novo_modulo(repo, "c.py")
    _novo_modulo(repo, "d.py")
    r = _cobertura(repo, "2026-01-10")
    assert r.returncode == 1
    assert "acima da tolerância de 1" in r.stdout and "src/c.py" in r.stdout and "src/d.py" in r.stdout


def test_cobertura_com_prazo_vencido_falha_com_a_data(tmp_path):
    repo, arq = _projeto(tmp_path, {"tolerancia_modulos": 2})
    _novo_modulo(repo, "c.py")
    assert _cli(arq, "--adiar", hoje="2026-01-01").returncode == 0
    assert _cobertura(repo, "2026-01-15").returncode == 0
    r = _cobertura(repo, "2026-01-16")
    assert r.returncode == 1
    assert "Prazo vencido" in r.stdout and "src/c.py (venceu em 2026-01-15)" in r.stdout


def test_cobertura_sem_registro_falha_e_aponta_o_comando(tmp_path):
    repo, arq = _projeto(tmp_path, {"tolerancia_modulos": 2})
    _novo_modulo(repo, "c.py")
    r = _cobertura(repo, "2026-01-10")
    assert r.returncode == 1
    assert "sem prazo registrado em pendentes.json" in r.stdout and "src/c.py" in r.stdout
    assert "python arq/scripts/lodemap_decidir.py --adiar" in r.stdout


def test_cobertura_em_ingles(tmp_path):
    repo, arq = _projeto(tmp_path, {"tolerancia_modulos": 1}, idioma="en")
    _novo_modulo(repo, "c.py")
    r = _cobertura(repo, "2026-01-10")
    assert r.returncode == 1 and "have no deadline in pendentes.json" in r.stdout
    _novo_modulo(repo, "d.py")
    assert "over the tolerance of 1" in _cobertura(repo, "2026-01-10").stdout


def test_cobertura_respeita_excecoes_com_tolerancia(tmp_path):
    repo, arq = _projeto(tmp_path, {"tolerancia_modulos": 1})
    _novo_modulo(repo, "c.py")
    teste = repo / "tests" / "test_arquitetura_cobertura.py"
    teste.write_text(teste.read_text(encoding="utf-8").replace("EXCECOES: dict[str, str] = {}",
                                                               'EXCECOES: dict[str, str] = {"src/c.py": "rascunho"}'),
                     encoding="utf-8")
    assert _cobertura(repo, "2026-01-10").returncode == 0


# ------------------------------------------------------------------------------------------------ paridade com o teste

def test_fora_do_modelo_e_caminhos_quebrados_batem_com_o_teste_de_cobertura(tmp_path):
    repo, arq = _projeto(tmp_path)
    cfg = json.loads((arq / "lodemap.json").read_text(encoding="utf-8"))
    cfg["modulos"] = ["src/*.py", "src/*/", "tools/*.sh"]
    (arq / "lodemap.json").write_text(json.dumps(cfg), encoding="utf-8")
    for pasta in ("pac", "par", "solta", "node_modules"):
        (repo / "src" / pasta).mkdir()
        (repo / "src" / pasta / "x.py").write_text("v = 1\n", encoding="utf-8")
    _novo_modulo(repo, "c.py")
    (repo / "tools").mkdir()
    for nome in ("run.sh", "outro.sh"):
        (repo / "tools" / nome).write_text("echo\n", encoding="utf-8")
    (arq / "model" / "componentes.dsl").write_text("""\
sistema = softwareSystem "S" {
    app = container "App" "d" "Py" {
        src = component "Raiz" "d" "Py" "Pronto" {
            properties {
                "codigo" "src/"
            }
        }
        compA = component "A" "d" "Py" "Pronto" {
            properties {
                "status" "Pronto"
                "codigo" "src/a.py, b.py (principal), src/pac/"
            }
        }
        compB = component "B" "d" "Py" "Pronto" {
            properties {
                "codigo" "src/par/x.py; tools/r*.sh"
            }
        }
        compFalta = component "F" "d" "Py" "Pronto" {
            properties {
                "codigo" "src/falta.py"
            }
        }
        compFuturo = component "G" "d" "Py" "Planejado" {
            properties {
                "status" "Planejado"
                "codigo" "src/futuro.py"
            }
        }
        compRamo = component "H" "d" "Py" "Pronto" {
            properties {
                "ramo" "outro"
                "codigo" "src/ramo.py, lib/*.js"
            }
        }
        compGlob = component "I" "d" "Py" "Pronto" {
            properties {
                "codigo" "tools/nada-*.sh"
            }
        }
    }
}
""", encoding="utf-8")
    spec = importlib.util.spec_from_file_location("cobertura_instanciada", repo / "tests" / "test_arquitetura_cobertura.py")
    teste = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(teste)
    pares = teste.caminhos_dos_componentes()
    do_teste = [a for a in teste.alvos() if a not in teste.EXCECOES and teste.quem_cobre(a, pares) is None]
    assert do_teste, "a fixture precisa ter módulos fora do modelo"
    assert "src/pac/" not in do_teste and "src/c.py" in do_teste and "src/solta/" in do_teste
    assert arq_comum.fora_do_modelo(arq, repo) == do_teste
    assert arq_comum.modulos_do_repo(arq, repo) == teste.alvos()
    with pytest.raises(AssertionError) as e:
        teste.test_caminhos_citados_existem()
    do_teste_q = [linha.strip() for linha in str(e.value).splitlines()[1:]]
    assert do_teste_q and "compFalta: src/falta.py" in do_teste_q
    assert arq_comum.caminhos_quebrados(arq, repo) == do_teste_q


# ------------------------------------------------------------------------------------------------ gancho do git

def _carregar_gancho():
    spec = importlib.util.spec_from_file_location("lodemap_gancho_decidir_t", SCRIPTS / "lodemap_gancho.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _isolar_gancho(m, monkeypatch, arq: Path) -> list:
    smap = arq / ".lodemap"
    monkeypatch.setattr(m, "ARQ", arq)
    monkeypatch.setattr(m, "SMAP", smap)
    monkeypatch.setattr(m, "LOG", smap / "ultimo-atualizar.log")
    chamadas: list = []
    monkeypatch.setattr(m, "disparar", lambda *a, **k: chamadas.append(a))
    return chamadas


def test_gancho_post_commit_so_dispara_na_cadencia(tmp_path, monkeypatch):
    repo, arq = _projeto(tmp_path, {"commits_para_regenerar": 2})
    m = _carregar_gancho()
    chamadas = _isolar_gancho(m, monkeypatch, arq)
    (repo / "src" / "a.py").write_text("x = 2\n", encoding="utf-8")
    _commitar(repo)
    assert m.main(["post-commit"]) == 0
    assert chamadas == []
    log = (arq / ".lodemap" / "ultimo-atualizar.log").read_text(encoding="utf-8")
    assert "não regenerei" in log and "1 commit(s) desde a última geração; regenera em 2" in log
    (repo / "src" / "a.py").write_text("x = 3\n", encoding="utf-8")
    _commitar(repo)
    assert m.main(["post-commit"]) == 0
    assert len(chamadas) == 1 and chamadas[0][0].startswith("post-commit ")


def test_gancho_post_commit_que_toca_o_modelo_dispara_na_hora(tmp_path, monkeypatch):
    repo, arq = _projeto(tmp_path)
    m = _carregar_gancho()
    chamadas = _isolar_gancho(m, monkeypatch, arq)
    dsl = arq / "model" / "componentes.dsl"
    dsl.write_text("// ajuste\n" + dsl.read_text(encoding="utf-8"), encoding="utf-8")
    _commitar(repo)
    assert m.main(["post-commit"]) == 0 and len(chamadas) == 1


def test_gancho_post_commit_com_modulo_novo_nao_dispara_e_nunca_chama_modelo(tmp_path, monkeypatch):
    repo, arq = _projeto(tmp_path)
    m = _carregar_gancho()
    chamadas = _isolar_gancho(m, monkeypatch, arq)
    _novo_modulo(repo, "c.py")
    _commitar(repo)
    assert m.main(["post-commit"]) == 0 and chamadas == []
    assert "modelar" in (arq / ".lodemap" / "ultimo-atualizar.log").read_text(encoding="utf-8")


def test_gancho_post_merge_nao_muda(tmp_path, monkeypatch):
    repo, arq = _projeto(tmp_path)
    m = _carregar_gancho()
    chamadas = _isolar_gancho(m, monkeypatch, arq)
    (repo / "src" / "a.py").write_text("x = 2\n", encoding="utf-8")
    _commitar(repo)
    assert m.main(["post-merge"]) == 0 and len(chamadas) == 1, "o post-merge segue disparando como antes"


def test_gancho_nunca_derruba_o_git_se_a_decisao_falhar(tmp_path, monkeypatch):
    repo, arq = _projeto(tmp_path)
    m = _carregar_gancho()
    chamadas = _isolar_gancho(m, monkeypatch, arq)

    def quebrada(*a, **k):
        raise RuntimeError("decisão quebrada")

    monkeypatch.setattr(dec, "decidir", quebrada)
    (repo / "src" / "a.py").write_text("x = 2\n", encoding="utf-8")
    _commitar(repo)
    assert m.main(["post-commit"]) == 0 and chamadas == []
    assert "gancho falhou" in (arq / ".lodemap" / "ultimo-atualizar.log").read_text(encoding="utf-8")


# ------------------------------------------------------------------------------------------------ esqueleto.py pendencias

def _foto(raiz: Path) -> dict:
    return {p.relative_to(raiz).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(raiz.rglob("*")) if p.is_file() and ".git" not in p.relative_to(raiz).parts}


def _pendencias(arq: Path) -> subprocess.CompletedProcess:
    env = {**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}
    return subprocess.run([sys.executable, str(RAIZ / "scripts" / "esqueleto.py"), "pendencias", "--arq", str(arq),
                           "--fonte", "ast"], capture_output=True, text=True, encoding="utf-8", env=env)


def test_esqueleto_pendencias_nao_grava_nada_e_avisa_quando_nao_ha_decisoes(tmp_path):
    import esqueleto
    r = tmp_path / "amostra"
    (r / "app").mkdir(parents=True)
    (r / "app" / "api.py").write_text('"""Rotas."""\nfrom app import regras\n', encoding="utf-8")
    (r / "app" / "regras.py").write_text('"""Regras."""\n\n\ndef calcular():\n    return 1\n', encoding="utf-8")
    _git(r, "init", "-q")
    _commitar(r, "inicio")
    novo = subprocess.run([sys.executable, str(RAIZ / "scripts" / "novo_mapa.py"), "--repo", str(r), "--projeto", "Amostra"],
                          capture_output=True, text=True, encoding="utf-8")
    assert novo.returncode == 0, novo.stdout + novo.stderr
    arq = r / "docs" / "architecture" / "structurizr"
    antes = _foto(r)
    res = _pendencias(arq)
    assert res.returncode == 0, res.stderr
    j = json.loads(res.stdout)
    assert set(j) == {"componentes_novos", "componentes_revisar", "relacoes_novas", "removidos", "sem_decisoes"}
    assert j["sem_decisoes"] is True and set(j["componentes_novos"]) == {"app/api.py", "app/regras.py"}
    assert _foto(r) == antes, "pendencias não pode escrever nada"
    assert not esqueleto.caminho_decisoes(arq).exists()
    # com decisões gravadas pelo rascunho: sem o aviso, só o que mudou, e ainda sem escrever
    esqueleto.rascunho(r, arq, fonte="ast")
    # o que o rascunho deixou sem decidir continua na conta enquanto ninguém decide (pendência não some sozinha)
    j = json.loads(_pendencias(arq).stdout)
    assert set(j["componentes_novos"]) == {"app/api.py", "app/regras.py"}
    assert j["relacoes_novas"] == ["app/api.py -> app/regras.py"]
    # o modelador decide tudo: a partir daqui só o que mudar no código volta
    destino = esqueleto.caminho_decisoes(arq)
    dados = json.loads(destino.read_text(encoding="utf-8"))
    for c in dados["componentes"]:
        c.update(nome="Nome", descricao="Faz uma coisa concreta neste projeto de amostra.", container="app", status="Pronto")
    for rel in dados["relacoes"]:
        rel.update(verbo="usa", manter=True)
    destino.write_text(json.dumps(dados, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    (r / "app" / "novo.py").write_text("from app import api\n", encoding="utf-8")
    antes = _foto(r)
    j = json.loads(_pendencias(arq).stdout)
    assert "sem_decisoes" not in j and j["componentes_novos"] == ["app/novo.py"]
    assert j["relacoes_novas"] == ["app/novo.py -> app/api.py"]
    assert _foto(r) == antes
    # o decidir lê esses números pela skill de verdade
    d = dec.decidir(arq, skill=RAIZ)
    assert d["divida"]["revisoes"] == 0 and d["divida"]["relacoes_novas"] == 1


def test_rascunho_sem_gravar_devolve_o_mesmo_calculo(tmp_path):
    import esqueleto
    r = tmp_path / "amostra"
    (r / "app").mkdir(parents=True)
    (r / "app" / "api.py").write_text('"""Rotas."""\n', encoding="utf-8")
    _git(r, "init", "-q")
    _commitar(r, "inicio")
    novo = subprocess.run([sys.executable, str(RAIZ / "scripts" / "novo_mapa.py"), "--repo", str(r), "--projeto", "Amostra"],
                          capture_output=True, text=True, encoding="utf-8")
    assert novo.returncode == 0, novo.stdout + novo.stderr
    arq = r / "docs" / "architecture" / "structurizr"
    seco = esqueleto.rascunho(r, arq, fonte="ast", gravar=False)
    assert not esqueleto.caminho_decisoes(arq).exists()
    gravado = esqueleto.rascunho(r, arq, fonte="ast")
    assert esqueleto.caminho_decisoes(arq).is_file()
    assert {k: v for k, v in seco.items() if k != "geradoEm"} == {k: v for k, v in gravado.items() if k != "geradoEm"}
