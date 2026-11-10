"""Junta os vereditos do juiz de cada rodada numa tabela: frases falsas entre as que a rodada gravou.

Uma frase que a rota deixou para o modelador não foi gravada por ela; se o juiz a viu (porque a cópia trazia a frase
antiga do mapa), ela sai da conta. Uso: python resumir.py --pasta F:/lodemap-desc [rodada ...]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--pasta", required=True)
    ap.add_argument("rodadas", nargs="+")
    a = ap.parse_args()
    base = Path(a.pasta)
    linhas = []
    for r in a.rodadas:
        rel = json.loads((base / f"{r}.rel.json").read_text(encoding="utf-8"))
        juiz = json.loads((base / f"{r}.juiz.json").read_text(encoding="utf-8"))
        fora = {p["modulo"] for p in rel.get("para_modelador", [])}
        itens = [s for s in juiz["itens"] if s["modulo"] not in fora]
        falsas = [s["modulo"] for s in itens if s["veredito"] == "falsa"]
        vagas = [s["modulo"] for s in itens if s["veredito"] == "vaga"]
        conf = rel.get("conferencia") or {}
        linhas.append({"rodada": r, "gravadas": len(itens), "falsas": len(falsas), "vagas": len(vagas),
                       "para_modelador": len(fora), "reenviadas": rel.get("reenviados", 0),
                       "conferencia": {k: conf.get(k) for k in ("falsas", "corrigidas", "incertas")} if conf else None,
                       "tokens": rel.get("tokens", {}).get("total"), "modulos_falsos": falsas})
    print(json.dumps(linhas, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
