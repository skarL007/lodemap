"""Experimento com e sem mapa: o mesmo agente responde as mesmas perguntas de navegação em duas cópias do repositório.

Braço A: cópia com docs/architecture (o mapa do Lodemap) e um parágrafo no prompt de sistema que aponta para ele, o
mesmo texto que o Lodemap sugere colocar no CLAUDE.md. Braço B: mesma cópia sem docs/architecture e sem o parágrafo.
Todo o resto é igual: modelo, esforço, ferramentas (Read, Grep, Glob), sem MCP, sem settings nem hooks do usuário,
sem sessão persistida, resposta pela ferramenta de saída estruturada.

Só o CLI oficial do Claude Code, pela assinatura (nunca a API). Cada execução grava o JSON bruto do CLI em
resultados/brutos/<tarefa>-<braço>-<rep>.json; execuções já gravadas são puladas, então dá para retomar.

Uso:
  python rodar.py preparar                     # cria as cópias em --base (padrão F:/lodemap-exp)
  python rodar.py rodar [--reps 3] [--tarefas C1,A1] [--paralelo 3] [--modelo sonnet] [--esforco medium]
                        [--saida resultados] [--seed 20261110]
"""
from __future__ import annotations

import argparse
import io
import json
import os
import random
import shutil
import subprocess
import sys
import tarfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

AQUI = Path(__file__).resolve().parent
TAREFAS = json.loads((AQUI / "tarefas.json").read_text(encoding="utf-8"))

BASE_SISTEMA = (
    "You are answering a code-navigation question about the repository in the current working directory. "
    "Use the tools to inspect the code before answering. In the structured answer, list repository-relative paths "
    "of the source files that answer the question (forward slashes, no leading ./), most important first, and give "
    "a short justification. Do not list test files or documentation unless the question asks for them."
)
PONTEIRO_MAPA = (
    "\n\nArchitecture map: this repository keeps a C4 architecture map in docs/architecture/structurizr/. "
    "model/componentes-*.dsl lists every component with its source path (property \"codigo\") and a one-sentence "
    "description; model/relacoes-componentes.dsl lists which component uses which. Read these first to locate the "
    "code, then confirm in the source files."
)
SCHEMA = {
    "type": "object",
    "properties": {
        "arquivos": {"type": "array", "items": {"type": "string"}},
        "justificativa": {"type": "string"},
    },
    "required": ["arquivos", "justificativa"],
}


def copia(base: Path, repo: str, braco: str) -> Path:
    return base / f"{repo}-{braco}"


def preparar(base: Path) -> None:
    base.mkdir(parents=True, exist_ok=True)
    for nome, r in TAREFAS["repos"].items():
        dados = subprocess.run(["git", "-C", r["origem"], "archive", "--format=tar", r["ref"]],
                               capture_output=True, check=True).stdout
        for braco in ("A", "B"):
            destino = copia(base, nome, braco)
            if destino.exists():
                print(f"já existe: {destino}")
                continue
            with tarfile.open(fileobj=io.BytesIO(dados)) as t:
                t.extractall(destino, filter="data")
            if braco == "B":
                shutil.rmtree(destino / r["mapa"])
            print(f"pronto: {destino}")


def comando(modelo: str, esforco: str, braco: str) -> list[str]:
    exe = os.environ.get("LODEMAP_CLAUDE") or shutil.which("claude") or "claude"
    sistema = BASE_SISTEMA + (PONTEIRO_MAPA if braco == "A" else "")
    return [exe, "-p", "--model", modelo, "--effort", esforco, "--output-format", "json",
            "--no-session-persistence", "--tools", "Read,Grep,Glob", "--allowedTools", "Read,Grep,Glob",
            "--strict-mcp-config", "--setting-sources", "", "--append-system-prompt", sistema,
            "--json-schema", json.dumps(SCHEMA)]


def uma(base: Path, saida: Path, t: dict, braco: str, rep: int, modelo: str, esforco: str) -> str:
    arq = saida / "brutos" / f"{t['id']}-{braco}-{rep}.json"
    if arq.exists():
        return f"pulado {arq.name}"
    cwd = copia(base, t["repo"], braco)
    t0 = time.time()
    try:
        r = subprocess.run(comando(modelo, esforco, braco), input=t["pergunta"], capture_output=True, text=True,
                           encoding="utf-8", cwd=str(cwd), timeout=900)
        bruto = {"rc": r.returncode, "stdout": r.stdout, "stderr": r.stderr[-2000:]}
    except subprocess.TimeoutExpired:
        bruto = {"rc": None, "stdout": "", "stderr": "timeout 900 s"}
    bruto.update(tarefa=t["id"], braco=braco, rep=rep, modelo=modelo, esforco=esforco,
                 seg=round(time.time() - t0, 1), iniciado=time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(t0)))
    arq.parent.mkdir(parents=True, exist_ok=True)
    arq.write_text(json.dumps(bruto, ensure_ascii=False, indent=1), encoding="utf-8")
    return f"{arq.name} rc={bruto['rc']} {bruto['seg']} s"


def rodar(a) -> None:
    base, saida = Path(a.base), AQUI / a.saida
    escolhidas = set(a.tarefas.split(",")) if a.tarefas else None
    fila = [(t, braco, rep) for t in TAREFAS["tarefas"] if not escolhidas or t["id"] in escolhidas
            for rep in range(1, a.reps + 1) for braco in ("A", "B")]
    random.Random(a.seed).shuffle(fila)  # braços intercalados no tempo: limite de uso e cache não favorecem um lado
    print(f"{len(fila)} execuções, paralelo {a.paralelo}, modelo {a.modelo} {a.esforco}", flush=True)
    with ThreadPoolExecutor(max_workers=a.paralelo) as ex:
        for msg in ex.map(lambda x: uma(base, saida, *x, a.modelo, a.esforco), fila):
            print(msg, flush=True)


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("acao", choices=["preparar", "rodar"])
    ap.add_argument("--base", default="F:/lodemap-exp")
    ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--tarefas")
    ap.add_argument("--paralelo", type=int, default=3)
    ap.add_argument("--modelo", default="sonnet")
    ap.add_argument("--esforco", default="medium")
    ap.add_argument("--saida", default="resultados")
    ap.add_argument("--seed", type=int, default=20261110)
    a = ap.parse_args()
    if a.acao == "preparar":
        preparar(Path(a.base))
    else:
        rodar(a)
    return 0


if __name__ == "__main__":
    sys.exit(main())
