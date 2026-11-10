"""Idioma do explorador: o gerador grava `idioma` no dados.js; o dicionário pt/en da página é simétrico e o JS compila."""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys

import pytest

from lodemap import RAIZ

ESTRUTURIZR = RAIZ / "templates" / "structurizr"
HTML = ESTRUTURIZR / "explorador" / "index.html"


def _gerar(tmp_path, idioma):
    cfg = {"projeto": "Amostra"}
    if idioma:
        cfg["idioma"] = idioma
    (tmp_path / "lodemap.json").write_text(json.dumps(cfg), encoding="utf-8")
    (tmp_path / "ws.json").write_text('{"name": "Amostra", "model": {}, "views": {}}', encoding="utf-8")
    env = {k: v for k, v in os.environ.items() if k != "LODEMAP_IDIOMA"}
    r = subprocess.run([sys.executable, str(ESTRUTURIZR / "scripts" / "gerar_explorador.py"), str(tmp_path / "ws.json"),
                        str(tmp_path / "explorador")], capture_output=True, text=True, encoding="utf-8", env=env)
    assert r.returncode == 0, r.stdout + r.stderr
    js = (tmp_path / "explorador" / "dados.js").read_text(encoding="utf-8")
    return json.loads(re.search(r"window\.ARQ = (\{.*\});", js, re.S).group(1))


@pytest.mark.parametrize("idioma,esperado", [(None, "pt"), ("pt", "pt"), ("en", "en")])
def test_dados_js_grava_o_idioma(tmp_path, idioma, esperado):
    assert _gerar(tmp_path, idioma)["idioma"] == esperado


def _scripts():
    return re.findall(r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>", HTML.read_text(encoding="utf-8"), re.S)


@pytest.mark.skipif(shutil.which("node") is None, reason="node não instalado")
def test_js_do_explorador_tem_sintaxe_valida(tmp_path):
    for i, trecho in enumerate(_scripts()):
        f = tmp_path / f"s{i}.js"
        f.write_text(trecho, encoding="utf-8")
        r = subprocess.run(["node", "--check", str(f)], capture_output=True, text=True)
        assert r.returncode == 0, r.stderr


@pytest.mark.skipif(shutil.which("node") is None, reason="node não instalado")
def test_dicionario_pt_en_tem_as_mesmas_chaves_e_formas(tmp_path):
    dic = next(s for s in _scripts() if "LODEMAP_I18N" in s and "const $ = " not in s)
    f = tmp_path / "dic.js"
    f.write_text("global.window = {};\n" + dic + "\nconst T = window.LODEMAP_I18N;\n"
                 "const forma = v => Array.isArray(v) ? 'array' : typeof v;\n"
                 "const d = Object.keys(T.pt).filter(k => !(k in T.en) || forma(T.pt[k]) !== forma(T.en[k]))"
                 ".concat(Object.keys(T.en).filter(k => !(k in T.pt)));\n"
                 "console.log(JSON.stringify({n: Object.keys(T.pt).length, d}));\n", encoding="utf-8")
    r = subprocess.run(["node", str(f)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    res = json.loads(r.stdout)
    assert res["d"] == [] and res["n"] > 150


def test_pagina_sem_integracao_de_notas_nem_dinheiro():
    texto = HTML.read_text(encoding="utf-8")
    assert not re.search("|".join(["obsid" + "ian", "vau" + "lt", "cof" + "re"]), texto, re.I)
    assert not re.search(r"\bUSD\b|US\$|R\$ ?\d", texto)
