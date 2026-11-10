"""Gera os dados do explorador interativo a partir do workspace.json exportado.

Uso: python gerar_explorador.py <workspace.json> <pasta explorador> [raiz do repositório]

Produz explorador/dados.js com elementos, relações, visões (estáticas e dinâmicas), ADRs, documentos, as métricas
curadas (metricas/metricas.json), no formato que explorador/index.html lê. Também junta, sem LLM, o que o explorador mostra como inteligência do mapa:

  mudancas   o que mudou no código desde .lodemap/estado.json:ultimoCommit (lógica do lodemap_diff.py);
  qualidade  a saúde do mapa gravada em .lodemap/estado.json (total, aprovado, pendências);
  prova      para cada relação componente -> componente, se o código confirma (relacoes-codigo.json, gerado por
             codegraph_ponte.py --relacoes) ou se ela existe só no modelo.

Cada bloco é opcional: sem o arquivo de origem, sai null e a interface esconde o recurso. Só usa a biblioteca
padrão. Não edite dados.js à mão: mude o DSL e rode scripts/atualizar.ps1.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import arq_comum as ac  # noqa: E402


def _ler_json(p: Path):
    try:
        return json.loads(p.read_text(encoding="utf-8-sig")) if p.is_file() else None
    except (OSError, ValueError):
        return None


def dados_mudancas(base: Path, workspace: Path | None) -> dict | None:
    """Diff desde o último commit marcado (inclui o que ainda não foi commitado). None sem estado.json."""
    estado = _ler_json(base / ".lodemap" / "estado.json") or {}
    if not estado.get("ultimoCommit"):
        return None
    try:
        import lodemap_diff
        d = lodemap_diff.diff(base, workspace, trabalho=True)
    except (SystemExit, OSError, ValueError, KeyError) as erro:
        return {"modo": "indisponivel", "motivo": str(erro) or erro.__class__.__name__}
    if d.get("modo") != "incremental":
        return {"modo": d.get("modo", "completo"), "motivo": d.get("motivo", "")}
    return {
        "modo": "incremental",
        "de": d["de"], "ate": d["ate"],
        "geradoEm": estado.get("geradoEm"),
        "checkpoint": estado.get("checkpoint"),
        "componentesAfetados": d["componentesAfetados"],
        "modulosNovos": d["modulosNovos"],
        "modulosMudados": d["modulosMudados"],
        "modulosRemovidos": d["modulosRemovidos"],
        "semComponente": d["semComponente"],
    }


def dados_qualidade(base: Path) -> dict | None:
    estado = _ler_json(base / ".lodemap" / "estado.json") or {}
    q = estado.get("qualidade")
    if not isinstance(q, dict) or "total" not in q:
        return None
    return {"total": q.get("total"), "aprovado": bool(q.get("aprovado")), "rodadas": q.get("rodadas"),
            "pendencias": list(q.get("pendencias") or []), "geradoEm": estado.get("geradoEm")}


def dados_prova(base: Path, elementos: dict, relacoes: list) -> dict | None:
    """Relação componente -> componente confirmada no código (em qualquer sentido) ou só no modelo."""
    rel = _ler_json(base / "relacoes-codigo.json")
    if not isinstance(rel, dict) or not isinstance(rel.get("pares"), list):
        return None
    pares = {}
    for p in rel["pares"]:
        for chave in ((p.get("de"), p.get("para")), (p.get("para"), p.get("de"))):
            atual = pares.get(chave)
            if not atual or p.get("arestas", 0) > atual.get("arestas", 0):
                pares[chave] = p
    por_relacao, confirmadas, so_modelo = {}, 0, 0
    for r in relacoes:
        a, b = elementos.get(r["de"]), elementos.get(r["para"])
        if not a or not b or a["tipo"] != "Componente" or b["tipo"] != "Componente" or not a["ident"] or not b["ident"]:
            continue
        p = pares.get((a["ident"], b["ident"]))
        if p:
            confirmadas += 1
            por_relacao[r["id"]] = {"estado": "confirmada", "arestas": p.get("arestas", 0),
                                    "confianca": p.get("confianca", ""), "tipo": p.get("tipo", "")}
        else:
            so_modelo += 1
            por_relacao[r["id"]] = {"estado": "modelo"}
    faltando = [{"de": p["de"], "para": p["para"], "arestas": p.get("arestas", 0), "confianca": p.get("confianca", "")}
                for p in rel["pares"] if not p.get("noModelo")]
    return {"fonte": rel.get("fonte", ""), "geradoEm": rel.get("geradoEm"), "porRelacao": por_relacao,
            "resumo": {"confirmadas": confirmadas, "soModelo": so_modelo, "faltandoNoModelo": len(faltando)},
            "faltandoNoModelo": faltando}


def _cita(texto: str, ident: str) -> bool:
    return len(ident) >= 3 and re.search(rf"(?<![\w-]){re.escape(ident)}(?![\w-])", texto) is not None


def ancora_adr(arquivo: str) -> str:
    m = re.match(r"(\d+)", arquivo)
    return "adr-" + (m.group(1).zfill(4) if m else Path(arquivo).stem)


def citacoes(elementos: dict, textos: list[tuple[str, str]]) -> dict[str, list[str]]:
    """chave do texto -> ids dos elementos cujo identificador do DSL aparece nele."""
    com_ident = [e for e in elementos.values() if e["ident"]]
    return {chave: [e["id"] for e in com_ident if _cita(texto, e["ident"])] for chave, texto in textos}


def dados_documentos(pasta: Path, elementos: dict) -> list[dict]:
    if not pasta.is_dir():
        return []
    docs = []
    for f in sorted(pasta.glob("*.md")):
        texto = f.read_text(encoding="utf-8", errors="replace")
        titulo = next((l.lstrip("# ").strip() for l in texto.splitlines() if l.startswith("#")), f.stem)
        docs.append({"arquivo": f.name, "titulo": titulo, "ancora": "doc-" + f.stem, "_texto": texto})
    cit = citacoes(elementos, [(d["ancora"], d.pop("_texto")) for d in docs])
    for d in docs:
        d["elementos"] = cit[d["ancora"]]
    return docs


def _arq_rel(base: Path, raiz_repo: str) -> str | None:
    if not raiz_repo:
        return None
    try:
        return base.resolve().relative_to(Path(raiz_repo).resolve()).as_posix().strip(".")
    except (ValueError, OSError):
        return None


def gravar_local(base: Path, raiz_repo: str) -> None:
    """Raiz do repositório nesta máquina, para o link "VS Code" do explorador servido em 127.0.0.1. Fora do git."""
    if not raiz_repo:
        return
    try:
        (base / ".lodemap").mkdir(parents=True, exist_ok=True)
        (base / ".lodemap" / "local.json").write_text(
            json.dumps({"repo": raiz_repo.replace("\\", "/").rstrip("/")}, ensure_ascii=False) + "\n",
            encoding="utf-8", newline="\n")
    except OSError:
        pass


def montar(workspace: Path, destino: Path, raiz_repo: str = "") -> dict:
    ws = ac.ler_workspace(workspace)
    base = destino.parent
    cfg = ac.ler_config(base)
    elementos, relacoes = ac.coletar(ws)
    metricas = ac.ler_metricas(base, cfg)
    for m in metricas:
        for x in [m.get("atual", {})] + m.get("historico", []):
            x["fonte"]["url"] = ac.link_fonte(x.get("fonte", {}), cfg)
    adrs = ac.adrs(base / "adrs")
    cit = citacoes(elementos, [(a["arquivo"], a["texto"]) for a in adrs])
    for a in adrs:
        a["ancora"] = ancora_adr(a["arquivo"])
        a["elementos"] = cit[a["arquivo"]]
    return {
        "idioma": cfg["idioma"],
        "nome": ws.get("name", ""),
        "descricao": ws.get("description", ""),
        # Pasta da arquitetura a partir da raiz do repositório. O caminho absoluto desta máquina NÃO entra aqui: o
        # dados.js é versionado e o caminho levaria o nome do usuário para o git e para qualquer cópia hospedada.
        "arqRel": _arq_rel(base, raiz_repo),
        "leitor": cfg.get("leitor", "../leitor/index.html"),
        "elementos": list(elementos.values()),
        "relacoes": relacoes,
        "visoes": ac.visoes(ws),
        "adrs": adrs,
        "documentos": dados_documentos(base / "docs", elementos),
        "metricas": metricas,
        "mudancas": dados_mudancas(base, Path(workspace)),
        "qualidade": dados_qualidade(base),
        "prova": dados_prova(base, elementos, relacoes),
    }


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    destino = Path(sys.argv[2])
    dados = montar(Path(sys.argv[1]), destino, sys.argv[3] if len(sys.argv) > 3 else "")
    destino.mkdir(parents=True, exist_ok=True)
    js = ("// Gerado por scripts/gerar_explorador.py a partir do workspace.json. Não edite à mão.\nwindow.ARQ = "
          + json.dumps(dados, ensure_ascii=False) + ";\n")
    (destino / "dados.js").write_text(js, encoding="utf-8", newline="\n")
    gravar_local(destino.parent, sys.argv[3] if len(sys.argv) > 3 else "")
    extras = [k for k in ("mudancas", "qualidade", "prova") if dados[k]]
    if dados.get("idioma") == "en":
        nomes = {"mudancas": "changes", "qualidade": "quality", "prova": "code proof"}
        print(f"{len(dados['elementos'])} elements, {len(dados['relacoes'])} relationships, {len(dados['visoes'])} "
              f"views, {len(dados['adrs'])} ADRs, {len(dados['metricas'])} metrics in {destino / 'dados.js'}"
              + (f" (with {', '.join(nomes[k] for k in extras)})" if extras else ""))
    else:
        print(f"{len(dados['elementos'])} elementos, {len(dados['relacoes'])} relações, {len(dados['visoes'])} visões, "
              f"{len(dados['adrs'])} ADRs, {len(dados['metricas'])} métricas em {destino / 'dados.js'}"
              + (f" (com {', '.join(extras)})" if extras else ""))


if __name__ == "__main__":
    main()
