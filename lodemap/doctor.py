"""Diagnóstico do ambiente (python -m lodemap doctor): somente leitura, 0 tokens, sem rede.

Cada item vira {nome, estado, detalhe, acao} com estado ok | aviso | falha. Só `falha` faz o comando sair com 1.
"""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

from lodemap import RAIZ, instalador, permissao

PY_MINIMO = (3, 11)
INSTALAR = "python -m lodemap instalar --perfil padrao --aplicar"
NOME_CLI_WINDOWS = ("structurizr.bat",)
NOME_CLI_OUTROS = ("structurizr.sh", "structurizr", "structurizr-cli")


def _item(nome: str, estado: str, detalhe: str, acao: str = "") -> dict:
    return {"nome": nome, "estado": estado, "detalhe": detalhe, "acao": acao}


def _python() -> dict:
    v = sys.version_info
    atual = f"{v.major}.{v.minor}.{v.micro}"
    if (v.major, v.minor) >= PY_MINIMO:
        return _item("python", "ok", atual)
    return _item("python", "falha", f"{atual} (precisa de 3.11 ou mais novo)", "instale o Python 3.11 ou 3.12")


def _no_path(nome: str, exe: str, estado_falta: str, acao: str) -> dict:
    achado = shutil.which(exe)
    if achado:
        return _item(nome, "ok", achado)
    return _item(nome, estado_falta, "não está no PATH", acao)


def _cli_em(pasta: Path) -> Path | None:
    for nome in (NOME_CLI_WINDOWS if os.name == "nt" else NOME_CLI_OUTROS):
        c = pasta / nome
        if c.is_file():
            return c
    return None


def achar_structurizr() -> Path | None:
    """Mesma ordem de templates/structurizr/scripts/atualizar.py: STRUCTURIZR_CLI, ~/.structurizr/cli, PATH."""
    valor = os.environ.get("STRUCTURIZR_CLI", "")
    if valor:
        p = Path(valor).expanduser()
        achado = p if p.is_file() else (_cli_em(p) if p.is_dir() else None)
        if achado:
            return achado
    achado = _cli_em(_ferramentas() / "cli")
    if achado:
        return achado
    for nome in (NOME_CLI_WINDOWS if os.name == "nt" else NOME_CLI_OUTROS):
        a = shutil.which(nome)
        if a:
            return Path(a)
    return None


def _ferramentas() -> Path:
    return Path(os.environ.get("STRUCTURIZR_FERRAMENTAS") or str(Path.home() / ".structurizr")).expanduser()


def _dot() -> dict:
    """Mesma ordem do atualizar.py: <ferramentas>/graphviz e depois o PATH."""
    base = _ferramentas() / "graphviz"
    if base.is_dir():
        for c in sorted(base.rglob("dot.exe" if os.name == "nt" else "dot")):
            if c.is_file():
                return _item("dot", "ok", str(c))
    achado = shutil.which("dot")
    if achado:
        return _item("dot", "ok", achado)
    return _item("dot", "aviso", f"não está no PATH nem em {base}",
                 "instale o Graphviz (dot); sem ele o site estático opcional pode sair incompleto")


def _structurizr() -> dict:
    p = achar_structurizr()
    if p:
        return _item("structurizr", "ok", str(p))
    return _item("structurizr", "aviso", "Structurizr CLI não encontrado; sem ele não se exporta workspace.json",
                 "baixe structurizr-cli.zip em https://github.com/structurizr/cli/releases e extraia em "
                 "~/.structurizr/cli (ou aponte STRUCTURIZR_CLI)")


def _skill(home: Path) -> dict:
    skill = home / ".claude" / "skills" / "lodemap"
    if skill.exists() and instalador._mesmo(skill, RAIZ):
        return _item("skill", "ok", f"{skill} aponta para {RAIZ}")
    return _item("skill", "aviso", "skill não instalada aqui", INSTALAR)


def _agentes(home: Path) -> dict:
    esperados = sorted(p.name for p in (RAIZ / "agents").glob("lodemap-*.md"))
    faltam = [n for n in esperados if not (home / ".claude" / "agents" / n).is_file()]
    if esperados and not faltam:
        return _item("agentes", "ok", f"{len(esperados)} agentes lodemap-*.md em ~/.claude/agents")
    return _item("agentes", "aviso", f"faltam {len(faltam)} de {len(esperados)}: {', '.join(faltam)}", INSTALAR)


def _repo(repo: Path, arq: str) -> list[dict]:
    repo = repo.resolve()
    mapa = repo / arq / "lodemap.json"
    if mapa.is_file():
        itens = [_item("mapa", "ok", str(mapa))]
    else:
        itens = [_item("mapa", "aviso", f"sem {arq}/lodemap.json em {repo}",
                       "peça o mapa à skill Lodemap ou rode scripts/novo_mapa.py")]
    try:
        c = permissao.ler_consentimento(repo, arq)
    except ValueError as e:
        return itens + [_item("consentimento", "aviso", f"arquivo ilegível ({e})",
                              "python -m lodemap consentir --escopos gerar")]
    if c:
        itens.append(_item("consentimento", "ok", f"escopos {c.get('escopos')} ({c.get('data')})"))
    else:
        itens.append(_item("consentimento", "aviso", "nenhum consentimento gravado",
                           "python -m lodemap consentir --escopos gerar[,modelo]"))
    return itens


def diagnosticar(home: Path, repo: Path | None = None, arq: str = permissao.ARQ_PADRAO) -> list[dict]:
    itens = [
        _python(),
        _no_path("git", "git", "falha", "instale o git e deixe-o no PATH"),
        _no_path("claude", "claude", "aviso",
                 "sem o Claude Code a rota enxuta scripts/descrever.py cai para o agente modelador"),
        _structurizr(),
        _dot(),
        _no_path("java", "java", "aviso", "instale o Java 21; o Structurizr CLI precisa dele"),
        _no_path("node", "node", "aviso", "o verificador usa `node --check`; sem node essa checagem é pulada"),
        _skill(home),
        _agentes(home),
    ]
    if repo is not None:
        itens += _repo(repo, arq)
    return itens
