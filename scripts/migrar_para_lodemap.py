"""Migra uma árvore do antigo structurize-map para o Lodemap: nomes de arquivo, textos e estado local.

Usos:
  python migrar_para_lodemap.py <pasta> [--aplicar]          # plano por padrão; --aplicar grava
  python migrar_para_lodemap.py <pasta> --aplicar --so-estado # só .smap -> .lodemap e o JSON de configuração

Troca, nesta ordem: structurize-map.json -> lodemap.json; caminhos da skill; o nome structurize-map; as variáveis
STRUCTURIZE_* -> LODEMAP_*; smap_diff/smap_gancho; agentes smap-* -> lodemap-*; a pasta de estado .smap -> .lodemap.
"Structurizr" (o formato e a ferramenta de terceiros) não é tocado.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lodemap.idioma import opcao, t  # noqa: E402

TROCAS = [
    ("structurize-map.json", "lodemap.json"),
    ("skills/structurize-map", "skills/lodemap"),
    ("skills\\structurize-map", "skills\\lodemap"),
    ("structurize-map", "lodemap"),
    ("structurize_map", "lodemap"),
    ("STRUCTURIZE_", "LODEMAP_"),
    ("smap_diff", "lodemap_diff"),
    ("smap_gancho", "lodemap_gancho"),
    ("smap-", "lodemap-"),
    (".smap", ".lodemap"),
]
RENOMEAR = {"smap_diff.py": "lodemap_diff.py", "smap_gancho.py": "lodemap_gancho.py",
            "test_smap_diff.py": "test_lodemap_diff.py", "structurize-map.json": "lodemap.json"}
TEXTO = {".py", ".ps1", ".md", ".json", ".dsl", ".html", ".js", ".groovy", ".css", ".toml", ".txt", ".yml", ".yaml", ""}
IGNORAR = {".git", "__pycache__", ".structurizr", "site", "node_modules"}
PROPRIO = Path(__file__).name
_TIPO = {"pasta": "folder", "arquivo": "file", "texto": "text"}  # rótulos só da exibição; os valores do plano não mudam


def arquivos(raiz: Path):
    for p in sorted(raiz.rglob("*")):
        if any(parte in IGNORAR for parte in p.relative_to(raiz).parts) or not p.is_file() or p.name == PROPRIO:
            continue
        yield p


def trocar(texto: str) -> str:
    for a, b in TROCAS:
        texto = texto.replace(a, b)
    return texto


def planejar(raiz: Path, so_estado: bool = False) -> list[tuple[str, Path, Path | None]]:
    ops = []
    for antigo, novo in ((".smap", ".lodemap"),):
        for p in raiz.rglob(antigo):
            if p.is_dir() and not (p.parent / novo).exists():
                ops.append(("pasta", p, p.parent / novo))
    if so_estado:
        for p in raiz.rglob("structurize-map.json"):
            ops.append(("arquivo", p, p.with_name("lodemap.json")))
        return ops
    for p in arquivos(raiz):
        if ".smap" in p.parts:
            continue
        if p.suffix.lower() in TEXTO:
            try:
                t = p.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                t = None
            if t is not None and trocar(t) != t:
                ops.append(("texto", p, None))
        novo_nome = RENOMEAR.get(p.name) or (re.sub(r"^smap-", "lodemap-", p.name) if p.name.startswith("smap-") else None)
        if novo_nome:
            ops.append(("arquivo", p, p.with_name(novo_nome)))
    return ops


def aplicar(ops) -> None:
    for tipo, p, _ in ops:
        if tipo == "texto":
            p.write_text(trocar(p.read_text(encoding="utf-8")), encoding="utf-8")
    for tipo, p, destino in ops:
        if tipo in ("arquivo", "pasta") and p.exists() and not destino.exists():
            p.rename(destino)


def main(argv=None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    ap = argparse.ArgumentParser(description=t("Migra uma árvore do antigo structurize-map para o Lodemap: nomes de "
                                               "arquivo, textos e estado local.",
                                               "Migrate a tree from the old structurize-map to Lodemap: file names, "
                                               "texts and local state."))
    ap.add_argument("pasta", metavar=t("pasta", "folder"), help=t("pasta a migrar", "folder to migrate"))
    ap.add_argument(*opcao("--apply", "--aplicar"), dest="aplicar", action="store_true",
                    help=t("grava as mudanças (sem isto, só mostra o plano)", "write the changes (without it, only shows the plan)"))
    ap.add_argument(*opcao("--state-only", "--so-estado"), dest="so_estado", action="store_true",
                    help=t("só .smap -> .lodemap e o JSON de configuração", "only .smap -> .lodemap and the config JSON"))
    a = ap.parse_args(argv)
    raiz = Path(a.pasta).resolve()
    ops = planejar(raiz, a.so_estado)
    for tipo, p, d in ops:
        print(f"{_TIPO.get(tipo, tipo) if t('pt', 'en') == 'en' else tipo:8} {p.relative_to(raiz)}"
              + (f" -> {d.name}" if d else ""))
    print(t(f"{len(ops)} operações", f"{len(ops)} operations")
          + ("" if a.aplicar else t(" (plano; use --aplicar)", " (plan; use --apply)")))
    if a.aplicar:
        aplicar(ops)
    return 0


if __name__ == "__main__":
    sys.exit(main())
