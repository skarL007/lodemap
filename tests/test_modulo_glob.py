"""Arquivo -> módulo pelos globs do lodemap.json, com a semântica do Path.glob (e não a do fnmatch)."""
from __future__ import annotations

import json
import subprocess
import sys

import pytest

from lodemap import RAIZ

sys.path.insert(0, str(RAIZ / "scripts"))
import codegraph_ponte as cp  # noqa: E402
import esqueleto  # noqa: E402

from test_esqueleto import _arq, _git  # noqa: E402


@pytest.mark.parametrize("arquivo,globs,esperado", [
    ("lib/axios.js", ["lib/**/*.js"], "lib/axios.js"),           # ** casa zero pastas
    ("lib/core/Axios.js", ["lib/**/*.js"], "lib/core/Axios.js"),
    ("lib/a/b/c.js", ["lib/**/*.js"], "lib/a/b/c.js"),
    ("lib/a/b.ts", ["lib/**/*.js"], None),
    ("lib/a/b.js", ["lib/*.js"], None),                          # * não atravessa /
    ("lib/b.js", ["lib/*.js"], "lib/b.js"),
    ("outra/lib/b.js", ["lib/**/*.js"], None),
    ("app/dados/repo.py", ["app/*.py", "app/*/"], "app/dados/"),
])
def test_modulo_de_segue_o_path_glob(arquivo, globs, esperado):
    assert cp._modulo_de(arquivo, globs) == esperado


@pytest.fixture()
def projeto_js(tmp_path):
    r = tmp_path / "jsamostra"
    (r / "lib" / "core").mkdir(parents=True)
    (r / "lib" / "index.js").write_text("import util from './util.js';\nimport Nucleo from './core/Nucleo.js';\n"
                                        "export default new Nucleo(util);\n", encoding="utf-8")
    (r / "lib" / "util.js").write_text("export default {um: 1};\n", encoding="utf-8")
    (r / "lib" / "core" / "Nucleo.js").write_text("import util from '../util.js';\nexport default class Nucleo {}\n",
                                                  encoding="utf-8")
    _git(r, "init", "-q")
    _git(r, "add", "-A")
    _git(r, "commit", "-q", "-m", "inicio")
    novo = subprocess.run([sys.executable, str(RAIZ / "scripts" / "novo_mapa.py"), "--repo", str(r),
                           "--projeto", "JS"], capture_output=True, text=True, encoding="utf-8")
    assert novo.returncode == 0, novo.stdout + novo.stderr
    return r


def test_rascunho_js_ve_as_arestas_dos_arquivos_da_raiz_do_codigo(projeto_js):
    """Regressão: com `lib/**/*.js`, as arestas de e para `lib/index.js` e `lib/util.js` sumiam do rascunho."""
    cfg = json.loads((_arq(projeto_js) / "lodemap.json").read_text(encoding="utf-8"))
    assert cfg["modulos"] == ["lib/**/*.js"], "globs padrão de um repositório JS"
    d = esqueleto.rascunho(projeto_js, _arq(projeto_js), fonte="ast")
    pares = {(r["de"], r["para"]) for r in d["relacoes"]}
    assert pares == {("lib/index.js", "lib/util.js"), ("lib/index.js", "lib/core/Nucleo.js"),
                     ("lib/core/Nucleo.js", "lib/util.js")}


def test_relacao_manual_nao_vira_sumiu_do_codigo_e_perde_a_marca_quando_o_codigo_mostra(projeto_js):
    arq = _arq(projeto_js)
    d = esqueleto.rascunho(projeto_js, arq, fonte="ast")
    d["relacoes"].append({"de": "lib/util.js", "para": "lib/core/Nucleo.js", "verbo": "Configures", "manter": True,
                          "manual": True})
    for r in d["relacoes"]:
        if (r["de"], r["para"]) == ("lib/index.js", "lib/util.js"):
            r.update(manter=True, verbo="Reads", manual=True)  # marcada à mão, mas o código mostra
    (arq / ".lodemap" / "decisoes-modelo.json").write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    d2 = esqueleto.rascunho(projeto_js, arq, fonte="ast")
    por_par = {(r["de"], r["para"]): r for r in d2["relacoes"]}
    so_manual = por_par[("lib/util.js", "lib/core/Nucleo.js")]
    assert so_manual["manual"] is True and so_manual["sumiu_do_codigo"] is False and so_manual["arestas"] == 0
    mostrada = por_par[("lib/index.js", "lib/util.js")]
    assert "manual" not in mostrada and mostrada["arestas"] >= 1 and mostrada["verbo"] == "Reads"


@pytest.mark.parametrize("arquivo,globs,esperado", [
    ("lib/axios.js", ["lib/**/*.js"], "lib/axios.js"),
    ("lib/core/Axios.js", ["lib/**/*.js"], "lib/core/Axios.js"),
    ("lib/a/b/c.js", ["lib/**/*.js"], "lib/a/b/c.js"),
    ("lib/a/b.js", ["lib/*.js"], None),
    ("app/dados/repo.py", ["app/*.py", "app/*/"], "app/dados/"),
    ("app/solto.py", ["app/*.py", "app/*/"], "app/solto.py"),
])
def test_diff_do_projeto_usa_a_mesma_regra_de_glob(arquivo, globs, esperado):
    """O diff incremental (painel de mudanças e aviso de módulo sem componente) não via arquivo fora de 1 nível."""
    sys.path.insert(0, str(RAIZ / "templates" / "structurizr" / "scripts"))
    import lodemap_diff
    assert lodemap_diff.modulo_de(arquivo, globs) == esperado


def test_atualizar_fala_ingles_quando_o_mapa_e_em_ingles(tmp_path, capsys, monkeypatch):
    sys.path.insert(0, str(RAIZ / "templates" / "structurizr" / "scripts"))
    import atualizar
    monkeypatch.delenv("LODEMAP_IDIOMA", raising=False)
    (tmp_path / "lodemap.json").write_text('{"idioma": "en"}', encoding="utf-8")
    assert atualizar._idioma_en(tmp_path) is True and atualizar._idioma_en(tmp_path / "nada") is False
    assert atualizar._idioma_en(tmp_path, {"LODEMAP_IDIOMA": "pt"}) is False
    monkeypatch.setattr(atualizar, "_EN", True)
    atualizar.info("1/7 validando", "1/7 validating the model")
    atualizar.info("sem tradução")
    atualizar.aviso("falhou", "failed")
    s = capsys.readouterr()
    assert s.out.splitlines() == ["1/7 validating the model", "sem tradução"] and "WARNING: failed" in s.err

