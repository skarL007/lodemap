"""Descreve os componentes pendentes do decisoes-modelo.json com uma chamada enxuta do Claude Code (claude -p).

Rota padrão (o modelador fica de reserva), mais barata do que um subagente para a parte repetitiva da fase B: nome, descrição de uma frase e área
dos componentes em `pendentes.componentes_novos` e `pendentes.componentes_revisar` (ou dos que estão sem descrição).
Containers, áreas, relações, status e fluxos continuam com o lodemap-modelador.

Como chama o modelo (só o CLI oficial do Claude Code, pela assinatura; nunca a API):
  claude -p --model haiku --effort medium --output-format json --no-session-persistence
            --tools "" --strict-mcp-config --setting-sources "" --system-prompt-file <arq> --json-schema <schema>
- sem ferramentas, MCP nem settings: o prefixo fixo cai de ~55 mil para ~1 mil tokens por chamada;
- saída estruturada com a área num enum das áreas já decididas: nenhum JSON a consertar, nenhuma área inventada;
- o modelo recebe uma ficha determinística por módulo (docstring, símbolos públicos, comentários, quem usa e quem é
  usado), não o arquivo inteiro;
- todos os módulos numa chamada (até --lote), com a instrução de responder só pela ferramenta de saída, o que evita o
  turno extra em que o modelo escreve o JSON em texto e depois de novo na ferramenta (dobrava o custo).

Depois da chamada, um gate determinístico (frase genérica, tamanho, nenhum termo do código, descrição repetida) reenvia
só os reprovados, uma vez, com o motivo. O que ainda falhar, ou qualquer erro do CLI, fica em
`pendentes.descricoes_para_modelador` para o lodemap-modelador fazer como antes. Código de saída: 0 tudo descrito,
3 sobrou algo para o modelador, 2 erro de uso.

Uso: python descrever.py --arq <pasta structurizr> [--repo <raiz>] [--todos] [--lote 76] [--modelo haiku]
                         [--esforco medium] [--simular]
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unicodedata
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
import esqueleto  # noqa: E402

TETO_FICHA = 1500
IGNORAR = esqueleto.IGNORAR
GENERICO = re.compile(
    r"^(este|esta|esse|essa|o|a)\s+(componente|m[oó]dulo|script|arquivo|classe)\b|garantindo|facilitando|"
    r"de forma (eficiente|consistente|robusta)|auxiliando|^(this|the)\s+(component|module|script|file|class)\b|"
    r"ensuring|seamless|in an efficient way", re.I)
PARE = set("para pelo pela pelos pelas como sobre entre quando sempre nunca cada todo toda todos todas esse essa este "
           "esta isso antes depois sem com que dos das nos nas uma umas uns outro outra mesmo mesma ainda apenas onde "
           "qual quais seus suas from with that this when each into over only which their there about".split())
SO_FERRAMENTA = {
    "pt": "Responda SOMENTE chamando a ferramenta StructuredOutput, uma única vez, com todos os itens. Não escreva "
          "nenhum texto fora dela.",
    "en": "Answer ONLY by calling the StructuredOutput tool, exactly once, with every item. Do not write any text "
          "outside it.",
}
INSTRUCAO = {
    "pt": ("Você documenta componentes de uma arquitetura C4, em português do Brasil.\nÁreas permitidas:\n{areas}\n\n"
           "Exemplos do estilo da casa:\n{exemplos}\n\nPara cada módulo recebido, escreva nome (2 a 5 palavras), descricao "
           "(UMA frase de 80 a 200 caracteres, começando por verbo no presente, com o fato que diferencia este módulo e o "
           "porquê; não comece por \"Este componente/módulo\", não use \"garantindo\", \"facilitando\" nem \"de forma "
           "eficiente\", não repita o nome) e area (uma das permitidas). Responda para todos os itens, mantendo o campo i."),
    "en": ("You document components of a C4 architecture, in English.\nAllowed areas:\n{areas}\n\nHouse style examples:\n"
           "{exemplos}\n\nFor each module, write nome (2 to 5 words), descricao (ONE sentence of 80 to 200 characters, "
           "starting with a present-tense verb, stating the fact that sets this module apart and why; do not start with "
           "\"This component/module\", do not use \"ensuring\" or \"seamless\", do not repeat the name) and area (one of "
           "the allowed ones). Answer for every item and keep the field i."),
}
EXEMPLOS_PADRAO = {
    "pt": [{"nome": "Gate de qualidade", "descricao": "Mede o modelo exportado contra a linha de base e reprova o mapa "
            "quando um critério cai abaixo de 70%, para a qualidade não depender do modelo que escreveu."},
           {"nome": "Ponte do índice", "descricao": "Lê símbolos e arestas do índice de código sem abrir arquivos e cai "
            "para o ast quando o índice não existe, mantendo o inventário barato."}],
    "en": [{"nome": "Quality gate", "descricao": "Scores the exported model against the baseline and fails the map when "
            "any criterion drops below 70%, so quality does not depend on the model that wrote it."},
           {"nome": "Index bridge", "descricao": "Reads symbols and edges from the code index without opening files and "
            "falls back to ast when no index exists, keeping the inventory cheap."}],
}


def _sem_acento(s: str) -> str:
    return "".join(ch for ch in unicodedata.normalize("NFD", s.lower()) if unicodedata.category(ch) != "Mn")


def termos(s: str) -> set[str]:
    return {w[:6] for w in re.findall(r"[a-z0-9_]{5,}", _sem_acento(s)) if w not in PARE}


def _texto(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _arquivos(repo: Path, modulo: str) -> list[Path]:
    p = repo / modulo.rstrip("/")
    if p.is_file():
        return [p]
    if p.is_dir():
        return sorted(f for f in p.rglob("*") if f.is_file() and not (set(f.relative_to(p).parts) & IGNORAR)
                      and f.suffix in esqueleto.EXTENSAO)
    return []


def _superficie(txt: str, sufixo: str) -> list[str]:
    partes = []
    if sufixo == ".py":
        try:
            t = ast.parse(txt)
        except SyntaxError:
            t = None
        if t is not None:
            d = ast.get_docstring(t)
            if d:
                partes.append("Docstring:\n" + d[:1000])
            sims = []
            for n in t.body:
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and not n.name.startswith("_"):
                    dd = (ast.get_docstring(n) or "").strip().splitlines()
                    pre = "class " if isinstance(n, ast.ClassDef) else ""
                    sims.append(f"- {pre}{n.name}" + (f": {dd[0][:140]}" if dd else ""))
                elif isinstance(n, ast.Assign) and all(isinstance(x, ast.Name) and x.id.isupper() for x in n.targets):
                    sims.append(f"- const {n.targets[0].id}")
            if sims:
                partes.append("Símbolos públicos:\n" + "\n".join(sims[:30]))
            return partes
    com = [l.strip() for l in txt.splitlines()[:400]
           if re.match(r"\s*(#|//|/\*|\*|<#|--)", l) and len(l.strip()) > 3 and not l.startswith("#!")]
    if com:
        partes.append("Comentários:\n" + "\n".join(com[:25])[:1000])
    dec = [l.strip() for l in txt.splitlines() if esqueleto._DECL.match(l)][:30]
    if dec:
        partes.append("Declarações:\n" + "\n".join(dec)[:1000])
    return partes


def ficha(repo: Path, c: dict, rels: list[dict], teto: int = TETO_FICHA) -> str:
    """Resumo determinístico do módulo: o que uma frase de descrição pode citar, sem o arquivo inteiro."""
    partes = [f"Módulo: {c['modulo']} ({c.get('linguagem', '')}, {c.get('linhas', '?')} linhas)"]
    if c.get("dica"):
        partes.append(f"Dica do inventário: {c['dica'][:300]}")
    arqs = _arquivos(repo, c["modulo"])
    textos = []
    for f in arqs[:6]:
        txt = _texto(f)
        textos.append(txt)
        sup = _superficie(txt, f.suffix)
        if len(arqs) > 1:
            sup = [f"[{f.relative_to(repo).as_posix()}]"] + sup
        partes += sup
    usa = [r["para"] for r in rels if r.get("de") == c["modulo"]][:8]
    usado = [r["de"] for r in rels if r.get("para") == c["modulo"]][:8]
    if usa:
        partes.append("Usa: " + ", ".join(usa))
    if usado:
        partes.append("É usado por: " + ", ".join(usado))
    corpo = "\n\n".join(partes)
    if len(corpo) < teto and textos:
        corpo += "\n\nCódigo (início):\n" + textos[0][: teto - len(corpo)]
    return corpo[: teto + 400]


def gate(o: dict, ficha_txt: str, modulo: str) -> str:
    d = (o.get("descricao") or "").strip()
    if GENERICO.search(d):
        return "frase genérica ou enchimento"
    if not 60 <= len(d) <= 220:
        return f"tamanho {len(d)} fora de 60 a 220 caracteres"
    if not (termos(d) & (termos(ficha_txt) | termos(modulo))):
        return "não cita nenhum termo concreto do código"
    if not (o.get("nome") or "").strip():
        return "nome vazio"
    return ""


def alvos(d: dict, todos: bool) -> list[dict]:
    pend = d.get("pendentes", {})
    marcados = set(pend.get("componentes_novos", [])) | set(pend.get("componentes_revisar", []))
    out = []
    for c in d.get("componentes", []):
        if c.get("fundir_em"):
            continue
        if todos or c["modulo"] in marcados or not c.get("descricao"):
            out.append(c)
    return out


def _exemplos(d: dict, idioma: str, excluir: set[str]) -> str:
    ex = [{"nome": c["nome"], "descricao": c["descricao"], "area": c.get("area", "")}
          for c in d.get("componentes", []) if c.get("descricao") and c.get("nome") and c["modulo"] not in excluir][:4]
    if len(ex) < 2:
        ex += EXEMPLOS_PADRAO[idioma][: 2 - len(ex)]
    return "\n".join(json.dumps(e, ensure_ascii=False) for e in ex)


def schema(areas: list[str]) -> dict:
    item = {"type": "object", "properties": {"i": {"type": "integer"}, "nome": {"type": "string"},
                                              "descricao": {"type": "string"}, "area": {"type": "string", "enum": areas}},
            "required": ["i", "nome", "descricao", "area"]}
    return {"type": "object", "properties": {"itens": {"type": "array", "items": item}}, "required": ["itens"]}


def comando(modelo: str, esforco: str, sistema: Path, sch: dict) -> list[str]:
    exe = os.environ.get("LODEMAP_CLAUDE") or shutil.which("claude") or "claude"
    base = [sys.executable, exe] if exe.endswith(".py") else [exe]
    return base + ["-p", "--model", modelo, "--effort", esforco, "--output-format", "json",
                   "--no-session-persistence", "--tools", "", "--strict-mcp-config", "--setting-sources", "",
                   "--system-prompt-file", str(sistema), "--json-schema", json.dumps(sch, ensure_ascii=False)]


def chamar(cmd: list[str], texto: str, cwd: Path, limite_s: int = 900) -> tuple[list[dict], dict]:
    t0 = time.time()
    r = subprocess.run(cmd, input=texto, capture_output=True, text=True, encoding="utf-8", cwd=str(cwd), timeout=limite_s)
    if r.returncode != 0:
        raise RuntimeError(f"claude -p saiu com {r.returncode}: {(r.stderr or r.stdout)[-300:]}")
    dados = json.loads(r.stdout)
    if dados.get("is_error"):
        raise RuntimeError(f"claude -p devolveu erro: {str(dados.get('result'))[:300]}")
    est = dados.get("structured_output")
    if est is None:
        txt = dados.get("result") or ""
        est = json.loads(txt[txt.find("{"): txt.rfind("}") + 1])
    u = dados.get("usage") or {}
    uso = {"input": u.get("input_tokens", 0), "cache_criado": u.get("cache_creation_input_tokens", 0),
           "cache_lido": u.get("cache_read_input_tokens", 0), "output": u.get("output_tokens", 0),
           "turnos": dados.get("num_turns"), "seg": round(time.time() - t0, 1)}
    return list(est.get("itens") or []), uso


# Revisão conservadora: o módulo já tinha nome, descrição e área, e a superfície pública dele mudou. Medido no axios
# (v1.20.0 -> v1.21.1): sem esta regra o modelo trocava a frase por outro detalhe do arquivo em 16 de 16 revisões e
# mudava a área de 3, desfazendo decisões do modelador sem que o código pedisse.
REVISAO = {
    "pt": ("Descrição atual (escrita antes de o módulo mudar): {desc}\n"
           "Devolva-a palavra por palavra se ainda for verdadeira. Mude só o que ficou falso ou o que o módulo passou "
           "a fazer de essencial; não troque por outro detalhe do arquivo."),
    "en": ("Current description (written before the module changed): {desc}\n"
           "Return it word for word if it is still true. Change only what became false, or what the module now does "
           "that is essential; do not swap it for a different detail of the file."),
}


def _pedido(idioma: str, itens: list[tuple[int, str, str]], anteriores: dict[int, str] | None = None) -> str:
    cab = f"Documente estes {len(itens)} módulos." if idioma == "pt" else f"Document these {len(itens)} modules."
    partes = []
    for i, f, erro in itens:
        p = f"### i={i}\n{f}"
        if anteriores and i in anteriores:
            p += "\n" + REVISAO[idioma].format(desc=anteriores[i])
        if erro:
            p += (f"\nA versão anterior foi reprovada: {erro}. Corrija." if idioma == "pt"
                  else f"\nThe previous version was rejected: {erro}. Fix it.")
        partes.append(p)
    return cab + "\n\n" + "\n\n".join(partes)


def descrever(arq: Path, repo: Path, todos: bool = False, lote: int = 76, modelo: str = "haiku",
              esforco: str = "medium", simular: bool = False) -> dict:
    destino = esqueleto.caminho_decisoes(arq)
    if not destino.is_file():
        raise ValueError(f"{destino} não existe: rode esqueleto.py rascunho antes")
    d = json.loads(destino.read_text(encoding="utf-8"))
    areas = list(d.get("areas") or {})
    if not areas:
        raise ValueError("decisoes-modelo.json não tem 'areas': a fase A (lodemap-modelador) vem antes")
    idioma = esqueleto._idioma(arq)
    lista = alvos(d, todos)
    rels = d.get("relacoes", [])
    fichas = [ficha(repo, c, rels) for c in lista]
    # Com --todos o dono pediu para refazer tudo; sem ele, quem já tem nome, descrição e área válida é uma revisão.
    anteriores = {} if todos else {i: c["descricao"] for i, c in enumerate(lista)
                                   if c.get("descricao") and c.get("nome") and c.get("area") in areas}
    rel = {"alvos": len(lista), "descritos": 0, "revisados": len(anteriores), "mantidos": 0, "reenviados": 0,
           "para_modelador": [], "chamadas": [], "simulado": simular}
    if not lista:
        return rel
    areas_txt = "\n".join(f"- {k}: {v}" for k, v in (d.get("areas") or {}).items())
    sistema = INSTRUCAO[idioma].format(areas=areas_txt, exemplos=_exemplos(d, idioma, {c["modulo"] for c in lista}))
    sistema += "\n\n" + SO_FERRAMENTA[idioma]
    sch = schema(areas)
    if simular:
        rel["sistema_car"] = len(sistema)
        rel["pedido_car"] = len(_pedido(idioma, [(i, f, "") for i, f in enumerate(fichas)], anteriores))
        return rel
    saidas: dict[int, dict] = {}
    with tempfile.TemporaryDirectory(prefix="lodemap-descrever-") as tmp:
        sp = Path(tmp) / "sistema.txt"
        sp.write_text(sistema, encoding="utf-8")
        cmd = comando(modelo, esforco, sp, sch)

        def rodada(idx: list[int], erros: dict[int, str]) -> None:
            for k in range(0, len(idx), lote):
                bloco = idx[k:k + lote]
                try:
                    itens, uso = chamar(cmd, _pedido(idioma, [(i, fichas[i], erros.get(i, "")) for i in bloco],
                                                     anteriores), Path(tmp))
                except (RuntimeError, ValueError, json.JSONDecodeError, subprocess.TimeoutExpired, OSError) as e:
                    rel["chamadas"].append({"itens": len(bloco), "erro": str(e)[:300]})
                    continue
                rel["chamadas"].append({"itens": len(bloco), **uso})
                for o in itens:
                    if isinstance(o, dict) and o.get("i") in bloco and o.get("area") in areas:
                        saidas[o["i"]] = o

        def reprovados() -> dict[int, str]:
            erros, vistas = {}, {}
            for i, c in enumerate(lista):
                o = saidas.get(i)
                if not o:
                    erros[i] = "item ausente"
                    continue
                e = gate(o, fichas[i], c["modulo"])
                chave = (o.get("descricao") or "").strip().lower()
                if not e and chave in vistas:
                    e = f"descrição idêntica à do módulo {lista[vistas[chave]]['modulo']}"
                vistas.setdefault(chave, i)
                if e:
                    erros[i] = e
            return erros

        rodada(list(range(len(lista))), {})
        erros = reprovados()
        if erros and any("erro" not in ch for ch in rel["chamadas"]):
            rel["reenviados"] = len(erros)
            rodada(sorted(erros), erros)
            erros = reprovados()
    for i, c in enumerate(lista):
        if i in erros:
            rel["para_modelador"].append({"modulo": c["modulo"], "motivo": erros[i]})
            continue
        o = saidas[i]
        if i in anteriores:
            # Nome e área de uma revisão são decisões já tomadas (talvez pelo modelador): só a frase pode mudar.
            if o["descricao"].strip() == anteriores[i].strip():
                rel["mantidos"] += 1
            else:
                c.update(descricao=o["descricao"].strip(), descrito_por=f"claude -p {modelo} {esforco}")
        else:
            c.update(nome=o["nome"].strip(), descricao=o["descricao"].strip(), area=o["area"],
                     descrito_por=f"claude -p {modelo} {esforco}")
        rel["descritos"] += 1
    pend = d.setdefault("pendentes", {})
    feitos = {c["modulo"] for c in lista} - {p["modulo"] for p in rel["para_modelador"]}
    for chave in ("componentes_novos", "componentes_revisar"):
        pend[chave] = [m for m in pend.get(chave, []) if m not in feitos]
    pend["descricoes_para_modelador"] = rel["para_modelador"]
    # O script decide nome, descrição e área; container e status são do modelador. Sem esta lista, um módulo novo
    # sairia de `componentes_novos` ao ser descrito e o modelador não saberia que ainda falta decidir o resto.
    pend["componentes_sem_container_ou_status"] = sorted(
        c["modulo"] for c in d.get("componentes", [])
        if not c.get("fundir_em") and not (c.get("container") and c.get("status")))
    rel["sem_container_ou_status"] = len(pend["componentes_sem_container_ou_status"])
    destino.write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    tot = {k: sum(ch.get(k, 0) or 0 for ch in rel["chamadas"]) for k in ("input", "cache_criado", "cache_lido", "output")}
    rel["tokens"] = {**tot, "total": sum(tot.values())}
    return rel


def _repo_de(arq: Path) -> Path:
    r = subprocess.run(["git", "-C", str(arq), "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    return Path(r.stdout.strip()) if r.returncode == 0 and r.stdout.strip() else arq.parents[2]


def resumo(rel: dict, idioma: str = "pt") -> str:
    """Uma linha para pessoa ler: o que foi descrito, o que sobrou e quanto custou (tokens do campo usage do CLI)."""
    seg = sum(ch.get("seg", 0) or 0 for ch in rel["chamadas"])
    tok = rel.get("tokens", {}).get("total", 0)
    n = len(rel["chamadas"])
    rev = rel.get("revisados", 0)
    falta = rel.get("sem_container_ou_status", 0)
    if idioma == "en":
        extra = f" ({rev} reviews, {rel.get('mantidos', 0)} kept as written)" if rev else ""
        return (f"described {rel['descritos']} of {rel['alvos']} modules{extra}; {rel['reenviados']} retried, "
                f"{len(rel['para_modelador'])} left for the modeler; {n} call(s), {tok:,} tokens, {seg:.0f} s"
                + (f"; {falta} still need container and status" if falta else ""))
    extra = f" ({rev} revisões, {rel.get('mantidos', 0)} mantidas como estavam)" if rev else ""
    return (f"{rel['descritos']} de {rel['alvos']} módulos descritos{extra}; {rel['reenviados']} reenviados, "
            f"{len(rel['para_modelador'])} para o modelador; {n} chamada(s), "
            + f"{tok:,} tokens, {seg:.0f} s".replace(",", ".")
            + (f"; {falta} ainda sem container e status" if falta else ""))


def main(argv=None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--arq", required=True, help="pasta structurizr do projeto")
    ap.add_argument("--repo", help="raiz do repositório (padrão: raiz do git de --arq)")
    ap.add_argument("--todos", action="store_true", help="descreve todos os componentes, não só os pendentes")
    ap.add_argument("--lote", type=int, default=76, help="módulos por chamada (padrão 76)")
    ap.add_argument("--modelo", default="haiku")
    ap.add_argument("--esforco", default="medium", choices=["low", "medium", "high"])
    ap.add_argument("--simular", action="store_true", help="monta as fichas e o prompt sem chamar o modelo")
    ap.add_argument("--resumo", action="store_true", help="imprime uma linha de resumo em vez do relatório em JSON")
    a = ap.parse_args(argv)
    arq = Path(a.arq).resolve()
    repo = Path(a.repo).resolve() if a.repo else _repo_de(arq)
    try:
        rel = descrever(arq, repo, a.todos, max(1, a.lote), a.modelo, a.esforco, a.simular)
    except ValueError as e:
        print(f"erro: {e}")
        return 2
    print(resumo(rel, esqueleto._idioma(arq)) if a.resumo else json.dumps(rel, ensure_ascii=False, indent=1))
    if rel["simulado"]:
        return 0
    return 3 if rel["para_modelador"] else 0


if __name__ == "__main__":
    sys.exit(main())
