"""Idioma do leitor: o gerador do template grava `idioma` no dados.js e o JS da página tem sintaxe válida."""
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


def _gerar(tmp_path, idioma):
    cfg = {"projeto": "Amostra"}
    if idioma:
        cfg["idioma"] = idioma
    (tmp_path / "lodemap.json").write_text(json.dumps(cfg), encoding="utf-8")
    (tmp_path / "ws.json").write_text('{"name": "Amostra", "model": {}}', encoding="utf-8")
    env = {k: v for k, v in os.environ.items() if k != "LODEMAP_IDIOMA"}
    r = subprocess.run([sys.executable, str(ESTRUTURIZR / "scripts" / "gerar_leitor.py"), str(tmp_path / "ws.json"),
                        str(tmp_path / "leitor")], capture_output=True, text=True, encoding="utf-8", env=env)
    assert r.returncode == 0, r.stdout + r.stderr
    js = (tmp_path / "leitor" / "dados.js").read_text(encoding="utf-8")
    return json.loads(re.search(r"window\.LEITOR_DADOS = (\{.*\});", js, re.S).group(1))


@pytest.mark.parametrize("idioma,esperado", [(None, "pt"), ("pt", "pt"), ("en", "en")])
def test_dados_js_grava_o_idioma(tmp_path, idioma, esperado):
    assert _gerar(tmp_path, idioma)["idioma"] == esperado


@pytest.mark.skipif(shutil.which("node") is None, reason="node não instalado")
def test_js_do_leitor_tem_sintaxe_valida(tmp_path):
    html = (ESTRUTURIZR / "leitor" / "index.html").read_text(encoding="utf-8")
    for i, trecho in enumerate(re.findall(r"<script>(.*?)</script>", html, re.S)):
        f = tmp_path / f"s{i}.js"
        f.write_text(trecho, encoding="utf-8")
        r = subprocess.run(["node", "--check", str(f)], capture_output=True, text=True)
        assert r.returncode == 0, r.stderr
