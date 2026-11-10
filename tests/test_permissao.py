"""Fluxo de permissão: plano com 0 tokens, consentimento por escopo, teto e revogação."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from lodemap import cli, permissao


def _repo(tmp_path: Path, n: int = 4) -> Path:
    r = tmp_path / "repo"
    for i in range(n):
        (r / "src").mkdir(parents=True, exist_ok=True)
        (r / "src" / f"m{i}.py").write_text('"""Módulo."""\n', encoding="utf-8")
    (r / "src" / "pacote").mkdir()
    return r


def test_plano_sem_mapa_conta_e_estima(tmp_path):
    r = _repo(tmp_path)
    antes = sorted(p.as_posix() for p in r.rglob("*"))
    p = permissao.plano(r)
    assert p["tokens_deste_plano"] == 0 and not p["mapa_existe"]
    assert p["modulos"]["modulos"] == 5
    e = p["estimativa"]
    assert e["sonnet_usd"] == round(2.84 * 5 / 63, 2)
    assert e["opus_usd_estimado"] > e["sonnet_usd"] > e["haiku_usd_projecao_nao_medida"]
    assert "estimativa" in e["tipo"] and "orquestrador" in e["tipo"] and e["checkpoint_por_commit_usd"] == 0.0
    caminhos = {a["caminho"] for a in p["arquivos"]}
    assert "docs/architecture/structurizr/workspace.dsl" in caminhos
    assert "docs/architecture/structurizr/lodemap.json" in caminhos
    assert sorted(p.as_posix() for p in r.rglob("*")) == antes, "plano não escreve"


def test_plano_sem_modulos_avisa(tmp_path):
    """Repositório sem módulos nos globs padrão não pode receber uma estimativa silenciosa."""
    r = tmp_path / "plano"
    (r / "docs").mkdir(parents=True)
    (r / "docs" / "guia.md").write_text("# Guia\n", encoding="utf-8")
    p = permissao.plano(r)
    assert p["modulos"]["modulos"] == 0
    assert p["aviso"] and "nenhum módulo" in p["aviso"]
    assert permissao.plano(_repo(tmp_path))["aviso"] is None
    # código fora das pastas convencionais: a raiz detectada é a do repositório, e o plano acha o módulo
    (r / "pkg").mkdir()
    (r / "pkg" / "a.py").write_text("x = 1\n", encoding="utf-8")
    p = permissao.plano(r)
    assert p["modulos"]["modulos"] == 1 and p["aviso"] is None


def test_plano_com_mapa_usa_inventario(tmp_path):
    r = _repo(tmp_path)
    arq = r / "docs" / "architecture" / "structurizr"
    (arq / "model").mkdir(parents=True)
    (arq / "lodemap.json").write_text(json.dumps({"raiz_codigo": "src", "modulos": ["src/*.py"]}), encoding="utf-8")
    p = permissao.plano(r)
    assert p["modulos"]["fonte"] == "inventario.py" and p["modulos"]["modulos"] == 4


def test_consentir_verificar_revogar(tmp_path, capsys):
    r = _repo(tmp_path)
    assert permissao.verificar(r, "gerar")[0] is False
    assert cli.main(["consentir", "--repo", str(r), "--escopos", "gerar,modelo", "--orcamento-mensal", "5"]) == 0
    c = json.loads((r / "docs/architecture/structurizr/.lodemap/consentimento.json").read_text(encoding="utf-8"))
    assert c["escopos"] == ["gerar", "modelo"] and c["orcamento_mensal_usd"] == 5 and c["data"]
    assert permissao.verificar(r, "gerar")[0]
    assert permissao.verificar(r, "modelo", 1.2)[0]
    assert permissao.verificar(r, "modelo", 7.0)[0] is False
    assert permissao.verificar(r, "synapse")[0] is False
    assert cli.main(["verificar", "--repo", str(r), "--escopo", "gancho"]) == 3
    assert cli.main(["revogar", "--repo", str(r), "--escopos", "modelo"]) == 0
    assert permissao.ler_consentimento(r)["escopos"] == ["gerar"]
    assert cli.main(["revogar", "--repo", str(r)]) == 0
    assert permissao.ler_consentimento(r) is None
    assert permissao.verificar(r, "gerar")[0] is False


def test_modelo_sem_teto_pede_confirmacao(tmp_path):
    r = _repo(tmp_path)
    permissao.consentir(r, ["modelo"])
    ok, msg = permissao.verificar(r, "modelo", 0.1)
    assert not ok and "confirme" in msg


def test_escopo_invalido(tmp_path):
    with pytest.raises(ValueError):
        permissao.consentir(_repo(tmp_path), ["tudo"])


def test_cli_plano(tmp_path, capsys):
    r = _repo(tmp_path)
    assert cli.main(["plano", "--repo", str(r)]) == 0
    out = capsys.readouterr().out
    assert "0 tokens" in out and "módulos: 5" in out and "estimativa" in out


@pytest.mark.parametrize("teto", [float("inf"), float("nan"), -1.0])
def test_teto_mensal_precisa_ser_numero_finito_e_nao_negativo(tmp_path, teto):
    with pytest.raises(ValueError, match="orçamento mensal"):
        permissao.consentir(tmp_path, ["modelo"], teto)
    assert not (tmp_path / "docs" / "architecture" / "structurizr" / ".lodemap" / "consentimento.json").exists()


def test_plano_e_consentir_recusam_repositorio_inexistente(tmp_path, capsys):
    nada = tmp_path / "nao-existe"
    for comando in (["plano", "--repo", str(nada)], ["consentir", "--repo", str(nada), "--escopos", "gerar"]):
        assert cli.main(comando) == 2
        assert "repositório não encontrado" in capsys.readouterr().out
    assert not nada.exists(), "nenhuma pasta é criada a partir do nada"


def test_revogar_sem_consentimento_nao_finge_que_revogou(tmp_path, capsys):
    r = _repo(tmp_path)
    assert cli.main(["revogar", "--repo", str(r)]) == 0
    saida = capsys.readouterr().out
    assert "nenhum consentimento" in saida and "revogado" not in saida


def test_plano_sem_mapa_em_repositorio_javascript_conta_os_arquivos(tmp_path):
    """Sem mapa, os globs padrão seguem a linguagem da raiz: um repositório JS não pode sair com 0 ou 2 módulos."""
    repo = tmp_path / "js"
    for rel in ("lib/a.js", "lib/core/b.js", "lib/core/c.js", "lib/helpers/d.mjs", "lib/node_modules/x/e.js"):
        f = repo / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text("export default 1\n", encoding="utf-8")
    m = permissao.contar_modulos(repo)
    assert m["globs"] == ["lib/**/*.js", "lib/**/*.mjs"]
    assert m["modulos"] == 4


def test_globs_padrao_python_continua_como_era(tmp_path):
    import novo_mapa
    repo = tmp_path / "py"
    (repo / "src" / "pacote").mkdir(parents=True)
    (repo / "src" / "a.py").write_text("x = 1\n", encoding="utf-8")
    (repo / "src" / "util.js").write_text("1\n", encoding="utf-8")
    assert novo_mapa.globs_padrao(repo, "src") == ["src/*.py", "src/*/"]
    assert novo_mapa.globs_padrao(repo, "nao_existe") == ["nao_existe/*.py", "nao_existe/*/"]

