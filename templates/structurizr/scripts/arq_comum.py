"""Peças comuns aos geradores da arquitetura (explorador, leitor e documentos).

Só usa a biblioteca padrão. Lê o workspace.json exportado pelo Structurizr, a configuração
lodemap.json e o resumo curado das métricas (metricas/metricas.json).
"""
from __future__ import annotations

import fnmatch
import functools
import json
import os
import re
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent  # docs/architecture/structurizr
TIPOS_ESTATICOS = ["systemLandscapeViews", "systemContextViews", "containerViews", "componentViews"]
ORDEM_STATUS = ["Pronto", "Em andamento", "Aguardando", "Planejado", "Fora do foco"]

# Idioma das saídas geradas (explorador, leitor e documentos). "pt" é o padrão; "en" está disponível.
# O status guarda a chave canônica em português (é o que os estilos e as tags usam); só o rótulo muda.
IDIOMAS = ("pt", "en")
IDIOMA_PADRAO = "pt"
ROTULOS_STATUS = {
    "pt": {s: s for s in ORDEM_STATUS + ["Externo"]},
    "en": {"Pronto": "Done", "Em andamento": "In progress", "Aguardando": "Waiting", "Planejado": "Planned",
           "Fora do foco": "Out of focus", "Externo": "External"},
}


@functools.lru_cache(maxsize=256)
def glob_regex(glob: str) -> re.Pattern:
    """Glob de arquivo com a semântica do Path.glob: `**/` casa zero ou mais pastas, `*` e `?` não atravessam `/`.

    O fnmatch não serve para isso: nele `*` atravessa `/` e `lib/**/*.js` exige ao menos uma pasta depois de `lib/`.
    """
    out, i = [], 0
    while i < len(glob):
        if glob.startswith("**/", i):
            out.append("(?:[^/]+/)*")
            i += 3
        elif glob.startswith("**", i):
            out.append(".*")
            i += 2
        elif glob[i] == "*":
            out.append("[^/]*")
            i += 1
        elif glob[i] == "?":
            out.append("[^/]")
            i += 1
        elif glob[i] == "[" and "]" in glob[i + 1:]:
            j = glob.index("]", i + 1)
            out.append("[" + glob[i + 1:j].replace("\\", "\\\\") + "]")
            i = j + 1
        else:
            out.append(re.escape(glob[i]))
            i += 1
    return re.compile("".join(out), re.IGNORECASE if os.name == "nt" else 0)


def globs_ignorar(cfg: dict | None) -> list[str]:
    """Os globs de "ignorar" do lodemap.json (lista de textos; ausente ou vazia = nada é ignorado).

    Uma barra no fim é aceita e descartada: o candidato a módulo é comparado sem ela (a pasta `pkg/testdata/` casa
    como `pkg/testdata`).
    """
    bruto = (cfg or {}).get("ignorar") or []
    if isinstance(bruto, str):
        bruto = [bruto]
    return [g.strip().rstrip("/") for g in bruto if isinstance(g, str) and g.strip().rstrip("/")]


def modulo_ignorado(caminho: str, ignorar) -> bool:
    """O candidato a módulo casa algum glob de "ignorar"? `caminho` é o posix relativo à raiz do repositório; numa
    pasta-módulo vale o caminho sem a barra final. Mesma semântica dos globs de "modulos" (`glob_regex`)."""
    if not ignorar:
        return False
    c = caminho.rstrip("/")
    return any(glob_regex(g.rstrip("/")).fullmatch(c) for g in ignorar)


def ler_config(base: Path = BASE) -> dict:
    """lodemap.json com as sobrescritas do ambiente (LODEMAP_IDIOMA)."""
    arq = base / "lodemap.json"
    cfg = json.loads(arq.read_text(encoding="utf-8-sig")) if arq.is_file() else {}
    cfg.setdefault("lite", "http://localhost:8790")
    idioma = os.environ.get("LODEMAP_IDIOMA") or cfg.get("idioma") or IDIOMA_PADRAO
    cfg["idioma"] = idioma if idioma in IDIOMAS else IDIOMA_PADRAO
    return cfg


def ler_workspace(caminho: str | Path) -> dict:
    return json.loads(Path(caminho).read_text(encoding="utf-8-sig"))


def _tags(texto: str) -> list[str]:
    return [t.strip() for t in (texto or "").split(",") if t.strip()]


def coletar(ws: dict) -> tuple[dict, list]:
    """Elementos (pessoas, sistemas, containers e componentes) e relações declaradas, por id."""
    elementos, relacoes = {}, []

    def add(e, tipo, pai=None):
        props = dict(e.get("properties", {}))
        elementos[e["id"]] = {
            "id": e["id"],
            "ident": props.get("structurizr.dsl.identifier", ""),
            "nome": e.get("name", ""),
            "tipo": tipo,
            "pai": pai,
            "grupo": e.get("group", ""),
            "desc": e.get("description", ""),
            "tech": e.get("technology", ""),
            "tags": _tags(e.get("tags", "")),
            "props": props,
            "url": e.get("url", ""),
        }
        for r in e.get("relationships", []):
            relacoes.append({
                "id": r["id"],
                "de": r["sourceId"],
                "para": r["destinationId"],
                "desc": r.get("description", ""),
                "tech": r.get("technology", ""),
                "tags": _tags(r.get("tags", "")),
            })

    m = ws["model"]
    for p in m.get("people", []):
        add(p, "Pessoa")
    for s in m.get("softwareSystems", []):
        add(s, "Sistema")
        for c in s.get("containers", []):
            add(c, "Container", s["id"])
            for k in c.get("components", []):
                add(k, "Componente", c["id"])
    return elementos, relacoes


def _ordem(r) -> list[int]:
    return [int(p) for p in re.findall(r"\d+", str(r.get("order", "0")))] or [0]


def visoes(ws: dict) -> list[dict]:
    out = []
    v = ws["views"]
    for tipo in TIPOS_ESTATICOS:
        for x in v.get(tipo, []):
            out.append({
                "chave": x["key"],
                "tipo": "estatica",
                "titulo": x.get("title") or x["key"],
                "desc": x.get("description", ""),
                "elementos": [e["id"] for e in x.get("elements", [])],
                "relacoes": [r["id"] for r in x.get("relationships", [])],
                "passos": [a.get("elements", []) for a in x.get("animations", [])],
            })
    for x in v.get("dynamicViews", []):
        passos = sorted(x.get("relationships", []), key=_ordem)
        out.append({
            "chave": x["key"],
            "tipo": "dinamica",
            "titulo": x.get("title") or x["key"],
            "desc": x.get("description", ""),
            "elementos": [e["id"] for e in x.get("elements", [])],
            "relacoes": [r["id"] for r in passos],
            "fluxo": [{"rel": r["id"], "ordem": str(r.get("order", "")), "desc": r.get("description", ""),
                       "resposta": bool(r.get("response"))} for r in passos],
        })
    return out


def adrs(pasta: Path) -> list[dict]:
    out = []
    if not pasta.is_dir():
        return out
    for f in sorted(pasta.glob("*.md")):
        texto = f.read_text(encoding="utf-8")
        titulo = next((l.lstrip("# ").strip() for l in texto.splitlines() if l.startswith("#")), f.stem)
        out.append({"arquivo": f.name, "titulo": titulo, "texto": texto})
    return out


_ROTULO_STATUS = {re.sub(r"\s", "", s).lower(): s for s in ORDEM_STATUS}
_ROTULO_STATUS.update({re.sub(r"\s", "", en).lower(): pt for pt, en in ROTULOS_STATUS["en"].items()
                       if pt in ORDEM_STATUS})


def status_de(e: dict) -> str:
    """Chave canônica do status. Aceita a tag ("EmAndamento"), o texto ("Em andamento") e o rótulo em inglês
    ("In progress"), para um modelo escrito em qualquer um dos dois idiomas."""
    st = e["props"].get("status")
    if st:
        return _ROTULO_STATUS.get(re.sub(r"\s", "", st).lower(), st)
    return "Externo" if ("Externo" in e["tags"] or "Nuvem" in e["tags"]) else "Pronto"


def rotulo_status(st: str, idioma: str = IDIOMA_PADRAO) -> str:
    """Rótulo do status no idioma das saídas; status desconhecido volta como veio."""
    return ROTULOS_STATUS.get(idioma, ROTULOS_STATUS[IDIOMA_PADRAO]).get(st, st)


def area_de(e: dict) -> str:
    a = e["props"].get("area", "")
    return re.sub(r"^Area", "", a) if a else ""


# ---------------------------------------------------------------- métricas

def ler_metricas(base: Path = BASE, cfg: dict | None = None) -> list[dict]:
    cfg = cfg if cfg is not None else ler_config(base)
    arq = base / (cfg.get("metricas") or "metricas/metricas.json")
    if not arq.is_file():
        return []
    return json.loads(arq.read_text(encoding="utf-8-sig")).get("metricas", [])


def metricas_por_ident(metricas: list[dict]) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for m in metricas:
        for ident in m.get("componentes", []):
            out.setdefault(ident, []).append(m)
    return out


def numero(v) -> str:
    """Número no formato brasileiro, sem casas desnecessárias."""
    if isinstance(v, bool) or v is None:
        return str(v)
    if isinstance(v, int) or (isinstance(v, float) and v.is_integer()):
        return f"{int(v):,}".replace(",", ".")
    return f"{v:,.2f}".rstrip("0").rstrip(",").replace(",", "X").replace(".", ",").replace("X", ".")


def link_fonte(fonte: dict, cfg: dict) -> str:
    """URL do JSON de evidência no commit (GitHub), ou vazio se não houver repositório configurado."""
    repo = (cfg.get("repo_github") or "").rstrip("/")
    if not repo or not fonte.get("commit") or not fonte.get("arquivo"):
        return ""
    return f"{repo}/blob/{fonte['commit']}/{fonte['arquivo']}"


# ---------------------------------------------------------------- cobertura do modelo
# A mesma regra do tests/test_arquitetura_cobertura.py, para quem precisa saber o que está fora do modelo sem rodar
# o pytest (lodemap_decidir.py). O teste continua com a sua própria cópia, porque ele é entregue sozinho ao projeto;
# um teste de paridade (tests/test_decidir.py) garante que as duas dão a mesma lista. As EXCECOES do teste não são
# visíveis aqui.

IGNORAR_MODULOS = {"__pycache__", "node_modules", ".git", ".venv", "dist", "build"}
_DSL_DECL = re.compile(r'^\s*(\w+)\s*=\s*(component|container|softwareSystem|person)\s+"([^"]*)"')
_DSL_PROP = re.compile(r'^\s*"(codigo|status|ramo)"\s+"([^"]*)"')


def _sem_strings(linha: str) -> str:
    return re.sub(r'"[^"]*"', '""', linha)


def elementos_dsl(arq: Path) -> list[dict]:
    """Elementos de model/*.dsl com as propriedades codigo (lista), status e ramo."""
    saida: list[dict] = []
    for arquivo in sorted((Path(arq) / "model").glob("*.dsl")):
        pilha: list[dict] = []
        profundidade = 0
        for linha in arquivo.read_text(encoding="utf-8").splitlines():
            m = _DSL_DECL.match(linha)
            limpa = _sem_strings(linha)
            if m and limpa.rstrip().endswith("{"):
                el = {"id": m.group(1), "tipo": m.group(2), "nivel": profundidade, "codigo": [], "status": "", "ramo": ""}
                pilha.append(el)
                saida.append(el)
            p = _DSL_PROP.match(linha)
            if p and pilha:
                if p.group(1) == "codigo":
                    pilha[-1]["codigo"].append(p.group(2))
                else:
                    pilha[-1][p.group(1)] = p.group(2)
            profundidade += limpa.count("{") - limpa.count("}")
            while pilha and profundidade <= pilha[-1]["nivel"]:
                pilha.pop()
    return saida


def caminhos_do_codigo(codigo: str) -> list[str]:
    """Caminhos de uma propriedade codigo: vírgula separa, nome sem barra herda a pasta, parênteses são comentário."""
    codigo = re.sub(r"\([^)]*\)", "", codigo)
    pasta, out = "", []
    for parte in re.split(r"[,;]", codigo):
        parte = parte.strip().strip("`")
        if not parte:
            continue
        if "/" in parte:
            pasta = parte if parte.endswith("/") else parte.rsplit("/", 1)[0] + "/"
            out.append(parte)
        else:
            out.append(pasta + parte)
    return out


def caminhos_dos_componentes(arq: Path) -> list[tuple[str, dict]]:
    return [(c, el) for el in elementos_dsl(arq) if el["tipo"] == "component"
            for cod in el["codigo"] for c in caminhos_do_codigo(cod)]


def _quem_cobre(alvo: str, pares, raiz: str) -> str | None:
    for c, el in pares:
        if c.rstrip("/") == raiz:  # a raiz do código sozinha cobriria tudo e não diria nada
            continue
        if any(ch in c for ch in "*?["):
            if fnmatch.fnmatch(alvo, c):
                return el["id"]
        elif c.endswith("/"):
            if alvo.startswith(c) or (alvo.endswith("/") and c.startswith(alvo)):
                return el["id"]
        elif c == alvo or (alvo.endswith("/") and c.startswith(alvo)):
            return el["id"]
    return None


def _config_arq(arq: Path) -> dict:
    return json.loads((Path(arq) / "lodemap.json").read_text(encoding="utf-8-sig"))


def modulos_do_repo(arq: Path, repo: Path) -> list[str]:
    """Os alvos de cobertura: pastas (glob terminado em "/") e arquivos casados pelos globs de "modulos"."""
    repo = Path(repo)
    out = set()
    cfg = _config_arq(arq)
    ignorar = globs_ignorar(cfg)  # candidato que casa algum glob de "ignorar" não é módulo
    for padrao in cfg.get("modulos", []):
        pasta = padrao.endswith("/")
        for p in repo.glob(padrao.rstrip("/")):
            if any(parte in IGNORAR_MODULOS or parte.startswith(".") for parte in p.relative_to(repo).parts):
                continue
            if modulo_ignorado(p.relative_to(repo).as_posix(), ignorar):
                continue
            if pasta and p.is_dir():
                out.add(p.relative_to(repo).as_posix() + "/")
            elif not pasta and p.is_file():
                out.add(p.relative_to(repo).as_posix())
    return sorted(out)


def fora_do_modelo(arq: Path, repo: Path) -> list[str]:
    """Módulos que nenhum componente do modelo cita (a lista do teste de cobertura, sem as EXCECOES)."""
    raiz = _config_arq(arq).get("raiz_codigo", "").strip("/")
    pares = caminhos_dos_componentes(arq)
    return [m for m in modulos_do_repo(arq, repo) if _quem_cobre(m, pares, raiz) is None]


def caminhos_quebrados(arq: Path, repo: Path) -> list[str]:
    """"id: caminho" de cada caminho citado por um componente que não existe (regra 2 do teste de cobertura).

    Componente Planejado/Planned ou com a propriedade ramo fica de fora: o código só existe no design ou em outro ramo.
    """
    repo = Path(repo)
    faltando = []
    for c, el in caminhos_dos_componentes(arq):
        if el["status"] in ("Planejado", "Planned") or el["ramo"]:
            continue
        existe = any(repo.glob(c)) if any(ch in c for ch in "*?[") else (repo / c.rstrip("/")).exists()
        if not existe:
            faltando.append(f"{el['id']}: {c}")
    return faltando
