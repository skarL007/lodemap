"""Rubrica objetiva e determinística da qualidade de um modelo C4 (lodemap).

Uso:
  python qualidade.py --arq <pasta structurizr> [--repo <raiz>] [--baseline <json>] [--min <total>|baseline]
                      [--listar-reprovados] [--fonte auto|codegraph|ast] [--db <codegraph.db>]
                      [--gravar-baseline <json>] [--sem-gate]

Lê o workspace.json (.structurizr/export/ ou ao lado do DSL) e dá uma nota de 0 a 100 por critério e uma total
ponderada. Sem LLM. O gate compara com references/baseline-qualidade.json (a linha de base: o primeiro mapa que a
skill gerou): o total pode ficar no máximo 10 pontos abaixo dela e nenhum critério abaixo de 70% do valor dela (critério "n/d" sai da conta nos dois
lados). Sai com 1 se reprovar. Com --listar-reprovados, devolve os componentes (e relações) que reprovam em
cada critério, para o lodemap-modelador corrigir só eles. Só usa a biblioteca padrão.

Critérios (peso entre parênteses; a justificativa está em references/gate-qualidade.md):
  descricao (14)  componentes com descrição de 40+ caracteres que não repete o nome
  codigo (12)     componentes cuja propriedade `codigo` aponta para caminhos que existem (Planejado e `ramo` ficam fora)
  observabilidade (5)   componentes com a propriedade `observabilidade`
  relacoes_media (6)    relações por componente, média; nota = média / 3 (teto 100)
  orfaos (6)      componentes com pelo menos uma relação
  relacoes_qualificadas (8)  relações com verbo (descrição) e tecnologia
  status (5)      componentes com uma tag de status válida e igual à propriedade `status`
  visoes_container (5)   containers com componentes que têm visão própria
  fluxos (5)      visões dinâmicas; nota = fluxos / 3 (teto 100)
  passos_fluxo (3)       passos médios por fluxo; nota = média / 6 (teto 100)
  agrupamento (4) componentes em algum grupo ou área
  cobertura (11)  módulos dos globs de `modulos` cobertos por algum `codigo`
  recall_relacoes (10)   pares componente->componente de confiança alta ou média no código (ast: todo import)
                         que estão no modelo (n/d sem CodeGraph nem ast útil)
  precisao_relacoes (6)  relações do modelo entre componentes de código que têm aresta real no código
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import codegraph_ponte as ponte  # noqa: E402
from lodemap.idioma import opcao, t, usar_mapa  # noqa: E402  (codegraph_ponte já pôs a raiz da skill no sys.path)

SKILL = Path(__file__).resolve().parent.parent
BASELINE_PADRAO = SKILL / "references" / "baseline-qualidade.json"
IGNORAR = {"__pycache__", "node_modules", ".git", ".venv", "dist", "build"}

PESOS = {
    "descricao": 14, "codigo": 12, "observabilidade": 5, "relacoes_media": 6, "orfaos": 6,
    "relacoes_qualificadas": 8, "status": 5, "visoes_container": 5, "fluxos": 5, "passos_fluxo": 3,
    "agrupamento": 4, "cobertura": 11, "recall_relacoes": 10, "precisao_relacoes": 6,
}
ALVO_RELACOES_POR_COMPONENTE = 3
ALVO_FLUXOS = 3
ALVO_PASSOS = 6
MIN_DESCRICAO = 40
FOLGA_TOTAL = 10
FRACAO_MINIMA = 0.70
# Critérios que contam no total mas não têm piso próprio. Observabilidade depende da natureza do projeto: uma
# biblioteca sem log nem métrica tira 0 com o modelo certo, e um piso ali só empurraria o modelador a inventar nome.
SEM_PISO = frozenset({"observabilidade"})
TAG_STATUS = re.compile(r"^(Pronto|EmAndamento|Aguardando\w*|Planejado|ForaDoFoco)$")
# Mapa em inglês: a propriedade traz o rótulo traduzido; a tag do estilo continua a chave em português.
STATUS_EN = {"done": "Pronto", "in progress": "EmAndamento", "waiting": "Aguardando", "planned": "Planejado",
             "out of focus": "ForaDoFoco"}


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower().replace("ã", "a").replace("á", "a").replace("ç", "c").replace("é", "e")
                  .replace("ê", "e").replace("í", "i").replace("ó", "o").replace("õ", "o").replace("ú", "u"))


def nota(frac: float) -> float:
    return round(100 * max(0.0, min(1.0, frac)), 1)


def razao(parte: int, total: int) -> float | None:
    return None if total == 0 else parte / total


# ------------------------------------------------------------------ cobertura (mesma regra do teste)

def _quem_cobre(alvo: str, pares: list[tuple[str, str]], raiz: str) -> str | None:
    for c, ident in pares:
        if c.rstrip("/") == raiz:
            continue
        if any(ch in c for ch in "*?["):
            if fnmatch.fnmatch(alvo, c):
                return ident
        elif c.endswith("/"):
            if alvo.startswith(c) or (alvo.endswith("/") and c.startswith(alvo)):
                return ident
        elif c == alvo or (alvo.endswith("/") and c.startswith(alvo)):
            return ident
    return None


def _alvos(repo: Path, globs: list[str], ignorar: list[str] | None = None) -> list[str]:
    out = set()
    for padrao in globs:
        pasta = padrao.endswith("/")
        for p in repo.glob(padrao.rstrip("/")):
            if any(parte in IGNORAR or parte.startswith(".") for parte in p.relative_to(repo).parts):
                continue
            if ponte._ignorado(p.relative_to(repo).as_posix(), ignorar):
                continue
            if pasta and p.is_dir():
                out.add(p.relative_to(repo).as_posix() + "/")
            elif not pasta and p.is_file():
                out.add(p.relative_to(repo).as_posix())
    return sorted(out)


def _existe(repo: Path, c: str) -> bool:
    return any(repo.glob(c)) if any(ch in c for ch in "*?[") else (repo / c.rstrip("/")).exists()


# ------------------------------------------------------------------ cálculo

def avaliar(arq: Path, repo: Path | None = None, fonte: str = "auto", db: Path | None = None,
            listar: bool = False) -> dict:
    arq = arq.resolve()
    repo = (repo or ponte.raiz_repo(arq)).resolve()
    ws_arq = ponte.achar_workspace(arq)
    if not ws_arq:
        raise SystemExit(t("qualidade: sem workspace.json (rode o atualizar.ps1 antes)",
                           "qualidade: no workspace.json (run atualizar.ps1 first)"))
    ws = json.loads(ws_arq.read_text(encoding="utf-8-sig"))
    cfg_arq = arq / "lodemap.json"
    cfg = json.loads(cfg_arq.read_text(encoding="utf-8-sig")) if cfg_arq.is_file() else {}
    comps = ponte.componentes(ws)
    n = len(comps)
    crit: dict[str, dict] = {}
    rep: dict[str, list] = {}

    def registrar(nome, frac, valor, detalhe, reprovados=None):
        if frac is None:
            crit[nome] = {"nota": None, "valor": None, "detalhe": detalhe or "n/d"}
        else:
            crit[nome] = {"nota": nota(frac), "valor": valor if valor is not None else round(frac, 4),
                          "detalhe": detalhe}
        if listar and reprovados:
            rep[nome] = reprovados

    # descrição
    ruins = [c["ident"] for c in comps
             if len(c["desc"].strip()) < MIN_DESCRICAO or _norm(c["desc"]) == _norm(c["nome"])]
    registrar("descricao", razao(n - len(ruins), n), None,
              t(f"{n - len(ruins)} de {n} com {MIN_DESCRICAO}+ caracteres",
                f"{n - len(ruins)} of {n} with {MIN_DESCRICAO}+ characters"), ruins)

    # código
    exempt, ruins, avaliados = 0, [], 0
    for c in comps:
        p = c["props"]
        if "Planejado" in c["tags"] or p.get("ramo"):
            exempt += 1
            continue
        avaliados += 1
        caminhos = ponte.caminhos_codigo(p.get("codigo", ""))
        if not caminhos or not all(_existe(repo, x) for x in caminhos):
            ruins.append(c["ident"])
    registrar("codigo", razao(avaliados - len(ruins), avaliados), None,
              t(f"{avaliados - len(ruins)} de {avaliados} com caminho existente ({exempt} Planejado/ramo fora)",
                f"{avaliados - len(ruins)} of {avaliados} with an existing path ({exempt} Planejado/ramo left out)"),
              ruins)

    # observabilidade
    ruins = [c["ident"] for c in comps if not c["props"].get("observabilidade", "").strip()]
    registrar("observabilidade", razao(n - len(ruins), n), None, t(f"{n - len(ruins)} de {n}", f"{n - len(ruins)} of {n}"),
              ruins)

    # O que o código mostra (pares de componentes com aresta): mede as relações e também diz o que NÃO é omissão
    # do modelo. Uma biblioteca de módulos independentes tem poucos pares; cobrar dela 3 relações por componente e
    # zero componente sem relação seria cobrar invenção.
    try:
        info = ponte.analisar(arq, repo, fonte, db)
    except SystemExit as e:
        info = None
        motivo = str(e)
    # Só vale quando a leitura achou pelo menos um par: com zero pares não dá para distinguir "código sem
    # ligação" de "linguagem que a fonte não lê", e a regra fixa continua.
    ve_codigo = bool(info and info["pares"])
    com_aresta = {x for par in info["pares"] for x in par} if ve_codigo else None

    # relações
    todas = []
    por_comp: Counter = Counter()
    ids = {c["id"] for c in comps}
    m = ws.get("model", {})
    elementos = list(m.get("people", [])) + list(m.get("softwareSystems", []))
    for s in m.get("softwareSystems", []):
        for ct in s.get("containers", []):
            elementos.append(ct)
            elementos.extend(ct.get("components", []))
    for el in elementos:
        for r in el.get("relationships", []):
            if r.get("linkedRelationshipId"):
                continue  # implícita, derivada de outra
            todas.append(r)
            for pt in (r["sourceId"], r["destinationId"]):
                if pt in ids:
                    por_comp[pt] += 1
    media = sum(por_comp.values()) / n if n else 0
    # Alvo: 3 por componente, ou o que o código oferece quando oferece menos (cada par conta nas duas pontas), nunca
    # abaixo de 1. Sem a leitura do código, o alvo fixo.
    alvo, origem = ALVO_RELACOES_POR_COMPONENTE, ""
    if ve_codigo and n:
        no_codigo = 2 * len(info["pares"]) / n
        if no_codigo < ALVO_RELACOES_POR_COMPONENTE:
            alvo = max(1.0, round(no_codigo, 2))
            origem = t(f"; o código mostra {no_codigo:.2f}, teto {ALVO_RELACOES_POR_COMPONENTE}",
                       f"; the code shows {no_codigo:.2f}, cap {ALVO_RELACOES_POR_COMPONENTE}")
    registrar("relacoes_media", min(1.0, media / alvo) if n else None, round(media, 2),
              t(f"{media:.2f} relações por componente (alvo {alvo:g}{origem})",
                f"{media:.2f} relationships per component (target {alvo:g}{origem})"),
              [c["ident"] for c in comps if por_comp[c["id"]] < min(2, alvo)])
    sem_relacao = [c["ident"] for c in comps if por_comp[c["id"]] == 0]
    if com_aresta is None:
        orfaos, nota_extra = sem_relacao, ""
    else:
        # Órfão é o componente sem relação no modelo que o código liga a outro. O que o código também deixa sozinho
        # (um middleware que só fala com a biblioteca padrão) é independente de verdade, não uma omissão.
        orfaos = [i for i in sem_relacao if i in com_aresta]
        soltos = len(sem_relacao) - len(orfaos)
        nota_extra = (t(f"; {soltos} sem relação também no código (fonte {info['fonte']}), não contam",
                        f"; {soltos} also have no relationship in the code (source {info['fonte']}), they do not count")
                      if soltos else "")
    registrar("orfaos", razao(n - len(orfaos), n), None,
              t(f"{len(orfaos)} órfãos de {n}{nota_extra}", f"{len(orfaos)} orphans of {n}{nota_extra}"), orfaos)
    ident_de = {c["id"]: c["ident"] for c in comps}
    nome_de = {el["id"]: el.get("properties", {}).get("structurizr.dsl.identifier", el.get("name", el["id"]))
               for el in elementos}
    sem_qual = [f"{nome_de.get(r['sourceId'])} -> {nome_de.get(r['destinationId'])}" for r in todas
                if not r.get("description", "").strip() or not r.get("technology", "").strip()]
    registrar("relacoes_qualificadas", razao(len(todas) - len(sem_qual), len(todas)), None,
              t(f"{len(todas) - len(sem_qual)} de {len(todas)} com verbo e tecnologia",
                f"{len(todas) - len(sem_qual)} of {len(todas)} with a verb and a technology"), sem_qual)

    # status
    ruins = []
    for c in comps:
        tags = [t for t in c["tags"] if TAG_STATUS.match(t)]
        prop = c["props"].get("status", "")
        prop = STATUS_EN.get(prop.strip().lower(), prop)
        if len(tags) != 1 or (prop and _norm(prop) != _norm(tags[0])):
            ruins.append(c["ident"])
    registrar("status", razao(n - len(ruins), n), None, t(f"{n - len(ruins)} de {n}", f"{n - len(ruins)} of {n}"), ruins)

    # visões
    v = ws.get("views", {})
    com_comp = {ct["id"]: ct.get("name", "") for s in m.get("softwareSystems", []) for ct in s.get("containers", [])
                if ct.get("components")}
    com_visao = {x.get("containerId") for x in v.get("componentViews", [])}
    sem_visao = [nm for cid, nm in com_comp.items() if cid not in com_visao]
    registrar("visoes_container", razao(len(com_comp) - len(sem_visao), len(com_comp)), None,
              t(f"{len(com_comp) - len(sem_visao)} de {len(com_comp)} containers com visão de componentes",
                f"{len(com_comp) - len(sem_visao)} of {len(com_comp)} containers with a component view"), sem_visao)
    dinamicas = v.get("dynamicViews", [])
    registrar("fluxos", min(1.0, len(dinamicas) / ALVO_FLUXOS), len(dinamicas),
              t(f"{len(dinamicas)} visões dinâmicas (alvo {ALVO_FLUXOS})",
                f"{len(dinamicas)} dynamic views (target {ALVO_FLUXOS})"),
              [] if len(dinamicas) >= ALVO_FLUXOS
              else [t(f"faltam {ALVO_FLUXOS - len(dinamicas)} fluxos (inicialização, pedido típico, falha)",
                      f"{ALVO_FLUXOS - len(dinamicas)} flows missing (startup, typical request, failure)")])
    passos = [len(x.get("relationships", [])) for x in dinamicas]
    mp = sum(passos) / len(passos) if passos else 0
    registrar("passos_fluxo", min(1.0, mp / ALVO_PASSOS), round(mp, 2),
              t(f"{mp:.1f} passos por fluxo (alvo {ALVO_PASSOS})", f"{mp:.1f} steps per flow (target {ALVO_PASSOS})"),
              [x.get("key", "") for x in dinamicas if len(x.get("relationships", [])) < ALVO_PASSOS])

    # agrupamento
    ruins = [c["ident"] for c in comps if not c["grupo"] and not c["props"].get("area")]
    registrar("agrupamento", razao(n - len(ruins), n), None, t(f"{n - len(ruins)} de {n}", f"{n - len(ruins)} of {n}"),
              ruins)

    # cobertura
    globs = cfg.get("modulos", [])
    raiz = cfg.get("raiz_codigo", "").strip("/")
    if globs:
        pares_cod = [(x, c["ident"]) for c in comps for x in ponte.caminhos_codigo(c["props"].get("codigo", ""))]
        alvos = _alvos(repo, globs, ponte._ignorar_da_config(cfg))
        fora = [a for a in alvos if _quem_cobre(a, pares_cod, raiz) is None]
        registrar("cobertura", razao(len(alvos) - len(fora), len(alvos)), None,
                  t(f"{len(alvos) - len(fora)} de {len(alvos)} módulos cobertos",
                    f"{len(alvos) - len(fora)} of {len(alvos)} modules covered"), fora)
    else:
        registrar("cobertura", None, None, t("n/d: lodemap.json sem 'modulos'", "n/d: lodemap.json has no 'modulos'"))

    # relações x código
    if info:
        rel = ponte.relatorio_relacoes(info, minimo=1 if info["fonte"] == "ast" else 2)
        sugeridos = [p for p in rel["pares"] if p["confianca"] in ("alta", "media")]
        faltam = [p for p in sugeridos if not p["noModelo"]]
        registrar("recall_relacoes", razao(len(sugeridos) - len(faltam), len(sugeridos)), None,
                  t(f"{len(sugeridos) - len(faltam)} de {len(sugeridos)} pares do código (confiança alta/média; ast: todo "
                    f"import) no modelo; fonte {info['fonte']}",
                    f"{len(sugeridos) - len(faltam)} of {len(sugeridos)} code pairs (confidence alta/media; ast: every "
                    f"import) in the model; source {info['fonte']}"),
                  [t(f"{p['de']} -> {p['para']} ({p['arestas']} arestas, {p['tipo']}, confiança {p['confianca']})",
                     f"{p['de']} -> {p['para']} ({p['arestas']} edges, {p['tipo']}, confidence {p['confianca']})")
                   for p in faltam])
        avaliaveis = set(info["mapa"].values())
        existentes = set(info["pares"]) | {(b, a) for a, b in info["pares"]}
        rel_modelo = [(k, d) for k, d in info["modelo"].items() if k[0] in avaliaveis and k[1] in avaliaveis]
        sem_aresta = [f"{a} -> {b}" for (a, b), _ in rel_modelo if (a, b) not in existentes]
        registrar("precisao_relacoes", razao(len(rel_modelo) - len(sem_aresta), len(rel_modelo)), None,
                  t(f"{len(rel_modelo) - len(sem_aresta)} de {len(rel_modelo)} relações componente->componente com "
                    f"aresta no código; fonte {info['fonte']}",
                    f"{len(rel_modelo) - len(sem_aresta)} of {len(rel_modelo)} component->component relationships with "
                    f"an edge in the code; source {info['fonte']}"), sem_aresta)
    else:
        for k in ("recall_relacoes", "precisao_relacoes"):
            registrar(k, None, None, f"n/d: {motivo}")  # o motivo vem do SystemExit da ponte, já no idioma ativo

    saida = {"projeto": cfg.get("projeto", ""), "componentes": n, "total": total(crit), "criterios": crit,
             "pesos": PESOS}
    if listar:
        saida["reprovados"] = rep
    return saida


def total(crit: dict, so: set[str] | None = None, pesos: dict | None = None) -> float:
    pesos = pesos or PESOS
    ativos = [k for k, c in crit.items() if c.get("nota") is not None and (so is None or k in so)]
    soma = sum(pesos.get(k, 0) for k in ativos)
    return round(sum(crit[k]["nota"] * pesos.get(k, 0) for k in ativos) / soma, 1) if soma else 0.0


# ------------------------------------------------------------------ gate

def gate(resultado: dict, baseline: dict, minimo_total: float | None = None) -> dict:
    notas_base = {k: v for k, v in baseline["criterios"].items() if v is not None}
    comuns = {k for k, c in resultado["criterios"].items() if c["nota"] is not None and k in notas_base}
    base_crit = {k: {"nota": notas_base[k]} for k in comuns}
    total_base = total(base_crit, pesos=baseline.get("pesos"))
    total_proj = total(resultado["criterios"], so=comuns)
    minimo = minimo_total if minimo_total is not None else round(total_base - baseline.get("folgaTotal", FOLGA_TOTAL), 1)
    fracao = baseline.get("fracaoMinimaPorCriterio", FRACAO_MINIMA)
    falhas = []
    if total_proj < minimo:
        falhas.append(t(f"total {total_proj} < mínimo {minimo} (linha de base {total_base})",
                        f"total {total_proj} < minimum {minimo} (baseline {total_base})"))
    for k in sorted(comuns - SEM_PISO):
        piso = round(notas_base[k] * fracao, 1)
        if resultado["criterios"][k]["nota"] < piso:
            falhas.append(t(f"{k} {resultado['criterios'][k]['nota']} < piso {piso} (linha de base {notas_base[k]})",
                            f"{k} {resultado['criterios'][k]['nota']} < floor {piso} (baseline {notas_base[k]})"))
    return {"aprovado": not falhas, "totalComparavel": total_proj, "totalBaselineComparavel": total_base, "minimoTotal": minimo,
            "criteriosComparados": sorted(comuns), "semPiso": sorted(comuns & SEM_PISO), "falhas": falhas}


def main(argv=None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    ap = argparse.ArgumentParser(description=t("Rubrica objetiva e determinística da qualidade de um modelo C4 (lodemap).",
                                               "Objective, deterministic quality rubric for a C4 model (lodemap)."))
    ap.add_argument("--arq", "--arch", required=True, help=t("pasta structurizr do projeto", "the project's structurizr folder"))
    ap.add_argument("--repo", help=t("raiz do repositório (padrão: raiz do git de --arq)",
                                     "repository root (default: the git root of --arq)"))
    ap.add_argument(*opcao("--source", "--fonte"), dest="fonte", choices=["auto", "codegraph", "ast"], default="auto",
                    help=t("de onde vêm as arestas do código (padrão: %(default)s)",
                           "where the code edges come from (default: %(default)s)"))
    ap.add_argument("--db", help=t("índice do CodeGraph em outro lugar", "CodeGraph index somewhere else"))
    ap.add_argument("--baseline", default=str(BASELINE_PADRAO),
                    help=t("JSON da linha de base (padrão: %(default)s)", "baseline JSON (default: %(default)s)"))
    ap.add_argument("--min", default="baseline",
                    help=t("total mínimo, ou 'baseline' (linha de base menos 10 pontos)",
                           "minimum total, or 'baseline' (the baseline minus 10 points)"))
    ap.add_argument(*opcao("--list-failed", "--listar-reprovados"), dest="listar_reprovados", action="store_true",
                    help=t("lista os componentes e relações que reprovam em cada critério",
                           "list the components and relationships that fail each criterion"))
    ap.add_argument(*opcao("--write-baseline", "--gravar-baseline"), dest="gravar_baseline", metavar="JSON",
                    help=t("grava o resultado como nova linha de base", "write the result as the new baseline"))
    ap.add_argument(*opcao("--no-gate", "--sem-gate"), dest="sem_gate", action="store_true",
                    help=t("só mede, sem comparar com a linha de base", "only measure, do not compare with the baseline"))
    a = ap.parse_args(argv)
    usar_mapa(Path(a.arq))
    res = avaliar(Path(a.arq), Path(a.repo) if a.repo else None, a.fonte, Path(a.db) if a.db else None,
                  a.listar_reprovados)
    if a.gravar_baseline:
        base = {"origem": res["projeto"] or Path(a.arq).name, "componentes": res["componentes"],
                "total": res["total"], "criterios": {k: c["nota"] for k, c in res["criterios"].items()},
                "valores": {k: c["detalhe"] for k, c in res["criterios"].items()}, "pesos": PESOS,
                "folgaTotal": FOLGA_TOTAL, "fracaoMinimaPorCriterio": FRACAO_MINIMA}
        Path(a.gravar_baseline).write_text(json.dumps(base, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    codigo = 0
    if not a.sem_gate and Path(a.baseline).is_file():
        base = json.loads(Path(a.baseline).read_text(encoding="utf-8-sig"))
        minimo = None if a.min == "baseline" else float(a.min)
        res["gate"] = gate(res, base, minimo)
        codigo = 0 if res["gate"]["aprovado"] else 1
    print(json.dumps(res, ensure_ascii=False, indent=1))
    return codigo


if __name__ == "__main__":
    sys.exit(main())
