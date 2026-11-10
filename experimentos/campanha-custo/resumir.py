"""Gera as tabelas do RESULTADOS.md a partir de resultados/*.json e resultados/*.internas.jsonl.

Uso: python resumir.py            (le a pasta `resultados/` ao lado deste arquivo)

Regras:
- custo da sessao = `total_cost_usd` do JSON da rodada (campo do proprio CLI, preco de lista equivalente da API);
- custo interno = soma de `total_cost_usd` das linhas de `<rodada>.internas.jsonl` (chamadas do descrever.py via shim);
- se nao existe `.internas.jsonl`, o custo interno e AUSENTE (marcado com `*`), nunca zero inventado;
- linhas `nao_json` do log interno tem custo desconhecido e sao contadas a parte.
"""
import json
import statistics as st
import sys
from pathlib import Path

PASTA = Path(__file__).resolve().parent / "resultados"


def carregar():
    rodadas = []
    for f in sorted(PASTA.glob("*.json")):
        if f.name.startswith("piloto-"):
            continue
        r = json.loads(f.read_text(encoding="utf-8"))
        log = PASTA / f"{f.stem}.internas.jsonl"
        linhas = [json.loads(x) for x in log.read_text(encoding="utf-8").splitlines() if x.strip()] if log.exists() else None
        r["_nome"] = f.stem
        r["_log"] = linhas
        r["_interno"] = None if linhas is None else round(sum(x.get("total_cost_usd") or 0 for x in linhas), 6)
        r["_sem_custo"] = 0 if linhas is None else sum(1 for x in linhas if x.get("total_cost_usd") is None)
        r["_total"] = round((r.get("total_cost_usd") or 0) + (r["_interno"] or 0), 6)
        rodadas.append(r)
    return rodadas


def cob(r):
    return "ok" if r.get("cobertura_ok") else "FALHA"


def main():
    rs = carregar()
    print(f"Rodadas lidas: {len(rs)}\n")
    print("| Rodada | Sessao (US$) | Interno (US$) | Chamadas internas | Total (US$) | Gate | Componentes | Cobertura | Tempo (s) |")
    print("|---|---|---|---|---|---|---|---|---|")
    for r in rs:
        i = "ausente*" if r["_interno"] is None else f"{r['_interno']:.4f}"
        n = "ausente*" if r["_log"] is None else str(len(r["_log"]))
        print(f"| {r['_nome']} | {r['total_cost_usd']:.4f} | {i} | {n} | {r['_total']:.4f}{'*' if r['_interno'] is None else ''} "
              f"| {r.get('qualidade_total')} | {r.get('componentes')} | {cob(r)} | {r['segundos']:.0f} |")
    print("\n`*` = sem registro das chamadas internas (descrever.py); o total e so a sessao, piso e nao valor medido.\n")

    print("| Repo x modelo | n | Total medio | Min | Max | So sessao medio | Min | Max | Rodadas c/ interno | Gate medio | Tempo medio (s) | Cobertura ok |")
    print("|---|---|---|---|---|---|---|---|---|---|---|---|")
    grupos = {}
    for r in rs:
        grupos.setdefault((r["repo"], r["pilha"]), []).append(r)
    for (repo, pilha), g in sorted(grupos.items()):
        tot = [x["_total"] for x in g]
        ses = [x["total_cost_usd"] for x in g]
        com = sum(1 for x in g if x["_interno"] is not None)
        gate = [x["qualidade_total"] for x in g if x.get("qualidade_total") is not None]
        print(f"| {repo} x {pilha} | {len(g)} | {st.mean(tot):.4f} | {min(tot):.4f} | {max(tot):.4f} | {st.mean(ses):.4f} | "
              f"{min(ses):.4f} | {max(ses):.4f} | {com}/{len(g)} | {st.mean(gate):.1f} | {st.mean(x['segundos'] for x in g):.0f} | "
              f"{sum(1 for x in g if x.get('cobertura_ok'))}/{len(g)} |")
    print("\nTotal medio mistura rodadas com e sem registro interno; a coluna 'So sessao' e comparavel entre todas.")

    print("\nPor modelo (todas as rodadas, so sessao):")
    for pilha in ("haiku", "sonnet"):
        ses = [x["total_cost_usd"] for x in rs if x["pilha"] == pilha]
        if ses:
            print(f"- {pilha}: n={len(ses)} media {st.mean(ses):.4f} min {min(ses):.4f} max {max(ses):.4f}")
    print("\nCobertura original (antes do remedir --noconftest) vs atual:")
    for r in rs:
        o = r.get("cobertura_original")
        if o and o.get("cobertura_ok") != r.get("cobertura_ok"):
            print(f"- {r['_nome']}: original={o.get('cobertura_ok')} atual={r.get('cobertura_ok')}")
    sem = [x["_nome"] for x in rs if x["_log"] is None]
    print(f"\nSem registro interno ({len(sem)}): {', '.join(sem) if sem else 'nenhuma'}")
    nj = [(x["_nome"], x["_sem_custo"]) for x in rs if x["_sem_custo"]]
    print(f"Chamadas internas sem custo legivel: {nj if nj else 'nenhuma'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
