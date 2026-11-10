"""Modo incremental da lodemap: o que mudou no código desde a última geração e quais componentes isso toca.

Uso (na pasta da arquitetura):
  python scripts/lodemap_diff.py                 # JSON com o diff desde estado.json:ultimoCommit
  python scripts/lodemap_diff.py --trabalho      # inclui também as mudanças ainda não commitadas
  python scripts/lodemap_diff.py --marcar [--checkpoint "rótulo"]   # fim de geração verde: ultimoCommit = HEAD
  python scripts/lodemap_diff.py --marcar --checkpoint-env          # o rótulo vem de LODEMAP_CHECKPOINT (acentos intactos)
  python scripts/lodemap_diff.py --relevante     # sai 0 se há mudança que pede regenerar (código dos globs,
                                             # DSL, métricas, ADRs, docs); 1 se não há; 0 no modo completo

Saída (JSON):
  {"modo": "incremental", "de": <commit>, "ate": <commit>,
   "modulosNovos": [...], "modulosMudados": [...], "modulosRemovidos": [...],
   "componentesAfetados": [{"id", "nome", "container", "status", "modulos": [...]}],
   "semComponente": [...]}
Sem ultimoCommit (ou com o commit ausente do repositório): {"modo": "completo", "motivo": "..."}.

Os módulos são os alvos dos globs de "modulos" do lodemap.json (um glob terminado em "/" casa a pasta
inteira). Os componentes e o codigo vêm do workspace.json exportado (.structurizr/export/workspace.json, ou
workspace.json ao lado do DSL). Só usa a biblioteca padrão.
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from arq_comum import glob_regex, globs_ignorar, modulo_ignorado  # noqa: E402

ESTADO_REL = Path(".lodemap") / "estado.json"
PASSOS = ("inventario", "modelador", "metricas", "gerador", "verificador", "revisor-visual")


def git(repo: Path, *args: str) -> tuple[int, str]:
    r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, encoding="utf-8")
    return r.returncode, r.stdout


def raiz_repo(arq: Path) -> Path:
    cod, out = git(arq, "rev-parse", "--show-toplevel")
    if cod:
        raise SystemExit("lodemap_diff: a pasta não está num repositório git")
    return Path(out.strip())


def ler_estado(arq: Path) -> dict:
    p = arq / ESTADO_REL
    return json.loads(p.read_text(encoding="utf-8-sig")) if p.is_file() else {}


def estado_vazio(projeto: str) -> dict:
    return {
        "versao": 1,
        "projeto": projeto,
        "ultimoCommit": None,
        "geradoEm": None,
        "passos": {p: {"status": "pendente", "arquivos": [], "contagens": {}, "pendencias": []} for p in PASSOS},
        "artefatos": {
            "inventario": "inventario.json",
            "modelo": "model/",
            "metricas": "metricas/metricas.json",
            "explorador": "explorador/dados.js",
            "documentos": "docs/",
            "site": "site/",
        },
    }


def marcar(arq: Path, checkpoint: str = "") -> dict:
    """Fim de geração verde: grava ultimoCommit = HEAD e geradoEm, preservando o resto do estado."""
    cfg = json.loads((arq / "lodemap.json").read_text(encoding="utf-8-sig"))
    repo = raiz_repo(arq)
    _, head = git(repo, "rev-parse", "HEAD")
    estado = ler_estado(arq) or estado_vazio(cfg.get("projeto", ""))
    base = estado_vazio(cfg.get("projeto", ""))
    for k, v in base.items():
        estado.setdefault(k, v)
    estado["ultimoCommit"] = head.strip()
    estado["geradoEm"] = datetime.now().astimezone().isoformat(timespec="seconds")
    estado["checkpoint"] = checkpoint or None
    hist = estado.setdefault("historico", [])
    hist.insert(0, {"commit": estado["ultimoCommit"], "geradoEm": estado["geradoEm"], "checkpoint": checkpoint or None})
    del hist[30:]
    g = estado["passos"].setdefault("gerador", {})
    g.update({"status": "ok", "arquivos": ["explorador/dados.js", "docs/02-mapa-de-status.md",
                                            "docs/90-catalogo-de-observabilidade.md", "docs/91-metricas-e-benchmarks.md"]})
    destino = arq / ESTADO_REL
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(estado, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return estado


def caminhos_codigo(codigo: str) -> list[str]:
    codigo = re.sub(r"\([^)]*\)", "", codigo)
    pasta, out = "", []
    for parte in re.split(r"[,;]", codigo):
        parte = parte.strip().strip("`")
        if not parte:
            continue
        if "/" in parte:
            pasta = parte if parte.endswith("/") else parte.rsplit("/", 1)[0] + "/"
            out.append(parte)
        else:
            out.append(pasta + parte)
    return out


def _en(arq: Path) -> bool:
    """Mapa em inglês? LODEMAP_IDIOMA vence o "idioma" do lodemap.json."""
    i = (os.environ.get("LODEMAP_IDIOMA") or "").strip().lower()
    if not i:
        try:
            i = str(json.loads((arq / "lodemap.json").read_text(encoding="utf-8")).get("idioma") or "")
        except (OSError, ValueError, AttributeError):
            i = ""
    return i == "en"


def modulo_de(arquivo: str, globs: list[str], ignorar: list[str] | None = None) -> str | None:
    """Alvo de cobertura que contém o arquivo: o próprio arquivo (glob de arquivo) ou a pasta (glob de pasta).

    Candidato que casa algum glob de `ignorar` (já normalizado por `globs_ignorar`) não é módulo: o glob seguinte
    ainda pode casar o arquivo.
    """
    for g in globs:
        if g.endswith("/"):
            partes_g = g.rstrip("/").split("/")
            partes_a = arquivo.split("/")
            if len(partes_a) > len(partes_g) and fnmatch.fnmatch("/".join(partes_a[:len(partes_g)]), g.rstrip("/")):
                pasta = "/".join(partes_a[:len(partes_g)])
                if modulo_ignorado(pasta, ignorar):
                    continue
                return pasta + "/"
        elif glob_regex(g).fullmatch(arquivo):
            if modulo_ignorado(arquivo, ignorar):
                continue
            return arquivo
    return None


def componentes(workspace: Path, raiz_codigo: str) -> list[dict]:
    ws = json.loads(workspace.read_text(encoding="utf-8-sig"))
    out = []
    for s in ws["model"].get("softwareSystems", []):
        for c in s.get("containers", []):
            for k in c.get("components", []):
                p = k.get("properties", {})
                cods = [x for x in caminhos_codigo(p.get("codigo", "")) if x.rstrip("/") != raiz_codigo]
                out.append({"id": p.get("structurizr.dsl.identifier", k["id"]), "nome": k["name"], "container": c["name"],
                            "status": p.get("status", ""), "codigo": cods})
    return out


def cobre(caminho_codigo: str, arquivo: str, modulo: str) -> bool:
    c = caminho_codigo
    if any(ch in c for ch in "*?["):
        return fnmatch.fnmatch(arquivo, c) or fnmatch.fnmatch(modulo, c)
    if c.endswith("/"):
        return arquivo.startswith(c) or modulo.startswith(c) or (modulo.endswith("/") and c.startswith(modulo))
    return c in (arquivo, modulo)


def diff(arq: Path, workspace: Path | None = None, trabalho: bool = False) -> dict:
    arq = arq.resolve()
    cfg = json.loads((arq / "lodemap.json").read_text(encoding="utf-8-sig"))
    estado = ler_estado(arq)
    de = estado.get("ultimoCommit")
    if not de:
        return {"modo": "completo", "motivo": "sem ultimoCommit em .lodemap/estado.json"}
    repo = raiz_repo(arq)
    if git(repo, "cat-file", "-e", f"{de}^{{commit}}")[0]:
        return {"modo": "completo", "motivo": f"o commit {de} não está no repositório"}
    _, ate = git(repo, "rev-parse", "HEAD")
    linhas = git(repo, "diff", "--name-status", "--no-renames", f"{de}..HEAD")[1].splitlines()
    if trabalho:
        linhas += git(repo, "diff", "--name-status", "--no-renames", "HEAD")[1].splitlines()
        linhas += [f"A\t{x}" for x in git(repo, "ls-files", "--others", "--exclude-standard")[1].splitlines()]
    globs = cfg.get("modulos", [])
    ignorar = globs_ignorar(cfg)
    raiz_codigo = cfg.get("raiz_codigo", "").strip("/")
    mudancas: dict[str, tuple[str, str]] = {}  # arquivo -> (status, módulo)
    for linha in linhas:
        partes = linha.split("\t")
        if len(partes) < 2:
            continue
        st, arquivo = partes[0][0], partes[-1].replace("\\", "/")
        mod = modulo_de(arquivo, globs, ignorar)
        if mod:
            mudancas[arquivo] = (st, mod)
    novos, mudados, removidos = set(), set(), set()
    for arquivo, (st, mod) in mudancas.items():
        pasta = mod.endswith("/")
        existe_mod = (repo / mod.rstrip("/")).exists()
        if st == "D":
            (mudados if pasta and existe_mod else removidos).add(mod)
        elif st == "A" and not pasta:
            novos.add(mod)
        elif st == "A" and pasta and not git(repo, "cat-file", "-e", f"{de}:{mod.rstrip('/')}")[0] == 0:
            novos.add(mod)
        else:
            mudados.add(mod)
    mudados -= novos | removidos
    ws = workspace or next((p for p in (arq / ".structurizr" / "export" / "workspace.json", arq / "workspace.json") if p.is_file()), None)
    comps = componentes(ws, raiz_codigo) if ws else []
    afetados: dict[str, dict] = {}
    sem = []
    for mod in sorted(novos | mudados | removidos):
        arquivos = [a for a, (_, m) in mudancas.items() if m == mod]
        donos = [k for k in comps if any(cobre(c, a, mod) for c in k["codigo"] for a in arquivos + [mod])]
        for k in donos:
            afetados.setdefault(k["id"], {**{x: k[x] for x in ("id", "nome", "container", "status")}, "modulos": []})["modulos"].append(mod)
        if not donos and mod not in removidos:
            sem.append(mod)
    return {
        "modo": "incremental",
        "de": de,
        "ate": ate.strip(),
        "workspace": str(ws) if ws else None,
        "modulosNovos": sorted(novos),
        "modulosMudados": sorted(mudados),
        "modulosRemovidos": sorted(removidos),
        "componentesAfetados": sorted(afetados.values(), key=lambda x: x["id"]),
        "semComponente": sorted(sem),
    }


FONTES_ARQ = ("model/", "views/", "metricas/", "adrs/", "docs/", "workspace.dsl", "lodemap.json")
GERADOS_ARQ = ("docs/02-mapa-de-status.md", "docs/90-catalogo-de-observabilidade.md", "docs/91-metricas-e-benchmarks.md")


def fontes_mudaram(arq: Path, de: str) -> bool:
    """Algum arquivo-fonte da própria arquitetura (DSL, métricas, ADRs, docs escritos à mão, lodemap.json) mudou
    desde o commit `de`, no histórico ou na árvore de trabalho? Os documentos gerados não contam."""
    repo = raiz_repo(arq)
    rel = arq.resolve().relative_to(repo.resolve()).as_posix().rstrip("/") + "/"
    nomes = git(repo, "diff", "--name-only", f"{de}..HEAD")[1].splitlines()
    nomes += git(repo, "diff", "--name-only", "HEAD")[1].splitlines()
    return any(n.startswith(rel) and n[len(rel):].startswith(FONTES_ARQ) and n[len(rel):] not in GERADOS_ARQ
               for n in nomes)


def relevante(arq: Path) -> bool:
    """Há o que regenerar desde ultimoCommit? Código dos globs ou arquivos da própria arquitetura."""
    d = diff(arq, trabalho=True)
    if d["modo"] == "completo":
        return True
    if d["modulosNovos"] or d["modulosMudados"] or d["modulosRemovidos"]:
        return True
    return fontes_mudaram(arq, d["de"])


def main(argv=None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--arq", default=str(Path(__file__).resolve().parent.parent))
    ap.add_argument("--workspace")
    ap.add_argument("--trabalho", action="store_true", help="inclui mudanças não commitadas e arquivos novos")
    ap.add_argument("--marcar", action="store_true", help="grava ultimoCommit = HEAD e geradoEm")
    ap.add_argument("--checkpoint", default="", help="rótulo do checkpoint, com --marcar")
    ap.add_argument("--checkpoint-env", action="store_true",
                    help="lê o rótulo da variável LODEMAP_CHECKPOINT (UTF-8 intacto; é o que o atualizar.ps1 usa)")
    ap.add_argument("--relevante", action="store_true", help="código de saída 0 se há o que regenerar")
    a = ap.parse_args(argv)
    arq = Path(a.arq)
    if a.marcar:
        rotulo = os.environ.get("LODEMAP_CHECKPOINT", "") if a.checkpoint_env else a.checkpoint
        e = marcar(arq, rotulo.strip())
        if _en(arq):
            print(f"estado.json: last commit {e['ultimoCommit'][:10]} at {e['geradoEm']}")
        else:
            print(f"estado.json: ultimoCommit {e['ultimoCommit'][:10]} em {e['geradoEm']}")
        return 0
    if a.relevante:
        ok = relevante(arq)
        if _en(arq):
            print("changes to regenerate" if ok else "nothing changed since the last run")
        else:
            print("há mudanças para regenerar" if ok else "nada mudou desde a última geração")
        return 0 if ok else 1
    print(json.dumps(diff(arq, Path(a.workspace) if a.workspace else None, a.trabalho), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
