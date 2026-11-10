"""Confere, lendo o código, se cada descrição escrita pela rota enxuta é verdadeira (juiz: Sonnet com Read/Grep/Glob).

Lê <copia>/<arq>/.lodemap/decisoes-modelo.json, julga em lotes os componentes descritos por `claude -p` e grava
<saida>.json com um veredito por componente: verdadeira, falsa (alguma afirmação não bate com o código) ou vaga
(verdadeira, mas sem nada específico do módulo). O juiz é outro modelo (Sonnet) que não o que escreveu (Haiku).

Só o CLI oficial do Claude Code, pela assinatura (nunca a API).
Uso: python julgar.py --copia F:/lodemap-desc/chi-base-1 --saida F:/lodemap-desc/chi-base-1.juiz [--lote 12]
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ARQ = "docs/architecture/structurizr"
SISTEMA = (
    "You are a strict reviewer of architecture documentation. For each item you get a source path in the repository "
    "in the current directory and a one-sentence description of that module. Open the source and decide:\n"
    "- \"falsa\" if any factual claim in the sentence is wrong or not supported by the code (wrong behaviour, a "
    "function, header, type or mechanism that is not there, a cause or purpose the code does not show);\n"
    "- \"vaga\" if everything is true but the sentence says nothing specific to this module;\n"
    "- \"verdadeira\" otherwise.\n"
    "Read the code; do not trust names. In motivo, say which claim is wrong and what the code does instead (or why it "
    "holds). In trecho, quote one short line of the code that settles it. Answer for every item, keeping the field i."
)
SCHEMA = {"type": "object", "properties": {"itens": {"type": "array", "items": {
    "type": "object", "properties": {"i": {"type": "integer"},
                                     "veredito": {"type": "string", "enum": ["verdadeira", "falsa", "vaga"]},
                                     "motivo": {"type": "string"}, "trecho": {"type": "string"}},
    "required": ["i", "veredito", "motivo", "trecho"]}}}, "required": ["itens"]}


def julgar_lote(copia: Path, itens: list[tuple[int, dict]]) -> list[dict]:
    exe = shutil.which("claude") or "claude"
    cmd = [exe, "-p", "--model", "sonnet", "--effort", "medium", "--output-format", "json",
           "--no-session-persistence", "--tools", "Read,Grep,Glob", "--allowedTools", "Read,Grep,Glob",
           "--strict-mcp-config", "--setting-sources", "", "--append-system-prompt", SISTEMA,
           "--json-schema", json.dumps(SCHEMA)]
    pedido = "\n\n".join(f"### i={i}\nSource: {c['modulo']}\nDescription: {c['descricao']}" for i, c in itens)
    r = subprocess.run(cmd, input=pedido, capture_output=True, text=True, encoding="utf-8", cwd=str(copia), timeout=1800)
    d = json.loads(r.stdout)
    u = d.get("usage") or {}
    out = (d.get("structured_output") or {}).get("itens") or []
    tok = sum(u.get(k, 0) or 0 for k in ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens",
                                         "output_tokens"))
    return [dict(o, _tokens_lote=tok) for o in out]


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--copia", required=True)
    ap.add_argument("--saida", required=True)
    ap.add_argument("--lote", type=int, default=12)
    a = ap.parse_args()
    copia = Path(a.copia)
    d = json.loads((copia / ARQ / ".lodemap" / "decisoes-modelo.json").read_text(encoding="utf-8"))
    comps = [c for c in d["componentes"] if not c.get("fundir_em") and "claude -p" in (c.get("descrito_por") or "")]
    numerados = list(enumerate(comps))
    lotes = [numerados[k:k + a.lote] for k in range(0, len(numerados), a.lote)]
    with ThreadPoolExecutor(max_workers=3) as ex:
        res = [o for lote in ex.map(lambda l: julgar_lote(copia, l), lotes) for o in lote]
    por_i = {o["i"]: o for o in res}
    saida = []
    for i, c in numerados:
        o = por_i.get(i, {"veredito": "sem_resposta", "motivo": "", "trecho": ""})
        saida.append({"modulo": c["modulo"], "descricao": c["descricao"], "veredito": o["veredito"],
                      "motivo": o.get("motivo", ""), "trecho": o.get("trecho", "")})
    cont = {v: sum(1 for s in saida if s["veredito"] == v) for v in ("verdadeira", "falsa", "vaga", "sem_resposta")}
    Path(a.saida + ".json").write_text(json.dumps({"contagem": cont, "itens": saida}, ensure_ascii=False, indent=1),
                                       encoding="utf-8")
    print(json.dumps(cont))
    return 0


if __name__ == "__main__":
    sys.exit(main())
