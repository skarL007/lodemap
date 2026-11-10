"""Cria o mapa de arquitetura (Structurizr + explorador + leitor + métricas) num repositório.

Uso:
  python novo_mapa.py --repo <raiz do repositório> --projeto "Nome" [--descricao "..."]
                      [--raiz-codigo src] [--modulos "src/*.py,src/*/"] [--ignorar "**/*_test.go"] [--destino docs/architecture/structurizr]
                      [--testes tests] [--github https://github.com/dono/repo] [--ramo main]
                      [--porta-lite 8790] [--porta-explorador 8791] [--idioma pt|en] [--forcar]

Copia templates/structurizr para <repo>/<destino> e templates/tests para <repo>/<testes>, trocando os marcadores
{{PROJETO}}, {{DESCRICAO}}, {{RAIZ_CODIGO}}, {{MODULOS_JSON}}, {{IGNORAR_JSON}}, {{REPO_GITHUB}}, {{REPO_BLOB}},
{{IDIOMA}}, {{ARQ_REL}}, {{PORTA_LITE}}, {{PORTA_EXPLORADOR}} e {{DATA}}. Não sobrescreve arquivo existente sem --forcar. Só usa a biblioteca padrão.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from datetime import date
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
TEMPLATES = SKILL / "templates"
TEXTO = {".dsl", ".json", ".md", ".py", ".ps1", ".html", ".groovy", ".gitignore"}


# Família de linguagem -> extensões. Python fica de fora: é o padrão antigo (arquivos da raiz + pastas).
FAMILIAS = {
    "javascript": (".js", ".mjs", ".cjs", ".jsx", ".ts", ".tsx"),
    "go": (".go",),
    "rust": (".rs",),
    "java": (".java",),
    "kotlin": (".kt",),
    "csharp": (".cs",),
    "c": (".c", ".h", ".cc", ".cpp", ".hpp"),
}
_PULAR = {"__pycache__", "node_modules", "dist", "build", "target", "vendor"}
_EXT_CODIGO = {".py"} | {e for exts in FAMILIAS.values() for e in exts}


def _tem_codigo(pasta: Path, repo: Path) -> bool:
    """A pasta tem algum arquivo de código (extensões conhecidas), fora das pastas de dependência e das ocultas?"""
    for p in pasta.rglob("*"):
        if (p.suffix.lower() in _EXT_CODIGO and p.is_file()
                and not any(x in _PULAR or x.startswith(".") for x in p.relative_to(repo).parts)):
            return True
    return False


def detectar_raiz(repo: Path) -> str:
    """Raiz do código quando o dono não passou --raiz-codigo.

    A primeira pasta convencional que tem código; se nenhuma tem e o repositório tem código fora delas (Go e muita
    biblioteca guardam os arquivos na raiz), a raiz do código é a do repositório (""). Repositório ainda sem código
    fica com "src", como sempre foi.
    """
    for nome in ("app", "src", "lib", "backend", "server"):
        if (repo / nome).is_dir() and _tem_codigo(repo / nome, repo):
            return nome
    return "" if _tem_codigo(repo, repo) else "src"


# Família dominante -> globs de "ignorar" escritos no lodemap.json novo: o que mora ao lado do código e não é módulo.
# Go: testes, e as pastas que o próprio `go build` ignora (nome começado em "_" e `testdata`). Linguagem fora da
# tabela (Rust, Java, ...) começa com lista vazia. O dono edita a lista no lodemap.json.
IGNORAR_PADRAO = {
    "go": ["**/*_test.go", "**/_*/**", "**/testdata/**"],
    "javascript": ["**/*.test.*", "**/*.spec.*"],
    "python": ["**/test_*.py", "**/*_test.py", "**/conftest.py"],
}
# Com o código na raiz do repositório, o padrão do Python (`*/`) casaria toda pasta: estas não são módulos.
IGNORAR_RAIZ_PYTHON = ["docs", "tests", "test", "examples"]


def globs_padrao(repo: Path, raiz: str) -> list[str]:
    """Globs de módulo quando o dono não passou --modulos: pela linguagem que domina a raiz do código.

    Python (ou raiz vazia) mantém o padrão `raiz/*.py` + `raiz/*/`. Nas outras linguagens um módulo é um arquivo, em
    qualquer profundidade: `raiz/**/*.<ext>` para cada extensão da família dominante que tem arquivo.
    """
    return padroes_da_linguagem(repo, raiz)[0]


def ignorar_padrao(repo: Path, raiz: str) -> list[str]:
    """Globs de "ignorar" quando o dono não passou --ignorar: pela mesma linguagem dominante dos globs padrão."""
    return padroes_da_linguagem(repo, raiz)[1]


def padroes_da_linguagem(repo: Path, raiz: str, fora: tuple[str, ...] = ()) -> tuple[list[str], list[str]]:
    """(globs de módulo, globs de ignorar) da linguagem dominante da raiz do código; uma só varredura.

    `raiz` vazia é a raiz do repositório: os globs saem sem prefixo (`**/*.go`). `fora`: pastas (posix, relativas ao
    repositório) que não contam na varredura, por exemplo a pasta do próprio mapa, que tem scripts em Python.
    """
    conta: dict[str, int] = {}
    base = repo / raiz
    fora = tuple(f.strip("/") + "/" for f in fora if f.strip("/"))
    if base.is_dir():
        for p in base.rglob("*"):
            rel = p.relative_to(repo)
            if (p.is_file() and not any(x in _PULAR or x.startswith(".") for x in rel.parts)
                    and not (fora and (rel.as_posix() + "/").startswith(fora))):
                conta[p.suffix.lower()] = conta.get(p.suffix.lower(), 0) + 1
    total = {f: sum(conta.get(e, 0) for e in exts) for f, exts in FAMILIAS.items()}
    familia = max(total, key=total.get)
    pre = f"{raiz}/" if raiz else ""
    if total[familia] == 0 or conta.get(".py", 0) >= total[familia]:
        return [f"{pre}*.py", f"{pre}*/"], list(IGNORAR_PADRAO["python"]) + ([] if raiz else list(IGNORAR_RAIZ_PYTHON))
    return [f"{pre}**/*{e}" for e in FAMILIAS[familia] if conta.get(e)], list(IGNORAR_PADRAO.get(familia, []))


def copiar(origem: Path, destino: Path, trocas: dict[str, str], forcar: bool,
           recem: set | None = None) -> tuple[list, list]:
    """Copia trocando os marcadores. `recem`: arquivos criados nesta execução, que a camada do idioma pode trocar."""
    criados, pulados = [], []
    for f in sorted(origem.rglob("*")):
        if f.is_dir() or "__pycache__" in f.parts:
            continue
        alvo = destino / f.relative_to(origem)
        if alvo.exists() and not forcar and alvo not in (recem or set()):
            pulados.append(alvo)
            continue
        alvo.parent.mkdir(parents=True, exist_ok=True)
        if f.suffix in TEXTO or f.name in TEXTO:
            bruto = f.read_bytes()
            bom = bruto.startswith(b"\xef\xbb\xbf")
            texto = bruto.decode("utf-8-sig")
            for k, v in trocas.items():
                texto = texto.replace("{{" + k + "}}", v)
            alvo.write_bytes((b"\xef\xbb\xbf" if bom else b"") + texto.encode("utf-8"))
        else:
            shutil.copy2(f, alvo)
        criados.append(alvo)
    return criados, pulados


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repo", required=True)
    ap.add_argument("--projeto", required=True)
    ap.add_argument("--descricao", default="")
    ap.add_argument("--raiz-codigo")
    ap.add_argument("--modulos", help="globs separados por vírgula; terminado em / casa pastas")
    ap.add_argument("--ignorar", help="globs de 'ignorar' separados por vírgula (candidatos que não são módulos, ex. "
                                      "'**/*_test.go'); substitui o padrão da linguagem; vazio = nenhum")
    ap.add_argument("--destino", default="docs/architecture/structurizr")
    ap.add_argument("--testes", default="tests")
    ap.add_argument("--github", default="")
    ap.add_argument("--ramo", default="main")
    ap.add_argument("--porta-lite", type=int, default=8790, help="porta do Structurizr Lite (troque se o projeto já usa 8790)")
    ap.add_argument("--porta-explorador", type=int, default=8791, help="porta do servidor do explorador (padrão 8791)")
    ap.add_argument("--idioma", choices=("pt", "en"), default="pt",
                    help="idioma das saídas geradas e do texto do modelo (padrão pt; en disponível)")
    ap.add_argument("--forcar", action="store_true")
    a = ap.parse_args(argv)
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

    repo = Path(a.repo).resolve()
    # "." e "" querem dizer a raiz do repositório
    raiz = (detectar_raiz(repo) if a.raiz_codigo is None else a.raiz_codigo).strip("/")
    raiz = "" if raiz == "." else raiz
    if a.modulos:
        modulos = [m.strip() for m in a.modulos.split(",")]
        padrao_ignorar: list[str] = []  # --modulos explícito: o dono manda nos módulos, nada é excluído sem ele pedir
    else:
        modulos, padrao_ignorar = padroes_da_linguagem(repo, raiz, fora=(a.destino, a.testes) if not raiz else ())
    ignorar = [g.strip() for g in a.ignorar.split(",") if g.strip()] if a.ignorar is not None else padrao_ignorar
    github = a.github.rstrip("/")
    trocas = {
        "PROJETO": a.projeto.replace('"', "'"),
        "DESCRICAO": (a.descricao or (f"Architecture of {a.projeto}." if a.idioma == "en"
                                     else f"Arquitetura de {a.projeto}.")).replace('"', "'"),
        "RAIZ_CODIGO": raiz,
        "MODULOS_JSON": json.dumps(modulos, ensure_ascii=False),
        "IGNORAR_JSON": json.dumps(ignorar, ensure_ascii=False),
        "REPO_GITHUB": github,
        # O DSL não aceita propriedade vazia: "-" quer dizer "sem link" para o enriquecer.groovy.
        "REPO_BLOB": f"{github}/blob/{a.ramo}/" if github else "-",
        "ARQ_REL": a.destino.strip("/"),
        "IDIOMA": a.idioma,
        "DATA": date.today().isoformat(),
        "PORTA_LITE": str(a.porta_lite),
        "PORTA_EXPLORADOR": str(a.porta_explorador),
    }
    c1, p1 = copiar(TEMPLATES / "structurizr", repo / a.destino, trocas, a.forcar)
    c2, p2 = copiar(TEMPLATES / "tests", repo / a.testes, trocas, a.forcar)
    # Camada do idioma: templates/i18n/<idioma>/ tem as versões traduzidas dos textos iniciais (docs, ADR modelo).
    camada = TEMPLATES / "i18n" / a.idioma
    if (camada / "structurizr").is_dir():
        c3, _ = copiar(camada / "structurizr", repo / a.destino, trocas, a.forcar, set(c1))
        c1 += [c for c in c3 if c not in c1]
    print(f"{len(c1) + len(c2)} arquivos criados em {repo}")
    for p in p1 + p2:
        print(f"  já existia, mantido: {p.relative_to(repo)}")
    print(f"Próximo passo: python {SKILL / 'scripts' / 'inventario.py'} --repo \"{repo}\" --arq {a.destino}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
