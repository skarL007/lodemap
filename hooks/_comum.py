"""Utilidades dos hooks do Lodemap: só biblioteca padrão, nunca derrubam a sessão (erro vira saída 0 sem decisão)."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

MARCA = "gerado por lodemap"


def entrada() -> dict:
    try:
        return json.loads(sys.stdin.read() or "{}")
    except ValueError:
        return {}


def saida(obj: dict | None = None, codigo: int = 0) -> None:
    if obj:
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
        sys.stdout.write(json.dumps(obj, ensure_ascii=False))
    sys.exit(codigo)


def pasta_config() -> Path:
    """~/.config/lodemap em todos os sistemas (LODEMAP_CONFIG_DIR troca, para testes)."""
    return Path(os.environ.get("LODEMAP_CONFIG_DIR") or Path.home() / ".config" / "lodemap")


def git(cwd: str | None, *args: str) -> str | None:
    if not cwd:
        return None
    try:
        r = subprocess.run(["git", "-C", cwd, *args], capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.SubprocessError):
        return None
    return r.stdout.strip() if r.returncode == 0 and r.stdout.strip() else None
