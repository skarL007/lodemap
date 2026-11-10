"""Idioma do terminal (pt | en): UM só lugar para a regra, usado por lodemap/ e scripts/.

Ordem de decisão:
  1. LODEMAP_IDIOMA (pt|en) vence;
  2. o "idioma" do lodemap.json do mapa que o comando aponta (--repo/--arq), registrado com `usar_mapa()`;
  3. português.

O lançamento é em português: o inglês existe, mas só aparece quando pedido (passo 1 ou 2). O idioma do sistema não
decide mais; `do_sistema()` fica para um lançamento em inglês. Só biblioteca padrão, sem efeito ao importar.
"""
from __future__ import annotations

import json
import locale
import os
from pathlib import Path

IDIOMAS = ("pt", "en")
_mapa: Path | None = None


def _valido(valor) -> str | None:
    v = str(valor or "").strip().lower()
    return v if v in IDIOMAS else None


def usar_mapa(arq: str | Path | None) -> None:
    """Registra a pasta do mapa (a que tem o lodemap.json) para a regra 2; None esquece."""
    global _mapa
    _mapa = Path(arq) if arq else None


def do_mapa(arq: str | Path | None) -> str | None:
    """O "idioma" do lodemap.json dessa pasta, ou None se não houver mapa legível ou o valor não for pt|en."""
    if not arq:
        return None
    try:
        cfg = json.loads((Path(arq) / "lodemap.json").read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return None
    return _valido(cfg.get("idioma")) if isinstance(cfg, dict) else None


def _codigo_do_sistema() -> str:
    """Código de idioma do sistema (ex.: 'pt_BR', 'en-US'), vazio se nada indicar."""
    for nome in ("LC_ALL", "LC_MESSAGES", "LANGUAGE", "LANG"):
        v = os.environ.get(nome, "").strip()
        if v and v not in ("C", "POSIX"):
            return v.split(":")[0]
    if os.name == "nt":
        try:
            import ctypes  # noqa: PLC0415
            buf = ctypes.create_unicode_buffer(85)
            if ctypes.windll.kernel32.GetUserDefaultLocaleName(buf, 85):
                return buf.value
        except (AttributeError, OSError, ValueError):
            pass
    try:
        return locale.getlocale()[0] or ""
    except (ValueError, TypeError):
        return ""


def do_sistema() -> str | None:
    codigo = _codigo_do_sistema().lower()
    if not codigo:
        return None
    return "pt" if codigo.startswith(("pt", "portuguese")) else "en"


def idioma(arq: str | Path | None = None) -> str:
    """'pt' ou 'en' pela regra acima. `arq` (opcional) vale como o mapa dessa chamada; senão, o de `usar_mapa()`."""
    return _valido(os.environ.get("LODEMAP_IDIOMA")) or do_mapa(arq or _mapa) or "pt"


def t(pt: str, en: str, arq: str | Path | None = None) -> str:
    """O texto no idioma escolhido."""
    return pt if idioma(arq) == "pt" else en


def opcao(en: str, pt: str) -> tuple[str, str]:
    """Strings de uma opção do argparse (`--profile`, `--perfil`) com a do idioma ativo primeiro, para o --help."""
    return (pt, en) if idioma() == "pt" else (en, pt)
