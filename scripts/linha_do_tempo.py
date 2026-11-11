"""Linha do tempo da arquitetura: o que mudou no mapa a cada versão dele, lido do histórico git (0 tokens).

Uso: python linha_do_tempo.py --mapa <pasta do mapa> [--saida <pasta>] [--max-versoes N] [--rev <ramo|tag|sha>]
                              [--omitir-sem-mudanca] [--resumo]

Fonte por versão: o `explorador/dados.js` de cada commit que tocou a pasta do mapa. É o único artefato que (1) já
carrega o modelo inteiro (elementos, relações, visões e fluxos) num JSON só, (2) o `atualizar.py` regera e o git
versiona a cada rodada, e (3) tem o identificador estável do DSL (`ident`) em cada elemento. O `workspace.json` não
é versionado, e ler o DSL de novo exigiria o Structurizr CLI em cada commit. O id numérico do Structurizr muda
quando o modelo muda, por isso o diff compara sempre pelo `ident`, nunca pelo `id`.

Para cada versão: sha curto, data, assunto, a tag mais próxima do código (`git describe --tags`) e `data_tag`, a data
do commit que a tag marca (a da release; `data` é a do commit do mapa e pode ser a mesma em várias versões), componentes
adicionados, removidos e alterados (nome, tipo, descrição, status, container, tecnologia, área, código), relações
novas e removidas, fluxos adicionados, removidos e alterados (com os passos) e as linhas novas do registro de
atualizações (`docs/99-registro-de-atualizacoes.md`). Uma alteração do mapa ainda não commitada vira a última
versão. Grava `explorador/linha-do-tempo.js` (`window.LODEMAP_LINHA_DO_TEMPO = {...}`, para o explorador abrir
direto do disco) e `explorador/linha-do-tempo.json`, sem carimbo de hora: rodar duas vezes dá o mesmo arquivo.

Código de saída: 0 ok, 2 pasta inexistente, 3 sem repositório git (nada é gravado). Só a biblioteca padrão.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lodemap.idioma import opcao, t, usar_mapa  # noqa: E402

FORMATO = 1
DADOS = "explorador/dados.js"
REGISTRO = "docs/99-registro-de-atualizacoes.md"
CAMPOS = ("nome", "tipo", "desc", "status", "container", "tech", "area", "codigo")
_DESCRIBE = re.compile(r"^(.+)-(\d+)-g[0-9a-f]+$")
_BARRA = re.compile(r"(?<!\\)\|")


class SemGit(Exception):
    """A pasta não está dentro de um repositório git (ou o git não está instalado, ou o rev não existe)."""


# ------------------------------------------------------------------------------------------------------------ git

def _env() -> dict:
    env = dict(os.environ)
    for v in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE"):
        env.pop(v, None)
    return env


def _git(cwd: Path, *args: str) -> subprocess.CompletedProcess:
    try:
        r = subprocess.run(["git", "-c", "core.quotepath=false", *args], cwd=str(cwd), capture_output=True,
                           env=_env())
    except FileNotFoundError as e:
        raise SemGit(t("o git não está instalado ou não está no PATH.", "git is not installed or not on PATH.")) from e
    return subprocess.CompletedProcess(r.args, r.returncode, r.stdout.decode("utf-8", "replace"),
                                       r.stderr.decode("utf-8", "replace"))


class _Objetos:
    """`git cat-file --batch` aberto uma vez: lê `<rev>:<caminho>` de cada commit sem subir um processo por arquivo."""

    def __init__(self, topo: Path):
        try:
            self.p = subprocess.Popen(["git", "cat-file", "--batch"], cwd=str(topo), stdin=subprocess.PIPE,
                                      stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, env=_env())
        except FileNotFoundError as e:
            raise SemGit(t("o git não está instalado ou não está no PATH.", "git is not installed or not on PATH.")) from e

    def ler(self, rev: str, caminho: str) -> bytes | None:
        self.p.stdin.write(f"{rev}:{caminho}\n".encode("utf-8"))
        self.p.stdin.flush()
        cab = self.p.stdout.readline().decode("utf-8", "replace").split()
        if len(cab) != 3 or cab[1] != "blob":
            if len(cab) == 3 and cab[1] != "blob":  # árvore, tag...: o conteúdo vem mesmo assim e tem de ser consumido
                self.p.stdout.read(int(cab[2]) + 1)
            return None
        corpo = self.p.stdout.read(int(cab[2]))
        self.p.stdout.read(1)  # o \n que fecha o objeto
        return corpo

    def fechar(self) -> None:
        try:
            self.p.stdin.close()
            self.p.stdout.close()
        finally:
            self.p.wait()


def _tag(topo: Path, sha: str) -> tuple[str | None, int | None]:
    r = _git(topo, "describe", "--tags", "--long", sha)
    m = _DESCRIBE.match(r.stdout.strip()) if r.returncode == 0 else None
    return (m.group(1), int(m.group(2))) if m else (None, None)


def _data_tag(topo: Path, tag: str | None, memo: dict) -> str | None:
    """Data (AAAA-MM-DD, a mesma de `data`) do commit que a tag marca: a da release, não a do commit do mapa.

    As versões do mapa podem ser gravadas todas no mesmo dia; a tag é o que diz quando a release saiu. Sem tag, ou com a
    tag ilegível, devolve None e o painel mostra só a data do mapa."""
    if not tag:
        return None
    if tag not in memo:
        memo[tag] = None
        for ref in (f"refs/tags/{tag}", tag):
            r = _git(topo, "log", "-1", "--format=%as", f"{ref}^{{commit}}", "--")
            if r.returncode == 0 and r.stdout.strip():
                memo[tag] = r.stdout.strip().splitlines()[0]
                break
    return memo[tag]


# ------------------------------------------------------------------------------------------------------------ leitura

def ler_dados(blob: bytes) -> dict:
    """O JSON dentro de `window.ARQ = {...};`. ValueError se o arquivo não tiver esse formato."""
    texto = blob.decode("utf-8-sig", "replace")
    m = re.search(r"window\.ARQ\s*=\s*", texto)
    if not m:
        raise ValueError(t("não achei `window.ARQ =` no dados.js", "`window.ARQ =` not found in dados.js"))
    try:
        obj, _ = json.JSONDecoder().raw_decode(texto, m.end())
    except json.JSONDecodeError as e:
        raise ValueError(t(f"JSON inválido no dados.js ({e.msg}, linha {e.lineno})",
                           f"invalid JSON in dados.js ({e.msg}, line {e.lineno})")) from e
    if not isinstance(obj, dict):
        raise ValueError(t("o dados.js não traz um objeto", "dados.js does not hold an object"))
    if any(not isinstance(obj.get(k), list) for k in ("elementos", "relacoes", "visoes")):
        raise ValueError(t("dados.js exige listas de elementos, relações e visões", "dados.js requires element, relationship and view lists"))
    if (any(not isinstance(e, dict) or any(e.get(k) is None for k in ("id", "nome", "tipo"))
            for e in obj["elementos"])
            or any(not isinstance(r, dict) or any(r.get(k) is None for k in ("id", "de", "para"))
                   for r in obj["relacoes"])
            or any(not isinstance(v, dict) for v in obj["visoes"])):
        raise ValueError(t("dados.js contém registros incompletos", "dados.js contains incomplete records"))
    return obj


def linhas_do_registro(texto: str | None) -> list[tuple[str, str, str]]:
    """As linhas da tabela do registro de atualizações como (data, o que mudou, motivo). `\\|` fica como está."""
    linhas = []
    for bruta in (texto or "").splitlines():
        s = bruta.strip()
        if not s.startswith("|"):
            continue
        s = s[1:]
        if s.endswith("|") and not s.endswith("\\|"):
            s = s[:-1]
        cel = [c.strip() for c in _BARRA.split(s)]
        if not cel or not cel[0] or set(cel[0]) <= set("-: ") or cel[0].lower() in ("data", "date"):
            continue
        cel += [""] * (3 - len(cel))
        linhas.append((cel[0], cel[1], " | ".join(cel[2:]) if len(cel) > 3 else cel[2]))
    return linhas


def linhas_novas(atual: list, anterior: list) -> list:
    """As linhas do registro que entraram depois de `anterior`. Primeiro tira as iguais; das que sobram, uma linha
    do mesmo dia que já existia conta como editada (um texto traduzido ou corrigido), não como entrada nova."""
    sobra_ant = _so_no_primeiro(anterior, atual, lambda x: x)
    pendentes = Counter(l[0] for l in sobra_ant)
    novas = []
    for l in _so_no_primeiro(atual, anterior, lambda x: x):
        if pendentes[l[0]] > 0:
            pendentes[l[0]] -= 1
        else:
            novas.append(l)
    return novas


def _decodificar(blob: bytes | None) -> str | None:
    return None if blob is None else blob.decode("utf-8-sig", "replace")


# ------------------------------------------------------------------------------------------------------------ modelo

def _vazio(x):
    return x if x not in ("", None) else None


def modelo(arq: dict) -> dict:
    """Normaliza o `window.ARQ`: elementos por `ident`, relações e fluxos já traduzidos de id para ident."""
    els = [e for e in (arq.get("elementos") or []) if isinstance(e, dict)]
    por_id = {str(e.get("id")): e for e in els}

    def ident(e):
        p = e.get("props") if isinstance(e.get("props"), dict) else {}
        return e.get("ident") or p.get("structurizr.dsl.identifier") or f'{e.get("tipo")}:{e.get("nome")}'

    chaves, vistos = {}, Counter()
    for e in els:
        k = ident(e)
        vistos[k] += 1
        chaves[str(e.get("id"))] = k if vistos[k] == 1 else f"{k}#{vistos[k]}"

    def container(e):
        pai, passos = por_id.get(str(e.get("pai"))) if e.get("pai") is not None else None, 0
        primeiro = chaves.get(str(pai.get("id"))) if pai else None
        while pai is not None and passos < 50:
            if pai.get("tipo") == "Container":
                return chaves[str(pai.get("id"))]
            pai = por_id.get(str(pai.get("pai"))) if pai.get("pai") is not None else None
            passos += 1
        return primeiro

    elementos = {}
    for e in els:
        p = e.get("props") if isinstance(e.get("props"), dict) else {}
        elementos[chaves[str(e.get("id"))]] = {
            "ident": chaves[str(e.get("id"))], "nome": e.get("nome"), "tipo": e.get("tipo"),
            "container": container(e), "area": _vazio(p.get("area") or e.get("grupo")),
            "status": _vazio(p.get("status")), "desc": _vazio(e.get("desc")), "tech": _vazio(e.get("tech")),
            "codigo": _vazio(p.get("codigo"))}

    relacoes, por_rel = [], {}
    for r in arq.get("relacoes") or []:
        de, para = chaves.get(str(r.get("de"))), chaves.get(str(r.get("para")))
        if de is None or para is None:
            continue
        rec = {"de": de, "para": para, "de_nome": elementos[de]["nome"], "para_nome": elementos[para]["nome"],
               "desc": _vazio(r.get("desc")), "tech": _vazio(r.get("tech"))}
        relacoes.append(rec)
        por_rel[str(r.get("id"))] = rec

    fluxos = {}
    for v in arq.get("visoes") or []:
        if not isinstance(v, dict) or v.get("tipo") != "dinamica":
            continue
        brutos = [p for p in (v.get("fluxo") or []) if isinstance(p, dict)]

        def ordem(par):
            i, p = par
            try:
                return (0, tuple(int(n) for n in str(p.get("ordem")).split(".")), i)
            except ValueError:
                return (1, (), i)

        passos = []
        for n, (_, p) in enumerate(sorted(enumerate(brutos), key=ordem), 1):
            r = por_rel.get(str(p.get("rel")))
            resposta = bool(p.get("resposta"))
            de, para = ("para", "de") if resposta else ("de", "para")
            passos.append({"ordem": n, "de": r[de] if r else None, "para": r[para] if r else None,
                           "de_nome": r[de + "_nome"] if r else None, "para_nome": r[para + "_nome"] if r else None,
                           "desc": _vazio(p.get("desc")), "resposta": resposta})
        fluxos[str(v.get("chave"))] = {"chave": str(v.get("chave")), "titulo": _vazio(v.get("titulo")),
                                       "desc": _vazio(v.get("desc")), "passos": passos}
    visoes = []
    for v in arq.get("visoes") or []:
        visoes.append({"chave": str(v.get("chave")), "tipo": v.get("tipo"), "titulo": _vazio(v.get("titulo")),
                       "desc": _vazio(v.get("desc")),
                       "elementos": [chaves[str(i)] for i in (v.get("elementos") or []) if str(i) in chaves],
                       "relacoes": [por_rel[str(i)] for i in (v.get("relacoes") or []) if str(i) in por_rel]})
    return {"elementos": elementos, "relacoes": relacoes, "fluxos": fluxos, "visoes": visoes,
            "idioma": arq.get("idioma"), "nome": arq.get("nome")}


# ------------------------------------------------------------------------------------------------------------ diff

def _so_no_primeiro(a: list, b: list, chave) -> list:
    """Os itens de `a` que não têm par em `b`, contando repetições (a mesma relação duas vezes é duas ocorrências)."""
    resto = Counter(chave(x) for x in b)
    fora = []
    for x in a:
        k = chave(x)
        if resto[k] > 0:
            resto[k] -= 1
        else:
            fora.append(x)
    return fora


def _passo(p):
    return (p["de"], p["para"], p["desc"], p.get("resposta", False))


def _passos(ant: list, novo: list) -> dict:
    adicionados, removidos = _so_no_primeiro(novo, ant, _passo), _so_no_primeiro(ant, novo, _passo)
    comum = Counter(map(_passo, ant)) & Counter(map(_passo, novo))

    def so_comuns(lista):
        resto, seq = Counter(comum), []
        for p in lista:
            k = _passo(p)
            if resto[k] > 0:
                resto[k] -= 1
                seq.append(k)
        return seq

    return {"antes": len(ant), "depois": len(novo), "adicionados": adicionados, "removidos": removidos,
            "reordenado": so_comuns(ant) != so_comuns(novo)}


def _ficha(e: dict) -> dict:
    return {k: e[k] for k in ("ident", "nome", "tipo", "container", "area", "status")}


def diferenca(ant: dict | None, novo: dict) -> dict:
    """O que mudou de `ant` para `novo` (modelos de `modelo()`); `ant=None` é a criação: tudo entra."""
    ae = ant["elementos"] if ant else {}
    ne = novo["elementos"]
    adicionados = [_ficha(e) for k, e in ne.items() if k not in ae]
    removidos = [_ficha(e) for k, e in ae.items() if k not in ne]
    alterados = []
    for k, e in ne.items():
        a = ae.get(k)
        if a is None:
            continue
        campos = {c: {"antes": _vazio(a[c]), "depois": _vazio(e[c])} for c in CAMPOS if _vazio(a[c]) != _vazio(e[c])}
        if campos:
            alterados.append({"ident": k, "nome": e["nome"], "tipo": e["tipo"], "campos": campos})

    ar = ant["relacoes"] if ant else []
    chave_rel = lambda r: (r["de"], r["para"], r["desc"], r["tech"])  # noqa: E731
    novas, sumidas = _so_no_primeiro(novo["relacoes"], ar, chave_rel), _so_no_primeiro(ar, novo["relacoes"], chave_rel)

    af = ant["fluxos"] if ant else {}
    nf = novo["fluxos"]
    f_add = [{"chave": k, "titulo": f["titulo"], "passos": len(f["passos"])} for k, f in nf.items() if k not in af]
    f_rem = [{"chave": k, "titulo": f["titulo"], "passos": len(f["passos"])} for k, f in af.items() if k not in nf]
    f_alt = []
    for k, f in nf.items():
        a = af.get(k)
        if a is None:
            continue
        ps = _passos(a["passos"], f["passos"])
        campos = []
        if a["titulo"] != f["titulo"]:
            campos.append("titulo")
        if a["desc"] != f["desc"]:
            campos.append("desc")
        if ps["adicionados"] or ps["removidos"] or ps["reordenado"]:
            campos.append("passos")
        if campos:
            rec = {"chave": k, "titulo": f["titulo"], "campos": campos, "passos": ps}
            if "titulo" in campos:
                rec["titulo_antes"] = a["titulo"]
            f_alt.append(rec)
    return {"componentes": {"adicionados": adicionados, "removidos": removidos, "alterados": alterados},
            "relacoes": {"novas": novas, "removidas": sumidas},
            "fluxos": {"adicionados": f_add, "removidos": f_rem, "alterados": f_alt}}


def contagem(d: dict) -> dict:
    r = {"componentes_adicionados": len(d["componentes"]["adicionados"]),
         "componentes_removidos": len(d["componentes"]["removidos"]),
         "componentes_alterados": len(d["componentes"]["alterados"]),
         "relacoes_novas": len(d["relacoes"]["novas"]), "relacoes_removidas": len(d["relacoes"]["removidas"]),
         "fluxos_adicionados": len(d["fluxos"]["adicionados"]), "fluxos_removidos": len(d["fluxos"]["removidos"]),
         "fluxos_alterados": len(d["fluxos"]["alterados"])}
    r["total"] = sum(r.values())
    return r


def _sem_diff() -> dict:
    return {"componentes": {"adicionados": [], "removidos": [], "alterados": []},
            "relacoes": {"novas": [], "removidas": []},
            "fluxos": {"adicionados": [], "removidos": [], "alterados": []}}


# ------------------------------------------------------------------------------------------------------------ construção

def _commits(mapa: Path, rev: str | None) -> list[tuple[str, str, str]]:
    r = _git(mapa, "log", "--reverse", "--format=%H%x1f%as%x1f%s", rev or "HEAD", "--", ".")
    if r.returncode != 0:
        if rev:
            raise SemGit(t(f"o rev `{rev}` não existe neste repositório.", f"rev `{rev}` does not exist in this repository."))
        return []  # repositório sem nenhum commit ainda
    saida = []
    for linha in r.stdout.splitlines():
        partes = linha.split("\x1f")
        if len(partes) == 3:
            saida.append((partes[0], partes[1], partes[2]))
    return saida


def construir(mapa, max_versoes: int | None = None, rev: str | None = None, omitir_sem_mudanca: bool = False) -> dict:
    """A linha do tempo do mapa em `mapa` (pasta com `explorador/dados.js`), do commit mais antigo ao mais novo."""
    mapa = Path(mapa).resolve()
    r = _git(mapa, "rev-parse", "--show-toplevel", "--show-prefix")
    if r.returncode != 0:
        raise SemGit(t(f"{mapa} não está dentro de um repositório git; sem histórico não há linha do tempo.",
                       f"{mapa} is not inside a git repository; without history there is no timeline."))
    topo_txt, _, prefixo = r.stdout.partition("\n")
    topo, prefixo = Path(topo_txt.strip()), prefixo.strip()
    commits = _commits(mapa, rev)
    total_commits = len(commits)

    versoes: list[dict] = []
    ant_modelo: dict | None = None
    ant_sha: str | None = None
    ant_registro: list = []
    ultimo_blob: bytes | None = None
    objetos = _Objetos(topo)
    datas_tag: dict = {}
    try:
        for sha, data, assunto in commits:
            blob = objetos.ler(sha, prefixo + DADOS)
            reg = linhas_do_registro(_decodificar(objetos.ler(sha, prefixo + REGISTRO)))
            tag, dist = _tag(topo, sha)
            v, ant_modelo, ant_sha = _versao(blob, reg, ant_registro, ant_modelo, ant_sha,
                                             dict(sha=sha[:7], sha_completo=sha, data=data, assunto=assunto,
                                                  tag=tag, tag_distancia=dist, data_tag=_data_tag(topo, tag, datas_tag),
                                                  commitado=True))
            versoes.append(v)
            ant_registro, ultimo_blob = reg, blob
    finally:
        objetos.fechar()

    if not rev:  # alteração ainda não commitada: a última versão, se de fato mudou a arquitetura ou o registro
        arq_dados = mapa / DADOS
        if arq_dados.is_file():
            blob = arq_dados.read_bytes()
            reg_arq = mapa / REGISTRO
            reg = linhas_do_registro(reg_arq.read_text(encoding="utf-8-sig", errors="replace") if reg_arq.is_file() else None)
            if blob != ultimo_blob or reg != ant_registro:
                data = datetime.fromtimestamp(arq_dados.stat().st_mtime).date().isoformat()
                v, _, _ = _versao(blob, reg, ant_registro, ant_modelo, ant_sha,
                                  dict(sha=None, sha_completo=None, data=data, assunto=None, tag=None,
                                       tag_distancia=None, data_tag=None, commitado=False))
                if not (v["dados"] and v["resumo"]["total"] == 0 and not v["registro"]):
                    versoes.append(v)

    if omitir_sem_mudanca:
        versoes = [v for v in versoes if (v["resumo"] or {}).get("total") or v["registro"] or not v["dados"]]
    truncado = len(commits) < total_commits
    if max_versoes and len(versoes) > max_versoes:
        versoes, truncado = versoes[-max_versoes:], True
    for i, v in enumerate(versoes, 1):
        v["indice"] = i
    nome = next((v["_nome"] for v in reversed(versoes) if v.get("_nome")), None)
    for v in versoes:
        v.pop("_nome", None)
    return {"formato": FORMATO,
            "mapa": {"nome": nome, "pasta": prefixo.rstrip("/") or ".", "rev": rev or "HEAD"},
            "total_versoes": len(versoes), "total_commits": total_commits,
            "truncado": truncado, "versoes": versoes}


def _versao(blob, reg, ant_registro, ant_modelo, ant_sha, base: dict):
    """Monta uma versão. Devolve (versão, modelo base da próxima, sha base da próxima)."""
    novas = linhas_novas(reg, ant_registro)
    v = dict(base)
    v.update({"dados": False, "erro": None, "inicial": False, "base": None, "idioma": None, "mudou_idioma": None,
              **_sem_diff(), "resumo": None, "snapshot": None,
              "registro": [{"data": d, "mudou": m, "motivo": mo} for d, m, mo in novas]})
    if blob is None:
        return v, ant_modelo, ant_sha
    try:
        mod = modelo(ler_dados(blob))
    except (ValueError, TypeError, KeyError, AttributeError) as e:
        v["erro"] = str(e)
        return v, ant_modelo, ant_sha
    v.update(diferenca(ant_modelo, mod))
    v.update({"dados": True, "inicial": ant_modelo is None, "base": ant_sha, "idioma": mod["idioma"],
              "resumo": contagem(v), "_nome": mod["nome"],
              "snapshot": {k: mod[k] for k in ("elementos", "relacoes", "fluxos", "visoes")}})
    if ant_modelo is not None and ant_modelo["idioma"] != mod["idioma"]:
        v["mudou_idioma"] = {"de": ant_modelo["idioma"], "para": mod["idioma"]}
    return v, mod, base["sha"]


# ------------------------------------------------------------------------------------------------------------ saída

def _json(dados: dict, indent: int | None) -> str:
    s = json.dumps(dados, ensure_ascii=False, indent=indent, separators=(",", ":") if indent is None else None)
    # `<` e os separadores de linha do JS fora do texto: o arquivo pode ir dentro de um <script> sem quebrar o HTML
    return s.replace("<", "\\u003c").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")


def gravar(dados: dict, pasta: Path) -> tuple[Path, Path]:
    pasta.mkdir(parents=True, exist_ok=True)
    js, js_json = pasta / "linha-do-tempo.js", pasta / "linha-do-tempo.json"
    cab = "// Gerado por scripts/linha_do_tempo.py a partir do histórico git. Não edite à mão.\n"
    with open(js, "w", encoding="utf-8", newline="\n") as f:
        f.write(cab + "window.LODEMAP_LINHA_DO_TEMPO = " + _json(dados, None) + ";\n")
    with open(js_json, "w", encoding="utf-8", newline="\n") as f:
        f.write(_json(dados, 1) + "\n")
    return js, js_json


def tabela(dados: dict) -> str:
    cab = t("  #  sha      data        tag (commits depois)   comp +/-/~   rel +/-   fluxo +/-/~   assunto",
            "  #  sha      date        tag (commits after)    comp +/-/~   rel +/-   flow +/-/~    subject")
    linhas = [cab]
    for v in dados["versoes"]:
        r = v["resumo"]
        tag = f'{v["tag"]} (+{v["tag_distancia"]})' if v["tag"] else "—"
        if r:
            mud = (f'{r["componentes_adicionados"]:>3}/{r["componentes_removidos"]}/{r["componentes_alterados"]:<4}'
                   f'  {r["relacoes_novas"]:>3}/{r["relacoes_removidas"]:<4}'
                   f'  {r["fluxos_adicionados"]:>3}/{r["fluxos_removidos"]}/{r["fluxos_alterados"]:<3}')
        else:
            mud = t("      sem dados.js legível      ", "      no readable dados.js      ")
        assunto = v["assunto"] or t("(não commitado)", "(not committed)")
        linhas.append(f'{v["indice"]:>3}  {v["sha"] or "-------":<7}  {v["data"] or "":<10}  {tag:<22} {mud}  {assunto}')
    return "\n".join(linhas)


def main(argv=None) -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(errors="replace")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(
        description=t("Linha do tempo da arquitetura: o que mudou no mapa a cada versão, lido do git (0 tokens).",
                      "Architecture timeline: what changed in the map at each version, read from git (0 tokens)."))
    ap.add_argument(*opcao("--map", "--mapa"), dest="mapa", required=True,
                    help=t("pasta do mapa (a que tem explorador/dados.js)", "map folder (the one with explorador/dados.js)"))
    ap.add_argument(*opcao("--out", "--saida"), dest="saida",
                    help=t("onde gravar linha-do-tempo.js e .json (padrão: <mapa>/explorador)",
                           "where to write linha-do-tempo.js and .json (default: <map>/explorador)"))
    ap.add_argument(*opcao("--max-versions", "--max-versoes"), dest="max_versoes", type=int, default=120,
                    help=t("guarda só as N versões mais novas; 0 = todas (padrão: 120)",
                           "keep only the N newest versions; 0 = all (default: 120)"))
    ap.add_argument("--rev", help=t("lê o histórico desse ramo, tag ou sha em vez do HEAD (não troca de ramo)",
                                    "read the history of this branch, tag or sha instead of HEAD (does not switch branch)"))
    ap.add_argument(*opcao("--skip-unchanged", "--omitir-sem-mudanca"), dest="omitir", action="store_true",
                    help=t("omite versões que não mudaram a arquitetura nem o registro",
                           "omit versions that changed neither the architecture nor the log"))
    ap.add_argument(*opcao("--summary", "--resumo"), dest="resumo", action="store_true",
                    help=t("imprime uma linha por versão", "print one line per version"))
    args = ap.parse_args(argv)

    mapa = Path(args.mapa).resolve()
    if not mapa.is_dir():
        print(t(f"Erro: a pasta do mapa não existe: {mapa}", f"Error: map folder does not exist: {mapa}"), file=sys.stderr)
        return 2
    usar_mapa(mapa)
    try:
        dados = construir(mapa, args.max_versoes or None, args.rev, args.omitir)
    except SemGit as e:
        print(t("Erro: ", "Error: ") + str(e), file=sys.stderr)
        return 3
    destino = Path(args.saida) if args.saida else mapa / "explorador"
    js, _ = gravar(dados, destino)
    n = dados["total_versoes"]
    print(t(f"Linha do tempo: {n} {'versão' if n == 1 else 'versões'} do mapa em {dados['mapa']['pasta']} -> {js}",
            f"Timeline: {n} map {'version' if n == 1 else 'versions'} in {dados['mapa']['pasta']} -> {js}"))
    if args.resumo:
        print(tabela(dados))
    return 0


if __name__ == "__main__":
    sys.exit(main())
