"""Decisões num formato só: todo ADR de {{ARQ_REL}}/adrs segue o cabeçalho único do Lodemap.

Cabeçalho YAML simples (entre linhas "---"): id (4 dígitos, igual ao número do arquivo), titulo, status
(proposta|aceita|substituida|rejeitada), data (AAAA-MM-DD), date (cópia de data, lida pelo importador "madr" do
Structurizr), decisores, elementos (identificadores do modelo), substitui, substituida_por e evidencia. Depois, as
seções Contexto, Decisão, Alternativas e Consequências.

Falha se um ADR cita elemento que não existe no workspace.json exportado (ou, sem exportação, nos .dsl), se
substitui/substituida_por não forem recíprocos ou se o status for inválido. Os testes de mutação garantem que o
validador pega cada um desses erros. O validador mora em scripts/gerar_leitor.py (o mesmo que gera o leitor).
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
ARQ = ROOT / "{{ARQ_REL}}"
sys.path.insert(0, str(ARQ / "scripts"))
import gerar_leitor as gl  # noqa: E402

EXPORT = ARQ / ".structurizr" / "export" / "workspace.json"
_DECL = re.compile(r"^\s*(\w+)\s*=\s*(?:person|softwareSystem|container|component)\b")


def identificadores() -> set[str]:
    if EXPORT.is_file():
        return set(gl.identificadores_do_workspace(json.loads(EXPORT.read_text(encoding="utf-8-sig"))))
    out: set[str] = set()
    for f in [ARQ / "workspace.dsl", *sorted((ARQ / "model").glob("*.dsl"))]:
        if f.is_file():
            out |= {m.group(1) for l in f.read_text(encoding="utf-8").splitlines() if (m := _DECL.match(l))}
    return out


ADRS = gl.ler_adrs(ARQ / "adrs")


def test_ha_adrs():
    assert ADRS, f"nenhum ADR em {ARQ / 'adrs'}"


def test_adrs_no_formato_unico():
    erros = gl.validar_adrs(ADRS, identificadores())
    assert not erros, "\n".join(erros)


def test_workspace_le_adrs_pelo_cabecalho():
    dsl = (ARQ / "workspace.dsl").read_text(encoding="utf-8")
    assert re.search(r"(?m)^\s*!adrs\s+adrs\s+madr\b", dsl), "use '!adrs adrs madr' (o importador lê status e date do cabeçalho)"


def test_indice_de_decisoes_em_dia():
    indice = ARQ / "docs" / f"{gl.INDICE_DECISOES}.md"
    if not indice.is_file():
        pytest.skip("índice ainda não gerado (rode scripts/atualizar.ps1)")
    texto = indice.read_text(encoding="utf-8")
    faltam = [a["arquivo"] for a in ADRS if f"../adrs/{a['arquivo']}" not in texto]
    assert not faltam, f"índice desatualizado; rode scripts/atualizar.ps1. Faltam: {faltam}"


# ------------------------------------------------------------ mutações: o validador pega cada erro

MODELO = """---
id: "{id}"
titulo: Decisão {id}
status: {status}
data: 2026-01-0{n}
date: 2026-01-0{n}
decisores: [dono]
elementos: [{elementos}]
substitui: [{substitui}]
substituida_por: [{substituida_por}]
evidencia:
  - docs/x.md
---

# Decisão {id}

## Contexto

Texto.

## Decisão

Texto.

## Alternativas

Texto.

## Consequências

Texto.
"""


def _adr(pasta: Path, id_: str, status="aceita", elementos="sistema", substitui="", substituida_por=""):
    n = int(id_[-1]) or 1
    (pasta / f"{id_}-decisao.md").write_text(MODELO.format(id=id_, n=n, status=status, elementos=elementos,
                                                            substitui=substitui, substituida_por=substituida_por),
                                             encoding="utf-8")


def _erros(pasta: Path) -> list[str]:
    return gl.validar_adrs(gl.ler_adrs(pasta), {"sistema", "app"})


def test_mutacao_base_valida(tmp_path):
    _adr(tmp_path, "0001", status="substituida", substituida_por="0002")
    _adr(tmp_path, "0002", substitui="0001", elementos="sistema, app")
    assert _erros(tmp_path) == []


def test_mutacao_elemento_inexistente(tmp_path):
    _adr(tmp_path, "0001", elementos="sistema, naoExiste")
    assert any("naoExiste" in e and "não existe no modelo" in e for e in _erros(tmp_path))


def test_mutacao_substituicao_nao_reciproca(tmp_path):
    _adr(tmp_path, "0001")
    _adr(tmp_path, "0002", substitui="0001")
    assert any("substitui '0001'" in e for e in _erros(tmp_path))


def test_mutacao_substituida_sem_par(tmp_path):
    _adr(tmp_path, "0001", status="substituida", substituida_por="0009")
    assert any("'0009', que não existe" in e for e in _erros(tmp_path))


def test_mutacao_status_invalido(tmp_path):
    _adr(tmp_path, "0001", status="Aceito")
    assert any("status 'aceito' inválido" in e for e in _erros(tmp_path))


def test_mutacao_id_difere_do_arquivo(tmp_path):
    _adr(tmp_path, "0001")
    (tmp_path / "0001-decisao.md").rename(tmp_path / "0003-decisao.md")
    assert any("difere do número do arquivo" in e for e in _erros(tmp_path))


def test_mutacao_secao_faltando(tmp_path):
    _adr(tmp_path, "0001")
    f = tmp_path / "0001-decisao.md"
    f.write_text(f.read_text(encoding="utf-8").replace("## Alternativas", "## Outras"), encoding="utf-8")
    assert any("'## Alternativas'" in e for e in _erros(tmp_path))
