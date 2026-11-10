"""Hook de aviso do Lodemap: uma linha, uma vez por repositório sem mapa."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import aviso_lodemap as aviso

RAIZ = Path(__file__).resolve().parents[1]


def _repo(tmp_path: Path, nome: str) -> Path:
    r = tmp_path / nome
    r.mkdir()
    subprocess.run(["git", "init", "-q", str(r)], check=True)
    return r


def test_aviso_dispara_uma_vez_so(home, tmp_path):
    r = _repo(tmp_path, "sem-mapa")
    cfg = home / ".config" / "lodemap"
    d = aviso.avaliar({"cwd": str(r), "source": "startup"}, cfg)
    linha = d["hookSpecificOutput"]["additionalContext"]
    assert "/lodemap plano" in linha and "\n" not in linha
    assert aviso.avaliar({"cwd": str(r), "source": "startup"}, cfg) is None
    assert aviso.avaliar({"cwd": str(r / "sub"), "source": "startup"}, cfg) is None
    assert len(json.loads((cfg / "avisos.json").read_text(encoding="utf-8"))) == 1


def test_aviso_nao_dispara_com_mapa_fora_do_git_ou_em_compact(home, tmp_path):
    cfg = home / ".config" / "lodemap"
    com = _repo(tmp_path, "com-mapa")
    arq = com / "docs" / "architecture" / "structurizr"
    arq.mkdir(parents=True)
    (arq / "lodemap.json").write_text("{}", encoding="utf-8")
    assert aviso.avaliar({"cwd": str(com), "source": "startup"}, cfg) is None
    fora = tmp_path / "nao-git"
    fora.mkdir()
    assert aviso.avaliar({"cwd": str(fora), "source": "startup"}, cfg) is None
    outro = _repo(tmp_path, "outro")
    assert aviso.avaliar({"cwd": str(outro), "source": "compact"}, cfg) is None
    assert not (cfg / "avisos.json").exists()


def test_aviso_por_processo(home, tmp_path):
    """O hook roda como script (stdin JSON -> stdout JSON), como o Claude Code chama."""
    import os
    import sys
    r = _repo(tmp_path, "proc")
    e = json.dumps({"cwd": str(r), "source": "startup"})
    cmd = [sys.executable, str(RAIZ / "hooks" / "aviso_lodemap.py")]
    p1 = subprocess.run(cmd, input=e, capture_output=True, text=True, env=os.environ.copy(), encoding="utf-8")
    p2 = subprocess.run(cmd, input=e, capture_output=True, text=True, env=os.environ.copy(), encoding="utf-8")
    assert p1.returncode == 0 and "lodemap plano" in p1.stdout
    assert p2.returncode == 0 and p2.stdout == ""
