"""Esqueleto do modelo (scripts/esqueleto.py): rascunho com 0 tokens, decisões em JSON, DSL que passa no gate."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from lodemap import RAIZ

sys.path.insert(0, str(RAIZ / "scripts"))
import esqueleto  # noqa: E402


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "-C", str(repo), *args],
                   check=True, capture_output=True)


@pytest.fixture()
def projeto(tmp_path):
    r = tmp_path / "amostra"
    (r / "app" / "dados").mkdir(parents=True)
    (r / "app" / "api.py").write_text('"""Rotas HTTP da amostra."""\nfrom app import regras\n\n\ndef rota():\n'
                                      '    return regras.calcular()\n', encoding="utf-8")
    (r / "app" / "regras.py").write_text('"""Regras de negócio."""\nfrom app.dados import repo\n\n\ndef calcular():\n'
                                         '    return repo.ler()\n', encoding="utf-8")
    (r / "app" / "dados" / "__init__.py").write_text("", encoding="utf-8")
    (r / "app" / "dados" / "repo.py").write_text("def ler():\n    return 1\n", encoding="utf-8")
    _git(r, "init", "-q")
    _git(r, "add", "-A")
    _git(r, "commit", "-q", "-m", "inicio")
    novo = subprocess.run([sys.executable, str(RAIZ / "scripts" / "novo_mapa.py"), "--repo", str(r),
                           "--projeto", "Amostra"], capture_output=True, text=True, encoding="utf-8")
    assert novo.returncode == 0, novo.stdout + novo.stderr
    return r


def _arq(r: Path) -> Path:
    return r / "docs" / "architecture" / "structurizr"


def _preencher(d: dict) -> dict:
    d["containers"] = [{"id": "app", "nome": "Aplicação", "descricao": "Processo da amostra.", "tecnologia": "Python",
                        "status": "Pronto", "codigo": "app/"}]
    d["areas"] = {"AreaNucleo": "Núcleo", "AreaDados": "Dados"}
    for c in d["componentes"]:
        c.update(nome=c["modulo"], descricao=c["dica"] or "Acesso aos dados.", container="app",
                 area="AreaDados" if "dados" in c["modulo"] else "AreaNucleo", status="Pronto")
    for rel in d["relacoes"]:
        rel.update(manter=True, verbo="Chama")
    return d


def test_rascunho_sugere_um_componente_por_modulo_e_as_relacoes_do_codigo(projeto):
    d = esqueleto.rascunho(projeto, _arq(projeto), fonte="ast")
    modulos = {c["modulo"] for c in d["componentes"]}
    assert modulos == {"app/api.py", "app/regras.py", "app/dados/"}
    pares = {(r["de"], r["para"]) for r in d["relacoes"]}
    assert pares == {("app/api.py", "app/regras.py"), ("app/regras.py", "app/dados/")}
    api = next(c for c in d["componentes"] if c["modulo"] == "app/api.py")
    assert api["dica"] == "Rotas HTTP da amostra." and api["nome"] == "" and api["status"] == ""
    assert d["pendentes"]["componentes_novos"] and esqueleto.caminho_decisoes(_arq(projeto)).is_file()


def test_modulo_que_o_inventario_nao_le_entra_no_rascunho(projeto):
    """Um .sh casado pelos globs precisa de componente (o gate cobra) mesmo sem o ast ler o arquivo."""
    arq = _arq(projeto)
    (projeto / "ops").mkdir()
    (projeto / "ops" / "subir.sh").write_text("#!/bin/sh\necho ok\n", encoding="utf-8")
    cfg = json.loads((arq / "lodemap.json").read_text(encoding="utf-8"))
    cfg["modulos"].append("ops/*.sh")
    (arq / "lodemap.json").write_text(json.dumps(cfg), encoding="utf-8")
    d = esqueleto.rascunho(projeto, arq, fonte="ast")
    sh = next(c for c in d["componentes"] if c["modulo"] == "ops/subir.sh")
    assert sh["linguagem"] == "Bash" and sh["linhas"] == 3 and sh["lido_pelo_inventario"] is False


def test_renderizar_recusa_decisoes_incompletas(projeto):
    esqueleto.rascunho(projeto, _arq(projeto), fonte="ast")
    with pytest.raises(ValueError, match="decisões incompletas") as e:
        esqueleto.renderizar(_arq(projeto))
    assert "falta nome" in str(e.value) and "decida manter" in str(e.value)


def test_dsl_renderizado_passa_no_gate_de_cobertura(projeto):
    arq = _arq(projeto)
    d = _preencher(esqueleto.rascunho(projeto, arq, fonte="ast"))
    esqueleto.caminho_decisoes(arq).write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    res = esqueleto.renderizar(arq)
    assert res["componentes"] == 3 and res["relacoes"] == 2
    comps = (arq / "model" / "componentes-app.dsl").read_text(encoding="utf-8")
    assert 'group "Núcleo"' in comps and '"codigo" "app/dados/"' in comps and "Troque pelo" not in comps
    assert "!include relacoes-componentes.dsl" in (arq / "model" / "relacoes.dsl").read_text(encoding="utf-8")
    assert any("appEntrada" in a for a in res["avisos"]), "as setas de exemplo do template precisam ser apontadas"
    gate = subprocess.run([sys.executable, "-m", "pytest", "tests/test_arquitetura_cobertura.py", "-q",
                           "-p", "no:cacheprovider", "--basetemp", str(projeto / ".pyt")],
                          cwd=projeto, capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert gate.returncode == 0, gate.stdout[-2000:]


def test_status_vira_rotulo_na_propriedade_e_tag_sem_espaco(projeto):
    """O explorador conta status pelo rótulo ("Em andamento"); a tag do estilo é "EmAndamento"."""
    arq = _arq(projeto)
    d = _preencher(esqueleto.rascunho(projeto, arq, fonte="ast"))
    d["componentes"][0]["status"] = "EmAndamento"
    esqueleto.caminho_decisoes(arq).write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    esqueleto.renderizar(arq)
    comps = (arq / "model" / "componentes-app.dsl").read_text(encoding="utf-8")
    assert '"status" "Em andamento"' in comps and '"EmAndamento,' in comps
    sys.path.insert(0, str(arq / "scripts"))
    import arq_comum  # noqa: PLC0415
    assert arq_comum.status_de({"props": {"status": "ForaDoFoco"}, "tags": []}) == "Fora do foco"


def test_fundir_junta_modulos_num_componente_e_tira_o_laco(projeto):
    arq = _arq(projeto)
    d = _preencher(esqueleto.rascunho(projeto, arq, fonte="ast"))
    regras = next(c for c in d["componentes"] if c["modulo"] == "app/regras.py")
    api = next(c for c in d["componentes"] if c["modulo"] == "app/api.py")
    for k in ("nome", "descricao", "container", "area", "status"):
        regras[k] = ""
    regras["fundir_em"] = api["id"]
    esqueleto.caminho_decisoes(arq).write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    res = esqueleto.renderizar(arq)
    assert res["componentes"] == 2 and res["relacoes"] == 1, "api->regras virou laço e saiu"
    comps = (arq / "model" / "componentes-app.dsl").read_text(encoding="utf-8")
    assert '"codigo" "app/api.py, app/regras.py"' in comps
    regras["fundir_em"] = "naoExiste"
    esqueleto.caminho_decisoes(arq).write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(ValueError, match="fundir_em"):
        esqueleto.renderizar(arq)


def test_rascunho_de_novo_preserva_decisoes_e_aponta_so_o_que_mudou(projeto):
    arq = _arq(projeto)
    d = _preencher(esqueleto.rascunho(projeto, arq, fonte="ast"))
    esqueleto.caminho_decisoes(arq).write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    (projeto / "app" / "regras.py").unlink()
    (projeto / "app" / "cli.py").write_text("from app import api\n\napi.rota()\n", encoding="utf-8")
    d2 = esqueleto.rascunho(projeto, arq, fonte="ast")
    api = next(c for c in d2["componentes"] if c["modulo"] == "app/api.py")
    assert api["nome"] == "app/api.py" and api["status"] == "Pronto", "decisão antiga preservada"
    assert d2["pendentes"]["componentes_novos"] == ["app/cli.py"]
    assert d2["pendentes"]["relacoes_novas"] == ["app/cli.py -> app/api.py"]
    assert d2["removidos"] == ["app/regras.py"]
    assert d2["containers"] and d2["areas"], "containers e áreas sobrevivem ao rascunho"


def test_visoes_estaticas_saem_do_json_e_o_exemplo_do_template_vira_include(projeto):
    """Contexto, containers, componentes e status por regra; o modelador fica só com os fluxos."""
    arq = _arq(projeto)
    d = _preencher(esqueleto.rascunho(projeto, arq, fonte="ast"))
    d["componentes"][0]["status"] = "Planejado"
    esqueleto.caminho_decisoes(arq).write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    res = esqueleto.renderizar(arq)
    assert "views/visoes-geradas.dsl" in res["escritos"]
    geradas = (arq / "views" / "visoes-geradas.dsl").read_text(encoding="utf-8")
    for chave in ('"Contexto"', '"Containers"', '"Componentes-app"', '"Status-app-Pronto"', '"Status-app-Planejado"'):
        assert chave in geradas, chave
    assert "Area-app-" not in geradas, "3 componentes: a visão do container inteiro já se lê"
    manual = (arq / "views" / "visoes.dsl").read_text(encoding="utf-8")
    assert "!include visoes-geradas.dsl" in manual and "Fluxo-principal" not in manual


def test_visao_por_area_so_com_container_grande_e_titulos_no_idioma(tmp_path):
    comps = [{"status": "Pronto"}] * esqueleto.MIN_COMPONENTES_POR_AREA
    por_cont = {"app": {"AreaNucleo": comps[:6], "AreaDados": comps[6:]}}
    d = {"containers": [{"id": "app", "nome": "App"}], "areas": {"AreaNucleo": "Core", "AreaDados": "Data"}}
    avisos = []
    esqueleto._renderizar_visoes(tmp_path, d, por_cont, "en", avisos)
    txt = (tmp_path / "views" / "visoes-geradas.dsl").read_text(encoding="utf-8")
    assert '"Area-app-Nucleo"' in txt and '"Area-app-Dados"' in txt
    assert 'include "element.tag==AreaNucleo"' in txt and 'title "App: components"' in txt
    assert "Status-app-" not in txt, "um status só: filtro não acrescenta nada"
    assert not avisos


def test_visoes_escritas_a_mao_nao_sao_sobrescritas(tmp_path):
    (tmp_path / "views").mkdir()
    manual = tmp_path / "views" / "visoes.dsl"
    manual.write_text('dynamic sistema "Meu-fluxo" { }\n', encoding="utf-8")
    avisos = []
    d = {"containers": [{"id": "app", "nome": "App"}], "areas": {"AreaNucleo": "N"}}
    esqueleto._renderizar_visoes(tmp_path, d, {"app": {"AreaNucleo": [{"status": "Pronto"}]}}, "pt", avisos)
    assert manual.read_text(encoding="utf-8") == 'dynamic sistema "Meu-fluxo" { }\n'
    assert any("escrito à mão" in a for a in avisos)


def test_gate_de_qualidade_aceita_status_em_ingles():
    sys.path.insert(0, str(RAIZ / "scripts"))
    import qualidade  # noqa: PLC0415
    assert qualidade.STATUS_EN["done"] == "Pronto" and qualidade.STATUS_EN["in progress"] == "EmAndamento"


# ---------------------------------------------------------------- pendências que sobrevivem a um segundo rascunho

def _gravar(projeto, d):
    esqueleto.caminho_decisoes(_arq(projeto)).write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")


def test_rascunho_repetido_nao_apaga_o_que_ainda_falta_decidir(projeto):
    """Achado ao mapear um repositório Go: o segundo rascunho zerava `relacoes_novas` com 31 relações sem decisão."""
    arq = _arq(projeto)
    d1 = esqueleto.rascunho(projeto, arq, fonte="ast")
    assert len(d1["pendentes"]["relacoes_novas"]) == 2 and len(d1["pendentes"]["componentes_novos"]) == 3
    d2 = esqueleto.rascunho(projeto, arq, fonte="ast")
    assert d2["pendentes"]["relacoes_novas"] == d1["pendentes"]["relacoes_novas"], "sem decisão continua pendente"
    assert d2["pendentes"]["componentes_novos"] == d1["pendentes"]["componentes_novos"]
    assert len(d2["pendentes"]["componentes_sem_container_ou_status"]) == 3


def test_revisao_pendente_sobrevive_ao_segundo_rascunho_e_some_no_renderizar(projeto):
    arq = _arq(projeto)
    _gravar(projeto, _preencher(esqueleto.rascunho(projeto, arq, fonte="ast")))
    esqueleto.renderizar(arq)
    assert not any(esqueleto.rascunho(projeto, arq, fonte="ast")["pendentes"].values()), "mapa em dia: nada pendente"
    (projeto / "app" / "api.py").write_text('"""Rotas HTTP da amostra."""\nfrom app import regras\n\n\ndef rota():\n'
                                            '    return regras.calcular()\n\n\ndef saude():\n    return "ok"\n',
                                            encoding="utf-8")
    assert esqueleto.rascunho(projeto, arq, fonte="ast")["pendentes"]["componentes_revisar"] == ["app/api.py"]
    # a digital nova já foi gravada; sem guardar a pendência, este segundo rascunho diria que não há nada a revisar
    assert esqueleto.rascunho(projeto, arq, fonte="ast")["pendentes"]["componentes_revisar"] == ["app/api.py"]
    assert esqueleto.rascunho(projeto, arq, fonte="ast", gravar=False)["pendentes"]["componentes_revisar"] == ["app/api.py"]
    esqueleto.renderizar(arq)  # as decisões foram aceitas: a pendência de modelo acaba aqui
    gravado = json.loads(esqueleto.caminho_decisoes(arq).read_text(encoding="utf-8"))
    assert gravado["pendentes"]["componentes_revisar"] == []
    assert esqueleto.rascunho(projeto, arq, fonte="ast")["pendentes"]["componentes_revisar"] == []


def test_sugestao_nunca_decidida_some_quando_o_codigo_deixa_de_mostrar(projeto):
    arq = _arq(projeto)
    d = esqueleto.rascunho(projeto, arq, fonte="ast")
    assert ("app/api.py", "app/regras.py") in {(r["de"], r["para"]) for r in d["relacoes"]}
    (projeto / "app" / "api.py").write_text('"""Rotas HTTP da amostra."""\n\n\ndef rota():\n    return 1\n', encoding="utf-8")
    d2 = esqueleto.rascunho(projeto, arq, fonte="ast")
    assert ("app/api.py", "app/regras.py") not in {(r["de"], r["para"]) for r in d2["relacoes"]}, \
        "sugestão sem decisão não fica para trás como 'sumiu do código'"


def test_relacao_decidida_que_sumiu_do_codigo_continua_marcada(projeto):
    arq = _arq(projeto)
    _gravar(projeto, _preencher(esqueleto.rascunho(projeto, arq, fonte="ast")))
    (projeto / "app" / "api.py").write_text('"""Rotas HTTP da amostra."""\n\n\ndef rota():\n    return 1\n', encoding="utf-8")
    d2 = esqueleto.rascunho(projeto, arq, fonte="ast")
    r = next(r for r in d2["relacoes"] if (r["de"], r["para"]) == ("app/api.py", "app/regras.py"))
    assert r["sumiu_do_codigo"] is True and r["manter"] is True and r["arestas"] == 0
