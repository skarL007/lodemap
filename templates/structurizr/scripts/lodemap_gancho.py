"""Gancho do git (post-commit e post-merge) que atualiza a arquitetura em segundo plano.

Instalado por scripts/instalar_gancho.py (opt-in). Nunca bloqueia o git: decide rápido, dispara um processo
separado e sai. O processo separado roda o atualizar.py (com o mesmo Python que roda este gancho) em modo incremental
(--incremental --sem-site) com o rótulo do checkpoint e grava a saída em .lodemap/ultimo-atualizar.log.

  python lodemap_gancho.py post-commit   # só dispara se o commit tocou os globs de código ou a pasta da arquitetura
                                         # E o lodemap_decidir manda regenerar por scripts agora (cadência, política);
                                         # senão grava a pendência no log e sai, sem chamar modelo
  python lodemap_gancho.py post-merge    # dispara se houver o que regenerar desde a última geração
  python lodemap_gancho.py --executar --checkpoint "rótulo"   # (interno) roda o atualizar.py com trava e log

Só usa a biblioteca padrão.
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
from arq_comum import glob_regex, globs_ignorar, modulo_ignorado  # noqa: E402
ARQ = SCRIPTS.parent
SMAP = ARQ / ".lodemap"
TRAVA = SMAP / "atualizar.lock"
LOG = SMAP / "ultimo-atualizar.log"
FONTES = ("model/", "views/", "metricas/", "adrs/", "workspace.dsl", "lodemap.json")


def git(*args: str) -> str:
    r = subprocess.run(["git", "-C", str(ARQ), *args], capture_output=True, text=True, encoding="utf-8")
    return r.stdout.strip()


def commit_toca_arquitetura() -> bool:
    cfg = json.loads((ARQ / "lodemap.json").read_text(encoding="utf-8-sig"))
    repo = Path(git("rev-parse", "--show-toplevel"))
    rel = ARQ.resolve().relative_to(repo.resolve()).as_posix().rstrip("/") + "/"
    arquivos = git("diff-tree", "--no-commit-id", "--name-only", "-r", "--root", "HEAD").splitlines()
    ignorar = globs_ignorar(cfg)  # arquivo ou pasta que casa "ignorar" não é módulo: commit só dele não toca a arquitetura
    for a in arquivos:
        if a.startswith(rel) and a[len(rel):].startswith(FONTES):
            return True
        for g in cfg.get("modulos", []):
            if g.endswith("/"):
                n = g.rstrip("/").count("/") + 1
                partes = a.split("/")
                if (len(partes) > n and fnmatch.fnmatch("/".join(partes[:n]), g.rstrip("/"))
                        and not modulo_ignorado("/".join(partes[:n]), ignorar)):
                    return True
            elif glob_regex(g).fullmatch(a) and not modulo_ignorado(a, ignorar):
                return True
    return False


def adiar_regeneracao() -> str:
    """Vazio se o gancho deve regenerar por scripts agora; senão, a linha do que está pendente (política do lodemap_decidir)."""
    import lodemap_decidir  # aqui dentro: um erro de importação cai no try do main e não derruba o git
    dec = lodemap_decidir.decidir(ARQ, usar_skill=False)
    if dec["acao"] == "scripts":
        return ""
    return lodemap_decidir.resumo(dec, lodemap_decidir._en(ARQ))


def disparar(checkpoint: str, ferramentas: str = "") -> None:
    SMAP.mkdir(parents=True, exist_ok=True)
    flags = 0
    if os.name == "nt":
        flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW
    extra = ["--ferramentas", ferramentas] if ferramentas else []
    subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "--executar", "--checkpoint", checkpoint, *extra],
                     cwd=str(ARQ), stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                     creationflags=flags, start_new_session=(os.name != "nt"), close_fds=True)


def comando_atualizar(checkpoint: str, ferramentas: str = "") -> list[str]:
    """O comando que roda a atualização: atualizar.py com o Python deste gancho (Windows, Linux e macOS)."""
    cmd = [sys.executable, str(SCRIPTS / "atualizar.py"), "--incremental", "--sem-site",
           "--checkpoint", checkpoint, "--python", sys.executable]
    if ferramentas:
        cmd += ["--ferramentas", ferramentas]
    return cmd


def executar(checkpoint: str, ferramentas: str = "") -> int:
    SMAP.mkdir(parents=True, exist_ok=True)
    if TRAVA.exists() and time.time() - TRAVA.stat().st_mtime < 1800:
        with LOG.open("a", encoding="utf-8") as f:
            f.write(f"{datetime.now():%Y-%m-%d %H:%M:%S} outra atualização em curso; pulei ({checkpoint})\n")
        return 0
    TRAVA.write_text(str(os.getpid()), encoding="utf-8")
    try:
        cmd = comando_atualizar(checkpoint, ferramentas)
        with LOG.open("w", encoding="utf-8") as f:
            f.write(f"{datetime.now():%Y-%m-%d %H:%M:%S} checkpoint: {checkpoint}\n")
            f.flush()
            r = subprocess.run(cmd, cwd=str(ARQ), stdout=f, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL)
            f.write(f"\n{datetime.now():%Y-%m-%d %H:%M:%S} fim, código {r.returncode}\n")
        return r.returncode
    finally:
        TRAVA.unlink(missing_ok=True)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("tipo", nargs="?", choices=["post-commit", "post-merge"])
    ap.add_argument("--executar", action="store_true")
    ap.add_argument("--checkpoint", default="")
    ap.add_argument("--ferramentas", default="", help="pasta do Structurizr CLI (gravada pelo instalar_gancho.py)")
    a = ap.parse_args(argv)
    if a.executar:
        return executar(a.checkpoint, a.ferramentas)
    try:
        sha = git("rev-parse", "--short", "HEAD")
        assunto = git("log", "-1", "--format=%s")[:80]
        if a.tipo == "post-commit":
            if not commit_toca_arquitetura():
                return 0
            pendente = adiar_regeneracao()
            if pendente:  # abaixo da cadência, ou pede modelo: o gancho nunca chama modelo nem adia por conta própria
                SMAP.mkdir(parents=True, exist_ok=True)
                with LOG.open("a", encoding="utf-8") as f:
                    f.write(f"{datetime.now():%Y-%m-%d %H:%M:%S} commit {sha}: não regenerei; {pendente}\n")
                return 0
        disparar(f"{a.tipo} {sha}: {assunto}", a.ferramentas)
    except Exception as e:  # o gancho nunca derruba o git
        SMAP.mkdir(parents=True, exist_ok=True)
        with LOG.open("a", encoding="utf-8") as f:
            f.write(f"{datetime.now():%Y-%m-%d %H:%M:%S} gancho falhou: {e!r}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
