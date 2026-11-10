"""Avalia as execuções gravadas por rodar.py contra o gabarito e aplica as regras do PREREGISTRO.md.

Uso: python avaliar.py [--saida resultados]
Escreve <saida>/resumo.json e imprime a tabela por tarefa e o veredito de H1, H2 e H3.
"""
from __future__ import annotations

import argparse
import json
import statistics as st
import sys
from math import comb
from pathlib import Path

AQUI = Path(__file__).resolve().parent
TAREFAS = {t["id"]: t for t in json.loads((AQUI / "tarefas.json").read_text(encoding="utf-8"))["tarefas"]}


def _norm(p: str) -> str:
    p = p.strip().replace("\\", "/")
    while p.startswith("./"):
        p = p[2:]
    return p.lstrip("/")


def medir(bruto: dict) -> dict:
    t = TAREFAS[bruto["tarefa"]]
    r = {"tarefa": bruto["tarefa"], "braco": bruto["braco"], "rep": bruto["rep"], "seg": bruto["seg"], "ok": False}
    try:
        d = json.loads(bruto["stdout"])
    except (ValueError, TypeError):
        return r
    if d.get("is_error") or not isinstance(d.get("structured_output"), dict):
        return r
    u = d.get("usage") or {}
    arquivos = [_norm(x) for x in d["structured_output"].get("arquivos") or [] if isinstance(x, str)]
    deve, aceita = set(t["deve"]), set(t["aceita"])
    r.update(ok=True, arquivos=arquivos, turnos=d.get("num_turns"),
             recall=len(deve & set(arquivos)) / len(deve),
             errados=sorted(set(arquivos) - deve - aceita),
             tokens=sum(u.get(k, 0) or 0 for k in ("input_tokens", "cache_creation_input_tokens",
                                                   "cache_read_input_tokens", "output_tokens")),
             saida=u.get("output_tokens", 0) or 0)
    return r


def sinal(vitorias: int, n: int) -> float:
    """P(X >= vitorias) para X ~ Binomial(n, 0,5): teste do sinal unilateral."""
    return sum(comb(n, k) for k in range(vitorias, n + 1)) / 2 ** n if n else 1.0


def avaliar(saida: Path) -> dict:
    runs = [medir(json.loads(p.read_text(encoding="utf-8"))) for p in sorted((saida / "brutos").glob("*.json"))]
    falhas = [r for r in runs if not r["ok"]]
    por = {}
    for r in runs:
        if r["ok"]:
            por.setdefault((r["tarefa"], r["braco"]), []).append(r)
    linhas = []
    for tid, t in TAREFAS.items():
        a, b = por.get((tid, "A"), []), por.get((tid, "B"), [])
        if not a or not b:
            continue
        m = lambda xs, k: st.mean(x[k] for x in xs)  # noqa: E731
        linhas.append({"tarefa": tid, "tipo": t.get("tipo", "localizar"), "n": [len(a), len(b)],
                       "tokens": [round(m(a, "tokens")), round(m(b, "tokens"))],
                       "saida": [round(m(a, "saida")), round(m(b, "saida"))],
                       "turnos": [round(m(a, "turnos"), 1), round(m(b, "turnos"), 1)],
                       "seg": [round(m(a, "seg"), 1), round(m(b, "seg"), 1)],
                       "recall": [round(m(a, "recall"), 3), round(m(b, "recall"), 3)],
                       "errados": [round(st.mean(len(x["errados"]) for x in a), 2),
                                   round(st.mean(len(x["errados"]) for x in b), 2)]})
    n = len(linhas)
    menos_tokens = sum(1 for l in linhas if l["tokens"][0] < l["tokens"][1])
    razoes = [l["tokens"][0] / l["tokens"][1] for l in linhas if l["tokens"][1]]
    rec_a = st.mean(l["recall"][0] for l in linhas) if linhas else 0
    rec_b = st.mean(l["recall"][1] for l in linhas) if linhas else 0
    err_a = st.mean(l["errados"][0] for l in linhas) if linhas else 0
    err_b = st.mean(l["errados"][1] for l in linhas) if linhas else 0
    melhor = sum(1 for l in linhas if l["recall"][0] > l["recall"][1])
    pior = sum(1 for l in linhas if l["recall"][0] < l["recall"][1])
    sub = {}
    for tipo in sorted({l["tipo"] for l in linhas}):
        g = [l for l in linhas if l["tipo"] == tipo]
        sub[tipo] = {"tarefas": len(g),
                     "mediana_razao_tokens": round(st.median(l["tokens"][0] / l["tokens"][1] for l in g), 3),
                     "recall": [round(st.mean(l["recall"][0] for l in g), 3), round(st.mean(l["recall"][1] for l in g), 3)],
                     "errados": [round(st.mean(l["errados"][0] for l in g), 2), round(st.mean(l["errados"][1] for l in g), 2)]}
    return {
        "execucoes": len(runs), "falhas": [{k: f[k] for k in ("tarefa", "braco", "rep")} for f in falhas],
        "tarefas": n, "por_tarefa": linhas, "subgrupos": sub,
        "H1": {"tarefas_com_menos_tokens_em_A": menos_tokens, "p_sinal": round(sinal(menos_tokens, n), 4),
               "mediana_razao_tokens_A_sobre_B": round(st.median(razoes), 3) if razoes else None,
               "demonstrada": n == 16 and menos_tokens >= 12},
        "H2": {"recall_medio": [round(rec_a, 3), round(rec_b, 3)], "errados_medio": [round(err_a, 2), round(err_b, 2)],
               "demonstrada": rec_a >= rec_b - 0.05 and err_a <= err_b + 0.25},
        "H3": {"tarefas_A_melhor": melhor, "tarefas_A_pior": pior, "p_sinal": round(sinal(melhor, melhor + pior), 4),
               "demonstrada": melhor > pior and melhor >= 12},
    }


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--saida", default="resultados")
    a = ap.parse_args()
    saida = AQUI / a.saida
    res = avaliar(saida)
    (saida / "resumo.json").write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{'tarefa':6} {'tipo':9} {'tokens A':>9} {'tokens B':>9} {'A/B':>5} {'recall A':>8} {'recall B':>8} "
          f"{'err A':>5} {'err B':>5} {'turnos A/B':>10}")
    for l in res["por_tarefa"]:
        print(f"{l['tarefa']:6} {l['tipo']:9} {l['tokens'][0]:>9} {l['tokens'][1]:>9} "
              f"{l['tokens'][0] / l['tokens'][1]:>5.2f} {l['recall'][0]:>8.2f} {l['recall'][1]:>8.2f} "
              f"{l['errados'][0]:>5} {l['errados'][1]:>5} {l['turnos'][0]:>5}/{l['turnos'][1]}")
    for h in ("H1", "H2", "H3"):
        print(h, json.dumps(res[h], ensure_ascii=False))
    print("subgrupos", json.dumps(res["subgrupos"], ensure_ascii=False))
    if res["falhas"]:
        print("falhas", res["falhas"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
