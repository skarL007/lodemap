"""Hook SessionStart opcional (perfil padrão): aviso único por repositório sem mapa.

Num repositório git sem docs/architecture/structurizr/lodemap.json e ainda não avisado, injeta UMA linha sugerindo
`/lodemap plano` e grava em ~/.config/lodemap/avisos.json que já avisou. Nada é gerado e nenhum token é gasto além
dessa linha. Sessões retomadas ou compactadas não avisam.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from _comum import entrada, git, pasta_config, saida

ARQ = Path("docs") / "architecture" / "structurizr"
LINHA = ("[lodemap] Este repositório ainda não tem mapa de arquitetura. Se o dono quiser, rode `/lodemap plano` "
         "(0 tokens: módulos, custo e tempo estimados); nada é gerado sem o ok dele. Aviso único.")


def avaliar(e: dict, config: Path | None = None) -> dict | None:
    if e.get("source") not in (None, "", "startup", "clear"):
        return None
    topo = git(e.get("cwd"), "rev-parse", "--show-toplevel")
    if not topo:
        return None
    raiz = Path(topo)
    if (raiz / ARQ / "lodemap.json").is_file():
        return None
    arq = (config or pasta_config()) / "avisos.json"
    try:
        avisos = json.loads(arq.read_text(encoding="utf-8")) if arq.is_file() else {}
    except ValueError:
        avisos = {}
    chave = raiz.resolve().as_posix().lower()
    if chave in avisos:
        return None
    avisos[chave] = datetime.now().astimezone().isoformat(timespec="seconds")
    try:
        arq.parent.mkdir(parents=True, exist_ok=True)
        arq.write_text(json.dumps(avisos, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except OSError:
        return None
    return {"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": LINHA}}


if __name__ == "__main__":
    saida(avaliar(entrada()))
