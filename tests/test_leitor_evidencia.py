"""Evidência de ADR no leitor: só vira link o caminho que existe no repositório mapeado."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "templates" / "structurizr" / "scripts"))
import gerar_leitor as gl  # noqa: E402

REPO = "https://github.com/exemplo/mapa"
CFG = {"repo_github": REPO, "ramo": "main"}


def _git(pasta: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(pasta), *args], check=True, capture_output=True)


def test_sem_repositorio_conhecido_a_evidencia_fica_so_texto(tmp_path):
    m = gl._repo_mapeado(tmp_path, CFG)                     # pasta fora de um clone: nada se pode confirmar
    assert gl._evidencia("workspace.dsl", CFG, m) == {"texto": "workspace.dsl", "url": ""}
    assert gl._evidencia("scripts/atualizar.ps1", CFG, m)["url"] == ""


def test_caminho_do_inventario_vira_link_e_o_que_nao_esta_nele_nao(tmp_path):
    (tmp_path / "inventario.json").write_text(json.dumps({"modulos": [{"caminho": "lib/adapters/http.js"}]}), encoding="utf-8")
    m = gl._repo_mapeado(tmp_path, CFG)
    assert gl._evidencia("lib/adapters/http.js", CFG, m)["url"] == f"{REPO}/blob/main/lib/adapters/http.js"
    assert gl._evidencia("workspace.dsl", CFG, m)["url"] == ""
    assert gl._evidencia("lib/nao/existe.js", CFG, m)["url"] == ""


def test_clone_do_repositorio_mapeado_confere_o_arquivo_no_disco(tmp_path):
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "remote", "add", "origin", REPO + ".git")
    (tmp_path / "docs" / "arq").mkdir(parents=True)
    (tmp_path / "docs" / "arq" / "workspace.dsl").write_text("workspace {}", encoding="utf-8")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "a.py").write_text("x = 1\n", encoding="utf-8")
    m = gl._repo_mapeado(tmp_path / "docs" / "arq", CFG)
    assert gl._evidencia("src/a.py", CFG, m)["url"] == f"{REPO}/blob/main/src/a.py"                       # relativo à raiz
    assert gl._evidencia("workspace.dsl", CFG, m)["url"] == f"{REPO}/blob/main/docs/arq/workspace.dsl"    # relativo à pasta do mapa
    assert gl._evidencia("src/b.py", CFG, m)["url"] == ""                                                  # não existe
    assert gl._evidencia("src/a.py (linha 3)", CFG, m)["url"].endswith("src/a.py")


def test_clone_de_outro_repositorio_nao_gera_link(tmp_path):
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "remote", "add", "origin", "https://github.com/outro/repo.git")
    (tmp_path / "a.py").write_text("x = 1\n", encoding="utf-8")
    m = gl._repo_mapeado(tmp_path, CFG)
    assert gl._evidencia("a.py", CFG, m)["url"] == ""


def test_url_completa_continua_link_e_o_adr_do_modelo_nao_cita_arquivos_do_template():
    assert gl._evidencia("https://exemplo.org/x", CFG)["url"] == "https://exemplo.org/x"
    for adr in [*(ROOT / "templates" / "structurizr" / "adrs").glob("0001-*.md"),
                *(ROOT / "templates" / "i18n" / "en" / "structurizr" / "adrs").glob("0001-*.md"),
                *(ROOT / "exemplos" / "axios" / "adrs").glob("0001-*.md")]:
        meta, _ = gl.ler_frontmatter(adr.read_text(encoding="utf-8"))
        assert not meta.get("evidencia"), adr


def test_formas_do_remoto_que_apontam_para_o_mesmo_repositorio():
    # `url.insteadOf` (o checkout do CircleCI reescreve https://github.com para ssh://git@github.com) não pode
    # desligar os links: todas estas formas são o mesmo repositório.
    for u in ("https://github.com/exemplo/mapa.git", "git@github.com:exemplo/mapa.git",
              "ssh://git@github.com/exemplo/mapa.git", "ssh://git@github.com:22/Exemplo/Mapa/",
              "git+ssh://git@github.com/exemplo/mapa"):
        assert gl._norm_repo(u) == gl._norm_repo(REPO), u
    assert gl._norm_repo("ssh://git@github.com/outro/mapa.git") != gl._norm_repo(REPO)
