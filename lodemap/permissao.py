"""Fluxo de permissão do Lodemap: plano com 0 tokens, consentimento por escopo e revogação.

- `plano`: conta os módulos (inventario.py quando o mapa já existe; senão os globs padrão do novo_mapa.py), estima
  custo e tempo pelo modelo de custo medido (references/custo-equivalente.json) e lista os arquivos que seriam
  escritos. Não chama modelo nenhum.
- `consentir`: grava <pasta da arquitetura>/.lodemap/consentimento.json com data, escopos e teto mensal.
- `revogar`: tira escopos ou apaga o consentimento.
- `verificar`: diz se um escopo (e um custo estimado) está autorizado; passo com modelo sem consentimento = perguntar.
"""
from __future__ import annotations

import contextlib
import io
import json
import math
import sys
import tempfile
from datetime import datetime
from pathlib import Path

from lodemap import RAIZ

ESCOPOS = {
    "gerar": "criar e atualizar o mapa só com scripts (0 tokens)",
    "gancho": "gancho de commit que atualiza o mapa sem tokens",
    "modelo": "passos com modelo (inventário, modelagem, revisão) dentro do teto",
    "synapse": "nota de arquitetura no Synapse",
}
ARQ_PADRAO = "docs/architecture/structurizr"
CUSTO = RAIZ / "references" / "custo-equivalente.json"


def _scripts():
    pasta = str(RAIZ / "scripts")
    if pasta not in sys.path:
        sys.path.insert(0, pasta)
    import codegraph_ponte  # noqa: PLC0415
    import inventario  # noqa: PLC0415
    import novo_mapa  # noqa: PLC0415
    return inventario, novo_mapa, codegraph_ponte


def contar_modulos(repo: Path, arq: str = ARQ_PADRAO) -> dict:
    inventario, novo_mapa, ponte = _scripts()
    cfg_p = repo / arq / "lodemap.json"
    if cfg_p.is_file():
        with tempfile.TemporaryDirectory() as tmp:
            j = Path(tmp) / "inventario.json"
            with contextlib.redirect_stdout(io.StringIO()):
                inventario.main(["--repo", str(repo), "--arq", arq, "--json", str(j)])  # já aplica o "ignorar" do mapa
            d = json.loads(j.read_text(encoding="utf-8"))
        cfg = json.loads(cfg_p.read_text(encoding="utf-8-sig"))
        out = {"fonte": "inventario.py", "modulos": len(d["modulos"]), "fora": d["fora"], "globs": cfg.get("modulos", [])}
        if ponte._ignorar_da_config(cfg):
            out["ignorar"] = ponte._ignorar_da_config(cfg)
        return out
    raiz = novo_mapa.detectar_raiz(repo)
    globs, ignorar = novo_mapa.padroes_da_linguagem(repo, raiz)  # os mesmos que o novo_mapa.py escreveria
    alvos = set()
    for padrao in globs:
        pasta = padrao.endswith("/")
        for p in repo.glob(padrao.rstrip("/")):
            if any(x in novo_mapa._PULAR or x.startswith(".") for x in p.relative_to(repo).parts):
                continue
            if ponte._ignorado(p.relative_to(repo).as_posix(), ignorar):
                continue
            if pasta == p.is_dir():
                alvos.add(p.relative_to(repo).as_posix())
    out = {"fonte": "globs padrão do novo_mapa.py (mapa ainda não existe)", "modulos": len(alvos),
           "fora": len(alvos), "globs": globs}
    if ignorar:
        out["ignorar"] = ignorar
    return out


def estimar(modulos: int, custo: dict | None = None) -> dict:
    """Escala linear pela rodada medida em fases do mapa do projeto B (63 módulos). Valores em US$ equivalentes da API."""
    custo = custo or json.loads(CUSTO.read_text(encoding="utf-8"))
    rod = {r["id"]: r for r in custo["rodadas"]}
    ref = rod["mapa-projeto-b-fases"]
    base = 63
    fator = max(modulos, 1) / base
    sonnet = ref["custo_usd"] * fator
    opus = sonnet / (1 - custo["reducao_opus_para_sonnet"]["custo"])
    proj = custo["projecao_haiku_mapa_projeto_b"]
    fora = ref.get("nao_registrado", []) + ref.get("nao_incluido", [])
    return {
        "metodo": f"linear sobre a rodada medida '{ref['rotulo']}' ({base} módulos, {ref['chamadas']} chamadas, "
                  f"{ref['minutos']} min, US$ {ref['custo_usd']} em {ref['modelo']}); fonte: {custo['fonte_tokens']}",
        "tipo": "estimativa linear de uma única rodada medida (não validada em outros tamanhos)"
                + (" ; fica de fora: " + ", ".join(fora) if fora else ""),
        "sonnet_usd": round(sonnet, 2),
        "opus_usd_estimado": round(opus, 2),
        "haiku_usd_projecao_nao_medida": round(proj["por_chamada"] * fator, 2),
        "minutos": round(ref["minutos"] * fator, 1),
        "chamadas": round(ref["chamadas"] * fator),
        "checkpoint_por_commit_usd": rod["checkpoint-incremental"]["custo_usd"],
    }


def arquivos_a_escrever(repo: Path, arq: str = ARQ_PADRAO, testes: str = "tests") -> list[dict]:
    tpl = RAIZ / "templates"
    out = []
    for origem, destino in ((tpl / "structurizr", repo / arq), (tpl / "tests", repo / testes)):
        for f in sorted(origem.rglob("*")):
            if f.is_dir() or "__pycache__" in f.parts:
                continue
            alvo = destino / f.relative_to(origem)
            out.append({"caminho": alvo.relative_to(repo).as_posix(), "acao": "mantém" if alvo.exists() else "cria"})
    return out


def _arq_consent(repo: Path, arq: str) -> Path:
    return repo / arq / ".lodemap" / "consentimento.json"


def ler_consentimento(repo: Path, arq: str = ARQ_PADRAO) -> dict | None:
    p = _arq_consent(repo, arq)
    return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else None


def _exigir_repositorio(repo: Path) -> Path:
    repo = Path(repo).resolve()
    if not repo.is_dir():
        raise ValueError(f"repositório não encontrado: {repo}")
    return repo


def plano(repo: Path, arq: str = ARQ_PADRAO) -> dict:
    repo = _exigir_repositorio(repo)
    mods = contar_modulos(repo, arq)
    arqs = arquivos_a_escrever(repo, arq)
    aviso = None
    if mods["modulos"] == 0:
        aviso = (f"nenhum módulo encontrado pelos globs {mods['globs']}; a estimativa não vale para este repositório. "
                 f"Ajuste 'raiz_codigo' e 'modulos' no lodemap.json (ou crie o mapa e edite os globs) antes de consentir.")
    return {"repo": str(repo), "arquitetura": arq, "mapa_existe": (repo / arq / "lodemap.json").is_file(),
            "modulos": mods, "estimativa": estimar(mods["modulos"]), "tokens_deste_plano": 0,
            "arquivos": arqs, "a_criar": sum(a["acao"] == "cria" for a in arqs),
            "consentimento": ler_consentimento(repo, arq), "aviso": aviso}


def consentir(repo: Path, escopos: list[str], orcamento_mensal: float | None = None, arq: str = ARQ_PADRAO) -> Path:
    desconhecidos = set(escopos) - set(ESCOPOS)
    if desconhecidos or not escopos:
        raise ValueError(f"escopos inválidos: {sorted(desconhecidos) or 'nenhum'} (use {', '.join(ESCOPOS)})")
    if orcamento_mensal is not None and not (math.isfinite(orcamento_mensal) and orcamento_mensal >= 0):
        raise ValueError(f"orçamento mensal inválido ({orcamento_mensal}): use um número finito, zero ou maior")
    p = _arq_consent(_exigir_repositorio(repo), arq)
    p.parent.mkdir(parents=True, exist_ok=True)
    dado = {"versao": 1, "data": datetime.now().astimezone().isoformat(timespec="seconds"),
            "escopos": sorted(set(escopos)), "orcamento_mensal_usd": orcamento_mensal,
            "nota": "Revogue com: python -m lodemap revogar --repo <repo>"}
    p.write_text(json.dumps(dado, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    return p


def revogar(repo: Path, escopos: list[str] | None = None, arq: str = ARQ_PADRAO) -> dict | None:
    p = _arq_consent(Path(repo).resolve(), arq)
    atual = ler_consentimento(Path(repo).resolve(), arq)
    if atual is None:
        return None
    resto = sorted(set(atual["escopos"]) - set(escopos)) if escopos else []
    if not resto:
        p.unlink()
        return None
    atual["escopos"] = resto
    atual["data_revogacao"] = datetime.now().astimezone().isoformat(timespec="seconds")
    p.write_text(json.dumps(atual, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    return atual


def verificar(repo: Path, escopo: str, custo_usd: float = 0.0, arq: str = ARQ_PADRAO) -> tuple[bool, str]:
    c = ler_consentimento(Path(repo).resolve(), arq)
    if not c or escopo not in c.get("escopos", []):
        return False, f"sem consentimento para '{escopo}': peça o ok do dono"
    teto = c.get("orcamento_mensal_usd")
    if escopo == "modelo" and (teto is None or custo_usd > teto):
        return False, (f"custo estimado US$ {custo_usd:.2f} acima do teto mensal ({teto}); confirme com o dono"
                       if teto is not None else "passo com modelo sem orçamento mensal: confirme com o dono")
    return True, f"autorizado ({escopo}, consentido em {c['data']})"
