"""Métricas da arquitetura: todo número do resumo curado (campo "metricas" do lodemap.json) precisa de evidência.

Confere, para cada métrica e cada ponto do histórico:
  1. a fonte tem arquivo, ramo, commit e campo;
  2. os componentes citados existem no modelo (identificadores do DSL);
  3. quando o commit está no repositório local, o JSON existe nesse commit e o campo tem o mesmo número
     (com a precisão gravada no resumo). Commit ausente (clone raso no CI, ramo não buscado) só pula esta
     conferência; ele não vale como evidência faltando.

O campo é um caminho com pontos ("latencia.trat.ttft_p50_s"); um "*" percorre todas as chaves daquele
nível e a agregação ("soma", "contar>0", "max") junta os valores. Índice de lista vale ("ic95.0").
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "{{ARQ_REL}}"
_CFG = json.loads((BASE / "lodemap.json").read_text(encoding="utf-8-sig"))
METRICAS = BASE / _CFG.get("metricas", "metricas/metricas.json")
MODELO = BASE / "model"


def _metricas() -> list[dict]:
    if not METRICAS.is_file():
        return []
    return json.loads(METRICAS.read_text(encoding="utf-8-sig")).get("metricas", [])


def _pontos():
    for m in _metricas():
        yield m["id"], "atual", m["atual"]
        for i, h in enumerate(m.get("historico", [])):
            yield m["id"], f"historico[{i}]", h


def _identificadores() -> set[str]:
    ids = set()
    for f in MODELO.glob("*.dsl"):
        ids |= set(re.findall(r"^\s*(\w+)\s*=\s*(?:component|container|softwareSystem|person)\b",
                              f.read_text(encoding="utf-8"), re.M))
    return ids


def resolver(dado, campo: str):
    atuais = [dado]
    for parte in campo.split("."):
        prox = []
        for a in atuais:
            if parte == "*":
                prox += list(a.values()) if isinstance(a, dict) else list(a)
            elif isinstance(a, list):
                prox.append(a[int(parte)])
            else:
                prox.append(a[parte])
        atuais = prox
    return atuais


def agregar(valores: list, agregacao: str | None):
    if not agregacao:
        assert len(valores) == 1, "campo com * precisa de agregação"
        return valores[0]
    if agregacao == "soma":
        return sum(valores)
    if agregacao == "contar>0":
        return sum(1 for v in valores if v > 0)
    if agregacao == "max":
        return max(valores)
    raise AssertionError(f"agregação desconhecida: {agregacao}")


def _casas(v) -> int:
    s = repr(float(v)) if not isinstance(v, int) else "0"
    return len(s.split(".")[1].rstrip("0")) if "." in s else 0


def test_resumo_e_valido():
    if not METRICAS.is_file():
        pytest.skip("sem resumo de métricas")
    assert isinstance(_metricas(), list)


def test_toda_metrica_tem_fonte_completa_e_componentes_reais():
    ids = _identificadores()
    problemas = []
    for mid, onde, p in _pontos():
        f = p.get("fonte") or {}
        for chave in ("arquivo", "ramo", "commit", "campo"):
            if not f.get(chave):
                problemas.append(f"{mid} {onde}: fonte sem {chave}")
        if not isinstance(p.get("valor"), (int, float)):
            problemas.append(f"{mid} {onde}: valor não numérico")
        if not p.get("data"):
            problemas.append(f"{mid} {onde}: sem data")
    for m in _metricas():
        fora = [c for c in m.get("componentes", []) if c not in ids]
        if not m.get("componentes") or fora:
            problemas.append(f"{m['id']}: componentes ausentes do modelo {fora or '(nenhum)'}")
    assert not problemas, "\n".join(problemas)


def test_ids_unicos():
    ids = [m["id"] for m in _metricas()]
    assert len(ids) == len(set(ids))


def _git_show(commit: str, arquivo: str) -> str | None:
    if not shutil.which("git"):
        return None
    r = subprocess.run(["git", "-C", str(ROOT), "show", f"{commit}:{arquivo}"], capture_output=True, timeout=30)
    return r.stdout.decode("utf-8") if r.returncode == 0 else None


def test_cada_numero_bate_com_o_json_no_commit():
    conferidos, sem_commit, divergentes = 0, [], []
    cache: dict[tuple, object] = {}
    for mid, onde, p in _pontos():
        f = p["fonte"]
        chave = (f["commit"], f["arquivo"])
        if chave not in cache:
            texto = _git_show(*chave)
            cache[chave] = json.loads(texto) if texto is not None else None
        dado = cache[chave]
        if dado is None:
            sem_commit.append(f"{mid} {onde}: {f['commit']}:{f['arquivo']}")
            continue
        real = agregar(resolver(dado, f["campo"]), f.get("agregacao"))
        tol = 0.5 * 10 ** -_casas(p["valor"]) + 1e-9
        if abs(float(real) - float(p["valor"])) > tol:
            divergentes.append(f"{mid} {onde}: resumo {p['valor']} x evidência {real} ({f['campo']})")
        conferidos += 1
    assert not divergentes, "\n".join(divergentes)
    if not conferidos:
        pytest.skip("nenhum commit de evidência no repositório local: " + "; ".join(sem_commit[:3]))


def test_resolver_e_agregar():
    d = {"a": {"x": {"leaks": 0}, "y": {"leaks": 2}}, "l": [1.5, 2]}
    assert agregar(resolver(d, "a.*.leaks"), "soma") == 2
    assert agregar(resolver(d, "a.*.leaks"), "contar>0") == 1
    assert agregar(resolver(d, "l.0"), None) == 1.5
