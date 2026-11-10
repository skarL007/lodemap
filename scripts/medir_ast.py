"""Mede a precisão e o recall da prova de relação por imports do modo ast (codegraph_ponte.py), por linguagem.

Duas camadas, ambas determinísticas e sem custo de modelo:
  A  gabarito rotulado à mão: cada pasta de tests/fixtures/ast_precisao/<linguagem>/ é um mini-repositório com um
     gabarito.json (arestas arquivo -> arquivo esperadas, mais `limites`: erros conhecidos que o método não promete
     evitar, como #if 0 ou alias de bundler). Limite conhecido NÃO entra na conta de precisão e recall; aparece à parte.
  B  repositório real (--repo): as arestas do ast contra o índice do CodeGraph, aberto em modo somente leitura. O índice
     é referência, não verdade: por isso o relatório separa o falso positivo "duro" (nenhuma aresta de nenhum tipo no
     índice) do "corroborado" (o índice não tem o import, mas tem chamada/referência entre os mesmos arquivos).

Definições (pares únicos arquivo -> arquivo):
  TP = no ast e na referência; FP = no ast e fora da referência; FN = na referência e fora do ast;
  precisão = TP / (TP + FP); recall = TP / (TP + FN). Sem denominador, o valor é null ("n/a"), nunca 1,0.

Uso:
  python medir_ast.py [--fixtures <pasta>] [--linguagem go] [--repo <raiz> ...] [--db <codegraph.db>]
                      [--ponte <codegraph_ponte.py alternativo>] [--saida medicao.json] [--silencioso]
`--ponte` mede outra versão do extrator (por exemplo, a de antes de uma correção: `git show <sha>:scripts/codegraph_ponte.py`).
Nunca escreve em --repo e nunca roda `codegraph init`. Só usa a biblioteca padrão.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sqlite3
import sys
from datetime import date
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI.parent))
from lodemap.idioma import opcao, t  # noqa: E402
FIXTURES = AQUI.parent / "tests" / "fixtures" / "ast_precisao"
# Tipos de aresta do CodeGraph que corroboram dependência entre arquivos sem serem o import em si.
TIPOS_CORROBORAM = ("calls", "instantiates", "references", "extends", "implements", "decorates")


def carregar_ponte(caminho: str | Path | None = None):
    """O módulo codegraph_ponte padrão (ao lado deste script) ou o arquivo dado em --ponte."""
    if caminho is None:
        sys.path.insert(0, str(AQUI))
        import codegraph_ponte
        return codegraph_ponte
    spec = importlib.util.spec_from_file_location("codegraph_ponte_alternativo", str(caminho))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def _razao(num: int, den: int) -> float | None:
    return round(num / den, 4) if den else None


def _fmt(v: float | None) -> str:
    return "n/a" if v is None else f"{v:.3f}"


def _pares(arestas) -> set[tuple[str, str]]:
    return {(a, b) for (a, b) in arestas}


# ------------------------------------------------------------------ camada A

def medir_fixture(pasta: Path, ponte) -> dict:
    gab = json.loads((pasta / "gabarito.json").read_text(encoding="utf-8"))
    esperado = {tuple(p) for p in gab["arestas"]}
    limites = {tuple(x["par"]): x for x in gab.get("limites", [])}
    obtido = _pares(ponte.arestas_ast(pasta))
    tp = esperado & obtido
    fn = esperado - obtido
    fp = obtido - esperado
    # Limite conhecido fica FORA da conta: `fp` = aresta falsa que o extrator ainda produz; `fn` = aresta verdadeira
    # que ele ainda perde (o par do limite NÃO consta em `arestas`, é só informado). Se o extrator já acerta o limite
    # (o `fp` sumiu, ou o par `fn` apareceu), o limite é listado em `superados` e não conta como erro.
    lim_fp = {p for p, x in limites.items() if x.get("tipo") == "fp" and p in obtido and p not in esperado}
    lim_fn = {p for p, x in limites.items() if x.get("tipo") == "fn" and p not in obtido}
    superados = {p for p, x in limites.items() if (x.get("tipo") == "fp" and p not in obtido)
                 or (x.get("tipo") == "fn" and p in obtido)}
    fp -= lim_fp | superados
    fn -= lim_fn
    arquivos = len(ponte.listar_fontes(pasta))
    return {
        "linguagem": gab["linguagem"], "arquivos": arquivos, "arestasGabarito": len(esperado),
        "tp": len(tp), "fp": len(fp), "fn": len(fn),
        "precisao": _razao(len(tp), len(tp) + len(fp)), "recall": _razao(len(tp), len(tp) + len(fn)),
        "limitesConhecidos": {"fpConhecidos": sorted(map(list, lim_fp)), "fnConhecidos": sorted(map(list, lim_fn)),
                              "superados": sorted(map(list, superados)), "total": len(limites)},
        "erros": {"fp": sorted(map(list, fp)), "fn": sorted(map(list, fn))},
    }


def medir_camada_a(fixtures: Path = FIXTURES, ponte=None, so: str | None = None) -> dict:
    ponte = ponte or carregar_ponte()
    out = {}
    for pasta in sorted(p for p in fixtures.iterdir() if (p / "gabarito.json").is_file()):
        if so and pasta.name != so:
            continue
        out[pasta.name] = medir_fixture(pasta, ponte)
    return out


# ------------------------------------------------------------------ camada B

def referencia_codegraph(db: Path) -> tuple[dict[tuple[str, str], set[str]], set[str]]:
    """(par arquivo->arquivo -> tipos de aresta no índice, arquivos indexados). Somente leitura."""
    con = sqlite3.connect(f"file:{db.resolve().as_posix()}?mode=ro", uri=True)
    try:
        q = ("SELECT DISTINCT s.file_path, t.file_path, e.kind FROM edges e "
             "JOIN nodes s ON s.id = e.source JOIN nodes t ON t.id = e.target WHERE s.file_path <> t.file_path")
        tipos: dict[tuple[str, str], set[str]] = {}
        for a, b, k in con.execute(q):
            tipos.setdefault((a, b), set()).add(k)
        indexados = {r[0] for r in con.execute("SELECT path FROM files")}
    finally:
        con.close()
    return tipos, indexados


def medir_repo(repo: Path, ponte, db: Path | None = None) -> dict:
    db = db or repo / ".codegraph" / "codegraph.db"
    if not db.is_file():
        return {"repo": str(repo), "erro": f"sem índice em {db}"}
    ref, indexados = referencia_codegraph(db)
    fontes = set(ponte.listar_fontes(repo))
    ast = _pares(ponte.arestas_ast(repo))
    ref_imports = {p for p, t in ref.items() if "imports" in t}
    ling = ponte.LINGUAGEM_EXT

    def lg(arq: str) -> str:
        nome = ling.get(os.path.splitext(arq)[1], "outra")
        return "c" if nome == "cpp" else nome

    # só se comparam arquivos que as duas fontes enxergam; o resto é cobertura diferente, não erro de aresta
    comum = fontes & indexados
    por: dict[str, dict] = {}
    for a, b in sorted(ast | ref_imports):
        if a not in comum or b not in comum:
            continue
        d = por.setdefault(lg(a), {"tp": 0, "fpDuro": 0, "fpCorroborado": 0, "fn": 0, "erros": {"fpDuro": [],
                                                                                              "fpCorroborado": [], "fn": []}})
        no_ast, no_ref = (a, b) in ast, (a, b) in ref_imports
        if no_ast and no_ref:
            d["tp"] += 1
        elif no_ast:
            corrobora = bool(ref.get((a, b), set()) & set(TIPOS_CORROBORAM))
            d["fpCorroborado" if corrobora else "fpDuro"] += 1
            d["erros"]["fpCorroborado" if corrobora else "fpDuro"].append([a, b])
        else:
            d["fn"] += 1
            d["erros"]["fn"].append([a, b])
    for lng, d in por.items():
        tp, fpd, fpc, fn = d["tp"], d["fpDuro"], d["fpCorroborado"], d["fn"]
        d["arquivos"] = sum(1 for f in comum if lg(f) == lng)
        d["precisaoImports"] = _razao(tp, tp + fpd + fpc)        # contra o que o índice chama de import
        d["precisaoAmpla"] = _razao(tp + fpc, tp + fpd + fpc)    # contando a dependência corroborada por chamada
        d["recall"] = _razao(tp, tp + fn)
    return {"repo": str(repo), "indice": str(db), "arquivosAst": len(fontes), "arquivosIndice": len(indexados),
            "arquivosComuns": len(comum), "linguagens": dict(sorted(por.items()))}


# ------------------------------------------------------------------ saída

def imprimir(resultado: dict, erros_max: int = 12) -> None:
    a = resultado.get("camadaA")
    if a:
        print(t(f"== Camada A: gabarito rotulado à mão ({resultado['fixtures']}) ==",
                f"== Layer A: hand-labeled ground truth ({resultado['fixtures']}) =="))
        print(f"{t('linguagem', 'language'):<11}{t('arq', 'files'):>4}{t('gab', 'gt'):>5}{'TP':>5}{'FP':>4}{'FN':>4}"
              f"{t('precisão', 'precision'):>10}{'recall':>8}  {t('limites conhecidos', 'known limits')}")
        for nome, d in a.items():
            lim = d["limitesConhecidos"]
            info = t(f"{len(lim['fpConhecidos'])} FP e {len(lim['fnConhecidos'])} FN conhecidos fora da conta, "
                     f"{len(lim['superados'])} superado(s), de {lim['total']}",
                     f"{len(lim['fpConhecidos'])} known FP and {len(lim['fnConhecidos'])} known FN left out of the count, "
                     f"{len(lim['superados'])} overcome, of {lim['total']}")
            print(f"{nome:<11}{d['arquivos']:>4}{d['arestasGabarito']:>5}{d['tp']:>5}{d['fp']:>4}{d['fn']:>4}"
                  f"{_fmt(d['precisao']):>10}{_fmt(d['recall']):>8}  {info}")
        for nome, d in a.items():
            for tipo in ("fp", "fn"):
                for par in d["erros"][tipo][:erros_max]:
                    print(f"  [{nome}] {tipo.upper()}: {par[0]} -> {par[1]}")
    for r in resultado.get("camadaB", []):
        print(t(f"\n== Camada B: {r['repo']} ==", f"\n== Layer B: {r['repo']} =="))
        if "erro" in r:
            print(f"  {r['erro']}")
            continue
        print(t(f"  arquivos: ast {r['arquivosAst']}, índice {r['arquivosIndice']}, comuns {r['arquivosComuns']}",
                f"  files: ast {r['arquivosAst']}, index {r['arquivosIndice']}, common {r['arquivosComuns']}"))
        print(f"  {t('linguagem', 'language'):<11}{t('arq', 'files'):>5}{'TP':>6}{t('FP duro', 'hard FP'):>9}"
              f"{t('FP corr.', 'corr. FP'):>9}{'FN':>6}{t('P imports', 'P imports'):>11}{t('P ampla', 'P broad'):>9}{'recall':>8}")
        for nome, d in r["linguagens"].items():
            print(f"  {nome:<11}{d['arquivos']:>5}{d['tp']:>6}{d['fpDuro']:>9}{d['fpCorroborado']:>9}{d['fn']:>6}"
                  f"{_fmt(d['precisaoImports']):>11}{_fmt(d['precisaoAmpla']):>9}{_fmt(d['recall']):>8}")
        for nome, d in r["linguagens"].items():
            for tipo in ("fpDuro", "fn"):
                for par in d["erros"][tipo][:erros_max]:
                    print(f"    [{nome}] {tipo}: {par[0]} -> {par[1]}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=t("Mede a precisão e o recall da prova de relação por imports do modo ast "
                                               "(codegraph_ponte.py), por linguagem.",
                                               "Measure the precision and recall of the ast mode's import-based relation "
                                               "proof (codegraph_ponte.py), per language."))
    ap.add_argument("--fixtures", type=Path, default=FIXTURES,
                    help=t("pasta com uma subpasta por linguagem (camada A)", "folder with one subfolder per language (layer A)"))
    ap.add_argument(*opcao("--language", "--linguagem"), dest="linguagem",
                    help=t("mede só essa subpasta da camada A", "measure only this layer A subfolder"))
    ap.add_argument("--repo", type=Path, action="append", default=[],
                    help=t("repositório real com .codegraph/ (camada B); repetível",
                           "real repository with .codegraph/ (layer B); repeatable"))
    ap.add_argument("--db", type=Path, help=t("índice do CodeGraph, se não for <repo>/.codegraph/codegraph.db",
                                              "CodeGraph index, if not <repo>/.codegraph/codegraph.db"))
    ap.add_argument(*opcao("--bridge", "--ponte"), dest="ponte", type=Path,
                    help=t("codegraph_ponte.py alternativo (medir a versão de antes)",
                           "alternative codegraph_ponte.py (to measure the version from before)"))
    ap.add_argument(*opcao("--output", "--saida"), dest="saida", type=Path,
                    help=t("grava o resultado completo em JSON", "write the full result as JSON"))
    ap.add_argument(*opcao("--max-errors", "--erros-max"), dest="erros_max", type=int, default=12,
                    help=t("erros listados por linguagem na tela", "errors listed per language on screen"))
    ap.add_argument(*opcao("--quiet", "--silencioso"), dest="silencioso", action="store_true",
                    help=t("não imprime a tabela", "do not print the table"))
    args = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):  # console do Windows em cp1252 estraga os acentos
        sys.stdout.reconfigure(encoding="utf-8")
    ponte = carregar_ponte(args.ponte)
    res = {"data": date.today().isoformat(), "ponte": str(args.ponte or AQUI / "codegraph_ponte.py"),
           "fixtures": str(args.fixtures), "camadaA": medir_camada_a(args.fixtures, ponte, args.linguagem),
           "camadaB": [medir_repo(r, ponte, args.db) for r in args.repo]}
    if args.saida:
        args.saida.write_text(json.dumps(res, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if not args.silencioso:
        imprimir(res, args.erros_max)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
