"""Campanha de custo do Lodemap: mapa completo, do zero, em repositórios públicos, 3 repetições por pilha de modelos.

Cada rodada:
- é uma cópia nova (`git archive` + `git init`) do repositório numa tag fixa;
- tem a skill e os agentes só em `.claude/` do projeto;
- roda numa sessão `claude -p` com `--setting-sources project` e `--strict-mcp-config`, sem CLAUDE.md, ganchos nem
  MCP do usuário.

O custo vem do próprio CLI, nos campos `total_cost_usd` e `modelUsage`. É o preço equivalente pela API, não a fatura: a
assinatura não fatura por chamada. A qualidade vem do `qualidade.py` e do teste de cobertura entregue no projeto.

Uso: python rodar_campanha.py --repos chi,click,axios --pilhas sonnet,haiku --reps 3 --paralelo 3
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import os
import random
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

# Caminhos do original trocados por variaveis de ambiente (publicacao sem caminho absoluto do autor).
# LODEMAP_CAMP_BASE: pasta da campanha (com src/<repo> clonados); LODEMAP_SKILL: checkout do lodemap.
BASE = Path(os.environ.get("LODEMAP_CAMP_BASE", ".")).resolve()
SRC = BASE / "src"
SKILL = Path(os.environ.get("LODEMAP_SKILL", "../..")).resolve()
PY = sys.executable
ARQ = "docs/architecture/structurizr"

PROMPT = """Use the lodemap skill to build the architecture map of this repository from scratch, in English
(`"idioma": "en"` in lodemap.json). The owner has already read the plan and approved it: record the consent with
scopes `gerar,modelo` only (no `gancho`: do not install a git hook), then go through every step of the skill until the
map is finished and verified (coverage test passing, quality gate run, explorer generated). Do not ask questions; when
the skill says to ask the owner, choose the documented default and note it. Never push, never touch files outside
this folder, never run `codegraph init`. At the end, print one line: DONE or FAILED with the reason."""


def sh(cmd, cwd=None, timeout=None, env=None):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace",
                          timeout=timeout, env=env)


def preparar(repo: str, pilha: str, rep: int) -> Path:
    d = BASE / "runs" / f"{repo}-{pilha}-{rep}"
    if d.exists():
        def _liberar(func, caminho, _exc):
            os.chmod(caminho, 0o700)
            func(caminho)
        shutil.rmtree(d, onerror=_liberar)
    d.mkdir(parents=True)
    p =subprocess.run(["git", "-C", str(SRC / repo), "archive", "--format=tar", "HEAD"], capture_output=True)
    subprocess.run(["tar", "-x", "-C", str(d)], input=p.stdout, check=True)
    for c in (["git", "init", "-q"], ["git", "add", "-A"],
              ["git", "-c", "user.name=campanha", "-c", "user.email=campanha@lodemap.invalid", "commit", "-q", "-m", "base"]):
        subprocess.run(c, cwd=d, check=True, capture_output=True)
    ag = d / ".claude" / "agents"
    ag.mkdir(parents=True)
    for f in (SKILL / "agents").glob("lodemap-*.md"):
        txt = f.read_text(encoding="utf-8")
        if pilha == "haiku":
            txt = re.sub(r"(?m)^model:\s*\S+", "model: haiku", txt)
        (ag / f.name).write_text(txt, encoding="utf-8")
    sk = d / ".claude" / "skills" / "lodemap"
    sk.mkdir(parents=True)
    shutil.copy2(SKILL / "SKILL.md", sk / "SKILL.md")
    # .claude fica fora do git da cópia, para não contar como código do projeto
    (d / ".git" / "info" / "exclude").write_text(".claude/\n", encoding="utf-8")
    return d


def rodar(repo: str, pilha: str, rep: int, timeout_s: int) -> dict:
    d = preparar(repo, pilha, rep)
    orq = "sonnet" if pilha == "sonnet" else "haiku"
    cmd = ["claude", "-p", "--model", orq, "--effort", "medium", "--output-format", "json",
           "--strict-mcp-config", "--setting-sources", "project", "--permission-mode", "bypassPermissions",
           PROMPT]
    log = BASE / "resultados" / f"{repo}-{pilha}-{rep}.internas.jsonl"
    log.parent.mkdir(exist_ok=True)
    log.unlink(missing_ok=True)
    env = dict(os.environ, LODEMAP_CLAUDE=str(BASE / "claude_shim.py"), LODEMAP_CAMP_LOG=str(log),
               LODEMAP_CAMP_REAL_CLAUDE=shutil.which("claude") or "claude")
    t0 = time.time()
    try:
        r = sh(cmd, cwd=d, timeout=timeout_s, env=env)
        saida, erro = r.stdout, r.stderr
    except subprocess.TimeoutExpired as e:
        saida, erro = (e.stdout or b"").decode("utf-8", "replace") if isinstance(e.stdout, bytes) else (e.stdout or ""), "timeout"
    dur = time.time() - t0
    res: dict = {"repo": repo, "pilha": pilha, "rep": rep, "pasta": str(d), "segundos": round(dur, 1),
                 "skill_commit": sh(["git", "-C", str(SKILL), "rev-parse", "--short", "HEAD"]).stdout.strip(),
                 "repo_commit": sh(["git", "-C", str(SRC / repo), "rev-parse", "--short", "HEAD"]).stdout.strip()}
    try:
        j = json.loads(saida)
        res.update({k: j.get(k) for k in ("total_cost_usd", "num_turns", "session_id", "is_error", "subtype")})
        res["modelUsage"] = j.get("modelUsage")
        res["fim"] = (j.get("result") or "")[-400:]
    except (json.JSONDecodeError, TypeError):
        res["erro"] = (erro or "")[-800:] + " | " + (saida or "")[-800:]
    internas = [json.loads(l) for l in log.read_text(encoding="utf-8").splitlines()] if log.exists() else []
    res["internas"] = {"chamadas": len(internas),
                       "total_cost_usd": round(sum(i.get("total_cost_usd") or 0 for i in internas), 6),
                       "modelos": sorted({m for i in internas for m in (i.get("modelUsage") or {})})}
    res["custo_total_usd"] = round((res.get("total_cost_usd") or 0) + res["internas"]["total_cost_usd"], 6)
    res.update(medir(d))
    (BASE / "resultados").mkdir(exist_ok=True)
    (BASE / "resultados" / f"{repo}-{pilha}-{rep}.json").write_text(json.dumps(res, ensure_ascii=False, indent=1),
                                                                     encoding="utf-8")
    return res


def medir(d: Path) -> dict:
    m: dict = {}
    arq = d / ARQ
    if not (arq / "workspace.dsl").exists():
        return {"mapa": False}
    m["mapa"] = True
    q = sh([PY, str(SKILL / "scripts" / "qualidade.py"), "--arq", str(arq), "--repo", str(d), "--sem-gate"],
           timeout=600)
    try:
        jq = json.loads(q.stdout)
        m["qualidade_total"] = jq.get("total")
        m["componentes"] = jq.get("componentes")
    except json.JSONDecodeError:
        m["qualidade_erro"] = (q.stderr or q.stdout)[-400:]
    teste = d / "tests" / "test_arquitetura_cobertura.py"
    if not teste.exists():
        cand = list(d.rglob("test_arquitetura_cobertura.py"))
        teste = cand[0] if cand else None
    if teste:
        t = sh([PY, "-m", "pytest", "-q", "-p", "no:cacheprovider", "--noconftest", str(teste)], cwd=d, timeout=600)
        m["cobertura"] = t.stdout.strip().splitlines()[-1] if t.stdout.strip() else t.stderr[-300:]
        m["cobertura_ok"] = t.returncode == 0
    m["explorador"] = (arq / "explorador" / "index.html").exists()
    return m


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repos", default="chi,click,axios")
    ap.add_argument("--pilhas", default="sonnet,haiku")
    ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--paralelo", type=int, default=3)
    ap.add_argument("--timeout", type=int, default=5400)
    ap.add_argument("--so", default="", help="só estas rodadas, ex.: chi-sonnet-1")
    a = ap.parse_args()
    corridas = [(r, p, k) for r in a.repos.split(",") for p in a.pilhas.split(",") for k in range(1, a.reps + 1)]
    if a.so:
        corridas = [c for c in corridas if f"{c[0]}-{c[1]}-{c[2]}" in a.so.split(",")]
    corridas = [c for c in corridas if not (BASE / "resultados" / f"{c[0]}-{c[1]}-{c[2]}.json").exists()]
    random.Random(20261110).shuffle(corridas)
    with cf.ThreadPoolExecutor(a.paralelo) as ex:
        fut = {ex.submit(rodar, *c, a.timeout): c for c in corridas}
        for f in cf.as_completed(fut):
            c = fut[f]
            try:
                r = f.result()
                print(f"{c}: US$ {r.get('total_cost_usd')} q={r.get('qualidade_total')} cov={r.get('cobertura_ok')} "
                      f"{r.get('segundos')} s", flush=True)
            except Exception as e:  # noqa: BLE001
                print(f"{c}: ERRO {e!r}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
