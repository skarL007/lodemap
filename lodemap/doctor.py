"""Diagnóstico do ambiente (python -m lodemap doctor): somente leitura, 0 tokens, sem rede.
(Environment diagnosis, read-only: 0 tokens, no network. Messages follow `lodemap.idioma`.)

Cada item vira {nome, estado, detalhe, acao} com estado ok | aviso | falha. Só `falha` faz o comando sair com 1.
"""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

from lodemap import RAIZ, instalador, permissao
from lodemap.idioma import t

PY_MINIMO = (3, 11)
NOME_CLI_WINDOWS = ("structurizr.bat",)
NOME_CLI_OUTROS = ("structurizr.sh", "structurizr", "structurizr-cli")


def _instalar() -> str:
    return t("python -m lodemap instalar --perfil padrao --aplicar", "python -m lodemap install --profile padrao --apply")


def _item(nome: str, estado: str, detalhe: str, acao: str = "") -> dict:
    return {"nome": nome, "estado": estado, "detalhe": detalhe, "acao": acao}


def _python() -> dict:
    v = sys.version_info
    atual = f"{v.major}.{v.minor}.{v.micro}"
    if (v.major, v.minor) >= PY_MINIMO:
        return _item("python", "ok", atual)
    return _item("python", "falha", t(f"{atual} (precisa de 3.11 ou mais novo)", f"{atual} (needs 3.11 or newer)"),
                 t("instale o Python 3.11 ou 3.12", "install Python 3.11 or 3.12"))


def _no_path(nome: str, exe: str, estado_falta: str, acao: str) -> dict:
    achado = shutil.which(exe)
    if achado:
        return _item(nome, "ok", achado)
    return _item(nome, estado_falta, t("não está no PATH", "not on PATH"), acao)


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
    return _item("dot", "aviso", t(f"não está no PATH nem em {base}", f"not on PATH nor in {base}"),
                 t("instale o Graphviz (dot); sem ele o site estático opcional pode sair incompleto",
                   "install Graphviz (dot); without it the optional static site may come out incomplete"))


def _structurizr() -> dict:
    p = achar_structurizr()
    if p:
        return _item("structurizr", "ok", str(p))
    return _item("structurizr", "aviso",
                 t("Structurizr CLI não encontrado; sem ele não se exporta workspace.json",
                   "Structurizr CLI not found; without it workspace.json cannot be exported"),
                 t("baixe structurizr-cli.zip em https://github.com/structurizr/cli/releases e extraia em "
                   "~/.structurizr/cli (ou aponte STRUCTURIZR_CLI)",
                   "download structurizr-cli.zip from https://github.com/structurizr/cli/releases and extract it to "
                   "~/.structurizr/cli (or point STRUCTURIZR_CLI at it)"))


def _skill(home: Path) -> dict:
    skill = home / ".claude" / "skills" / "lodemap"
    if skill.exists() and instalador._mesmo(skill, RAIZ):
        return _item("skill", "ok", t(f"{skill} aponta para {RAIZ}", f"{skill} points to {RAIZ}"))
    return _item("skill", "aviso", t("skill não instalada aqui", "skill not installed here"), _instalar())


def _agentes(home: Path) -> dict:
    esperados = sorted(p.name for p in (RAIZ / "agents").glob("lodemap-*.md"))
    faltam = [n for n in esperados if not (home / ".claude" / "agents" / n).is_file()]
    if esperados and not faltam:
        return _item("agentes", "ok", t(f"{len(esperados)} agentes lodemap-*.md em ~/.claude/agents",
                                        f"{len(esperados)} lodemap-*.md agents in ~/.claude/agents"))
    return _item("agentes", "aviso", t(f"faltam {len(faltam)} de {len(esperados)}: {', '.join(faltam)}",
                                       f"{len(faltam)} of {len(esperados)} missing: {', '.join(faltam)}"),
                 _instalar())


def _repo(repo: Path, arq: str) -> list[dict]:
    repo = repo.resolve()
    mapa = repo / arq / "lodemap.json"
    if mapa.is_file():
        itens = [_item("mapa", "ok", str(mapa))]
    else:
        itens = [_item("mapa", "aviso", t(f"sem {arq}/lodemap.json em {repo}", f"no {arq}/lodemap.json in {repo}"),
                       t("peça o mapa à skill Lodemap ou rode scripts/novo_mapa.py",
                         "ask the Lodemap skill for the map or run scripts/novo_mapa.py"))]
    try:
        c = permissao.ler_consentimento(repo, arq)
    except ValueError as e:
        return itens + [_item("consentimento", "aviso", t(f"arquivo ilegível ({e})", f"unreadable file ({e})"),
                              t("python -m lodemap consentir --escopos gerar", "python -m lodemap consent --scopes gerar"))]
    if c:
        itens.append(_item("consentimento", "ok", t(f"escopos {c.get('escopos')} ({c.get('data')})",
                                                    f"scopes {c.get('escopos')} ({c.get('data')})")))
    else:
        itens.append(_item("consentimento", "aviso", t("nenhum consentimento gravado", "no consent recorded"),
                           t("python -m lodemap consentir --escopos gerar[,modelo]",
                             "python -m lodemap consent --scopes gerar[,modelo]")))
    return itens


def diagnosticar(home: Path, repo: Path | None = None, arq: str = permissao.ARQ_PADRAO) -> list[dict]:
    itens = [
        _python(),
        _no_path("git", "git", "falha", t("instale o git e deixe-o no PATH", "install git and put it on PATH")),
        _no_path("claude", "claude", "aviso",
                 t("sem o Claude Code a rota enxuta scripts/descrever.py cai para o agente modelador",
                   "without Claude Code the lean route scripts/descrever.py falls back to the modeler agent")),
        _structurizr(),
        _dot(),
        _no_path("java", "java", "aviso", t("instale o Java 21; o Structurizr CLI precisa dele",
                                            "install Java 21; the Structurizr CLI needs it")),
        _no_path("node", "node", "aviso", t("o verificador usa `node --check`; sem node essa checagem é pulada",
                                            "the verifier uses `node --check`; without node that check is skipped")),
        _skill(home),
        _agentes(home),
    ]
    if repo is not None:
        itens += _repo(repo, arq)
    return itens
