#!/usr/bin/env python3
"""Lodemap: instala (opt-in) os ganchos do git que atualizam a arquitetura a cada checkpoint.

Equivalente multiplataforma (Windows, Linux e macOS) do instalar-gancho.ps1: Python 3.10+, só a biblioteca padrão.
O instalar-gancho.ps1 continua existindo como invólucro fino que chama este arquivo.

Grava em .git/hooks (ou no core.hooksPath) um post-commit e um post-merge que chamam o lodemap_gancho_lanca.py. O
post-commit só dispara quando o commit toca os globs de código do lodemap.json ou a pasta da arquitetura; o
post-merge dispara quando há o que regenerar. Em ambos, o atualizar.py roda em segundo plano, em modo incremental e
sem o site estático, sem bloquear o git; o log fica em .lodemap/ultimo-atualizar.log. Nunca roda sozinho: quem instala
é o dono do repositório. Gancho que já existe e não é deste script não é sobrescrito (use --forcar para trocar).

O lançador é copiado para a pasta dos ganchos (fora do versionamento) e só repassa a chamada se os scripts do
repositório ainda tiverem o hash aprovado agora: um git pull que troque os scripts não ganha execução de código.

Uso:
  python scripts/instalar_gancho.py [--python <exe>] [--ferramentas <pasta>] [--remover] [--forcar]

Mapeamento dos parâmetros do instalar-gancho.ps1 para as flags:

  -Python <exe>          --python <exe>          o Python que o gancho usa (padrão: o que roda este script)
  -Ferramentas <pasta>   --ferramentas <pasta>   env STRUCTURIZR_FERRAMENTAS, senão ~/.structurizr
  -Remover               --remover               tira os ganchos instalados por este script (e só eles)
  -Forcar                --forcar                sobrescreve um gancho que já existe e não é deste script

O arquivo do gancho é gravado com LF (o git o executa com sh, inclusive no Windows) e, fora do Windows, com chmod +x.
Código de saída: 0; 1 se a pasta não é um repositório git ou se a aprovação do lançador falhou.
"""
from __future__ import annotations

import argparse
import os
import shlex
import shutil
import stat
import subprocess
import sys
from pathlib import Path

MARCA = "# lodemap"
TIPOS = ("post-commit", "post-merge")
LANCA = "lodemap_gancho_lanca.py"
PIN = "lodemap-gancho.pin.json"

# Todo texto que o usuário lê está aqui (um lugar só para traduzir).
MSG = {
    "nao_git": "{arq} não está num repositório git; nada instalado.",
    "removido": "removido: {alvo}",
    "instalado": "instalado: {alvo}",
    "alheio": "AVISO: {alvo} já existe e não é da lodemap; não mexi (use --forcar para trocar).",
    "aprovacao": "ERRO: não consegui aprovar o lançador ({motivo}).",
    "fim": "Log de cada atualização: {log}. Para tirar: --remover.",
    "gancho_linha2": "atualiza a arquitetura em segundo plano (instalado por instalar_gancho.py)",
}


def _git(arq: Path, *args: str) -> str | None:
    try:
        r = subprocess.run(["git", "-C", str(arq), *args], capture_output=True, text=True, encoding="utf-8")
    except OSError:
        return None
    return r.stdout.strip() if r.returncode == 0 else None


def pasta_dos_ganchos(arq: Path) -> Path | None:
    """core.hooksPath se houver (relativo = à raiz do repositório, como o git faz); senão a pasta padrão do git."""
    topo = _git(arq, "rev-parse", "--show-toplevel")
    if topo is None:
        return None
    configurado = _git(arq, "config", "core.hooksPath")
    if configurado:
        p = Path(os.path.expanduser(configurado))
        return p if p.is_absolute() else Path(topo) / p
    padrao = _git(arq, "rev-parse", "--git-path", "hooks")
    if not padrao:
        return None
    p = Path(padrao)
    return p if p.is_absolute() else arq / p  # --git-path é relativo à pasta de onde o git foi chamado (arq)


def _caminho_sh(p: str | Path) -> str:
    """Caminho para dentro do sh do gancho: barras normais no Windows (o sh do git não lê contrabarra)."""
    s = str(p)
    return s.replace("\\", "/") if os.name == "nt" else s


def corpo_do_gancho(tipo: str, python: str, lanca: Path, ferramentas: str) -> str:
    return (f"#!/bin/sh\n{MARCA}: {MSG['gancho_linha2']}\n"
            f"{shlex.quote(_caminho_sh(python))} {shlex.quote(_caminho_sh(lanca))} {tipo} "
            f"--ferramentas {shlex.quote(_caminho_sh(ferramentas))} >/dev/null 2>&1 || true\nexit 0\n")


def _eh_nosso(alvo: Path) -> bool:
    try:
        return MARCA in alvo.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False


def instalar(arq: Path, scripts: Path, python: str, ferramentas: str, remover: bool = False, forcar: bool = False) -> int:
    hooks = pasta_dos_ganchos(arq)
    if hooks is None:
        print(MSG["nao_git"].format(arq=arq), file=sys.stderr)
        return 1
    hooks.mkdir(parents=True, exist_ok=True)
    lanca_copia = hooks / LANCA

    if not remover:
        # O lançador mora na pasta dos ganchos e só repassa a chamada se os scripts ainda tiverem o hash aprovado agora.
        shutil.copyfile(scripts / LANCA, lanca_copia)
        r = subprocess.run([python, str(lanca_copia), "--aprovar", str(scripts)], capture_output=True, text=True)
        if r.returncode != 0:
            print(MSG["aprovacao"].format(motivo=(r.stderr or r.stdout or f"código {r.returncode}").strip()),
                  file=sys.stderr)
            return 1

    for tipo in TIPOS:
        alvo = hooks / tipo
        nosso = alvo.is_file() and _eh_nosso(alvo)
        if remover:
            if nosso:
                alvo.unlink()
                print(MSG["removido"].format(alvo=alvo))
            continue
        if alvo.exists() and not nosso and not forcar:
            print(MSG["alheio"].format(alvo=alvo), file=sys.stderr)
            continue
        # bytes: o gancho tem de sair com LF em qualquer sistema (o sh não lê CRLF)
        alvo.write_bytes(corpo_do_gancho(tipo, python, lanca_copia, ferramentas).encode("utf-8"))
        if os.name != "nt":
            alvo.chmod(alvo.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        print(MSG["instalado"].format(alvo=alvo))

    if remover:
        lanca_copia.unlink(missing_ok=True)
        (hooks / PIN).unlink(missing_ok=True)
    else:
        print(MSG["fim"].format(log=arq / ".lodemap" / "ultimo-atualizar.log"))
    return 0


def parse_args(argv=None, env=None) -> argparse.Namespace:
    env = os.environ if env is None else env
    ferr = env.get("STRUCTURIZR_FERRAMENTAS") or str(Path.home() / ".structurizr")
    ap = argparse.ArgumentParser(prog="instalar_gancho.py", description=__doc__.splitlines()[0])
    ap.add_argument("--python", default=sys.executable, help="executável do Python que o gancho usa (padrão: %(default)s)")
    ap.add_argument("--ferramentas", default=ferr, help="pasta do Structurizr CLI que o gancho passa ao atualizar.py "
                                                       "(o gancho roda sem as variáveis da sua sessão; padrão: %(default)s)")
    ap.add_argument("--remover", action="store_true", help="tira os ganchos instalados por este script (e só eles)")
    ap.add_argument("--forcar", action="store_true", help="sobrescreve um gancho que já existe e não é deste script")
    return ap.parse_args(argv)


def main(argv=None, scripts: Path | None = None) -> int:
    for fluxo in (sys.stdout, sys.stderr):
        if hasattr(fluxo, "reconfigure") and not fluxo.isatty():
            fluxo.reconfigure(encoding="utf-8", errors="replace")
    a = parse_args(argv)
    scripts = (scripts or Path(__file__).resolve().parent).resolve()
    return instalar(scripts.parent, scripts, a.python, a.ferramentas, a.remover, a.forcar)


if __name__ == "__main__":
    sys.exit(main())
