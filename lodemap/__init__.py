"""Lodemap: mapa de arquitetura vivo e documentação do projeto (skill do Claude Code) com instalador próprio."""
from __future__ import annotations

from pathlib import Path

__version__ = "0.1.0"

RAIZ = Path(__file__).resolve().parents[1]
PASTA_HOOKS = RAIZ / "hooks"
MARCA = "gerado por lodemap"
