"""Inventário do código para modelar: cada módulo dos globs, quem o cobre no modelo e o resumo dele.

Uso: python inventario.py --repo <raiz> [--arq docs/architecture/structurizr] [--so-fora] [--importadores]
                          [--json <arq>/inventario.json]

Lê "modulos" e "raiz_codigo" do lodemap.json, aplica a mesma regra do teste de cobertura e imprime uma
linha por módulo: o componente que o cobre (ou FORA), o tamanho e a primeira frase da docstring ou do comentário
do topo. Com --importadores, mostra também quais módulos importam cada um (Python), para achar o componente certo
e as relações. Com --json, grava também a lista em JSON (base do inventario.json do agente
lodemap-inventario). Só usa a biblioteca padrão.
"""
from __future__ import annotations

import argparse
import ast
import fnmatch
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import codegraph_ponte as ponte  # noqa: E402  (só para o filtro "ignorar", o mesmo do esqueleto e da qualidade)

_DECL = re.compile(r'^\s*(\w+)\s*=\s*(component|container|softwareSystem|person)\s+"([^"]*)"')
_COD = re.compile(r'^\s*"codigo"\s+"([^"]*)"')


def componentes(modelo: Path) -> list[tuple[str, str]]:
    pares = []
    for f in sorted(modelo.glob("*.dsl")):
        pilha, prof = [], 0
        for linha in f.read_text(encoding="utf-8").splitlines():
            m = _DECL.match(linha)
            limpa = re.sub(r'"[^"]*"', '""', linha)
            if m and limpa.rstrip().endswith("{"):
                pilha.append((m.group(1), m.group(2), prof))
            c = _COD.match(linha)
            if c and pilha and pilha[-1][1] == "component":
                pasta = ""
                for parte in re.split(r"[,;]", re.sub(r"\([^)]*\)", "", c.group(1))):
                    parte = parte.strip().strip("`")
                    if not parte:
                        continue
                    if "/" in parte:
                        pasta = parte if parte.endswith("/") else parte.rsplit("/", 1)[0] + "/"
                        pares.append((parte, pilha[-1][0]))
                    else:
                        pares.append((pasta + parte, pilha[-1][0]))
            prof += limpa.count("{") - limpa.count("}")
            while pilha and prof <= pilha[-1][2]:
                pilha.pop()
    return pares


def cobre(alvo: str, pares, raiz: str) -> str:
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
    return ""


def resumo(p: Path) -> str:
    if p.is_dir():
        init = p / "__init__.py"
        if init.is_file():
            return resumo(init)
        arqs = [x.name for x in sorted(p.iterdir())][:6]
        return "pasta: " + ", ".join(arqs)
    try:
        texto = p.read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        return ""
    if p.suffix == ".py":
        try:
            doc = ast.get_docstring(ast.parse(texto)) or ""
        except SyntaxError:
            doc = ""
        if doc:
            return re.split(r"(?<=[.!?])\s", doc.strip().replace("\n", " "), maxsplit=1)[0][:140]
    for linha in texto.splitlines()[:15]:
        linha = linha.strip().lstrip("#/*- ").strip()
        if len(linha) > 15:
            return linha[:140]
    return ""


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repo", required=True)
    ap.add_argument("--arq", default="docs/architecture/structurizr")
    ap.add_argument("--so-fora", action="store_true")
    ap.add_argument("--importadores", action="store_true")
    ap.add_argument("--json", help="grava o inventário em JSON neste caminho")
    a = ap.parse_args(argv)
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    repo = Path(a.repo).resolve()
    arq = repo / a.arq
    cfg = json.loads((arq / "lodemap.json").read_text(encoding="utf-8-sig"))
    raiz = cfg.get("raiz_codigo", "").strip("/")
    pares = componentes(arq / "model")
    alvos = set()
    ignorar = ponte._ignorar_da_config(cfg)
    for padrao in cfg.get("modulos", []):
        pasta = padrao.endswith("/")
        for p in repo.glob(padrao.rstrip("/")):
            if any(x in {"__pycache__", "node_modules"} or x.startswith(".") for x in p.relative_to(repo).parts):
                continue
            if ponte._ignorado(p.relative_to(repo).as_posix(), ignorar):
                continue
            if pasta == p.is_dir():
                alvos.add(p.relative_to(repo).as_posix() + ("/" if pasta else ""))
    importadores: dict[str, list[str]] = {}
    if a.importadores:
        pys = list((repo / raiz).rglob("*.py")) if raiz else []
        for f in pys:
            try:
                arvore = ast.parse(f.read_text(encoding="utf-8-sig", errors="replace"))
            except SyntaxError:
                continue
            for n in ast.walk(arvore):
                nomes = [x.name for x in n.names] if isinstance(n, ast.Import) else (
                    [n.module or ""] if isinstance(n, ast.ImportFrom) else [])
                for nome in nomes:
                    importadores.setdefault(nome.split(".")[0], []).append(f.relative_to(repo).as_posix())
    fora = 0
    registros = []
    for alvo in sorted(alvos):
        quem = cobre(alvo, pares, raiz)
        fora += not quem
        if a.so_fora and quem:
            continue
        p = repo / alvo.rstrip("/")
        if p.is_file():
            with p.open(encoding="utf-8", errors="replace") as fh:
                tam = f"{sum(1 for _ in fh)} l"
        else:
            tam = "pasta"
        res = resumo(p)
        linha = f"{quem or 'FORA':<22} {alvo:<48} {tam:>7}  {res}"
        usos = []
        if a.importadores:
            chave = p.stem if p.is_file() else p.name
            usos = sorted(set(importadores.get(chave, [])) - {alvo})
            if usos:
                linha += f"\n{'':<22} importado por: {', '.join(usos[:4])}"
        registros.append({"caminho": alvo, "tipo": "arquivo" if p.is_file() else "pasta", "tamanho": tam,
                          "proposito": res, "coberto_por": quem or None, "importado_por": usos})
        print(linha)
    print(f"\n{len(alvos) - fora} de {len(alvos)} cobertos; {fora} fora do modelo.")
    if a.json:
        Path(a.json).write_text(json.dumps({"modulos": registros, "cobertos": len(alvos) - fora, "fora": fora},
                                           ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"inventário em {a.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
