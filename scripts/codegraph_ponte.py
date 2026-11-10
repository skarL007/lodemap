"""Ponte entre o código e o modelo C4: arestas arquivo -> arquivo, sem LLM e sem gastar token.

Fonte das arestas (--fonte):
  auto       (padrão) usa o CodeGraph se <repo>/.codegraph/codegraph.db existir; senão cai para ast;
  codegraph  lê o índice em modo somente leitura (calls, imports, instantiates e despacho resolvido);
  ast        só a biblioteca padrão, sem dependência nova: Python por `ast` (import e from-import), JS/TS por
             regex (import ... from '...', require('...') e import('...') com caminho relativo), e por regex,
             depois de tirar comentários e strings: Go (import com o module path do go.mod), Rust (use crate::,
             super::, self::, mod x; e crates do workspace), Java e Kotlin (import resolvido pelo pacote declarado
             ou pela árvore src/main/java), C# (using resolvido pelos namespace declarados) e C/C++ (#include "x.h").
             Import que não resolve para um arquivo do repositório é ignorado, nunca inventado.

As arestas são SUGESTÃO, não verdade: o índice deixa muita referência sem resolver (num repositório de 188 componentes, 84 mil
unresolved_refs contra 75 mil arestas resolvidas) e o modo ast só vê imports. Cada par sai com `confianca`:
  alta   chamadas (calls) com 3 arestas ou mais;
  media  imports (ou chamadas com 2 arestas);
  baixa  uma aresta só.
O modelador confirma e dá o verbo; nada entra no DSL de forma automática.

Uso:
  python codegraph_ponte.py --inventario [--repo <raiz>] [--arq <pasta>] [--json inventario-rascunho.json]
  python codegraph_ponte.py --relacoes --arq <pasta structurizr> [--saida relacoes-codigo.json] [--minimo 1]
  python codegraph_ponte.py --impacto <arquivo> --arq <pasta structurizr> [--profundidade 1]

O repositório é a raiz do git de --arq (ou --repo). A skill NUNCA roda `codegraph init`: indexar é decisão do dono.
Só usa a biblioteca padrão.
"""
from __future__ import annotations

import argparse
import ast
import bisect
import fnmatch
import functools
import json
import os
import posixpath
import re
import sqlite3
import subprocess
import sys
import tomllib
import warnings
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

IGNORAR = {"__pycache__", "node_modules", ".git", ".venv", "venv", "dist", "build", ".codegraph", ".structurizr"}
EXT_PY = {".py"}
EXT_JS = {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".mts", ".cts"}
EXT_GO = {".go"}
EXT_RS = {".rs"}
EXT_JAVA = {".java"}
EXT_KT = {".kt", ".kts"}
EXT_CS = {".cs"}
EXT_C = {".c", ".h"}
EXT_CPP = {".cc", ".cpp", ".cxx", ".hpp", ".hh", ".hxx", ".inl"}
# extensão -> nome da linguagem (o mesmo nome que o CodeGraph usa em files.language, quando existe)
LINGUAGEM_EXT = {**{e: "python" for e in EXT_PY}, **{e: "javascript" for e in EXT_JS}, **{e: "go" for e in EXT_GO},
                 **{e: "rust" for e in EXT_RS}, **{e: "java" for e in EXT_JAVA}, **{e: "kotlin" for e in EXT_KT},
                 **{e: "csharp" for e in EXT_CS}, **{e: "c" for e in EXT_C}, **{e: "cpp" for e in EXT_CPP}}
# Pastas de saída de build que só são ignoradas quando o irmão prova que são build (um `target/` em Python é código).
IGNORAR_COM_MARCA = {"target": ("Cargo.toml", "pom.xml", "build.gradle", "build.gradle.kts"), "vendor": ("go.mod",)}
MANIFESTOS = {"go.mod", "Cargo.toml"}
TIPOS_CODEGRAPH = {"calls": "calls", "instantiates": "calls", "imports": "imports"}


# ------------------------------------------------------------------ repositório e workspace

def raiz_repo(ponto: Path) -> Path:
    r = subprocess.run(["git", "-C", str(ponto), "rev-parse", "--show-toplevel"], capture_output=True, text=True,
                       encoding="utf-8")
    if r.returncode == 0 and r.stdout.strip():
        return Path(r.stdout.strip())
    for p in [ponto.resolve(), *ponto.resolve().parents]:
        if (p / ".git").exists():
            return p
    return ponto.resolve()


def achar_workspace(arq: Path) -> Path | None:
    for c in (arq / ".structurizr" / "export" / "workspace.json", arq / "workspace.json"):
        if c.is_file():
            return c
    return None


def componentes(ws: dict) -> list[dict]:
    """Componentes do workspace.json: ident, nome, container, grupo, descricao, tags, props."""
    out = []
    for s in ws.get("model", {}).get("softwareSystems", []):
        for c in s.get("containers", []):
            for k in c.get("components", []):
                p = dict(k.get("properties", {}))
                out.append({
                    "id": k["id"], "ident": p.get("structurizr.dsl.identifier", k["id"]), "nome": k.get("name", ""),
                    "container": c.get("name", ""), "containerId": c["id"], "grupo": k.get("group", ""),
                    "desc": k.get("description", ""), "tech": k.get("technology", ""),
                    "tags": [t.strip() for t in (k.get("tags") or "").split(",") if t.strip()], "props": p,
                })
    return out


def caminhos_codigo(codigo: str) -> list[str]:
    """Mesma regra do teste de cobertura: nome sem barra herda a pasta do anterior; parênteses são comentário."""
    codigo = re.sub(r"\([^)]*\)", "", codigo or "")
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


def _casa(caminho: str, arquivo: str) -> bool:
    if any(ch in caminho for ch in "*?["):
        return fnmatch.fnmatch(arquivo, caminho)
    if caminho.endswith("/"):
        return arquivo.startswith(caminho)
    return arquivo == caminho


def mapear_arquivos(arquivos, comps: list[dict], raiz_codigo: str = "") -> tuple[dict, set, set]:
    """arquivo -> ident do componente de caminho mais específico.

    Devolve (mapa, ambiguos, sem_componente). Arquivo que dois componentes disputam com a mesma especificidade
    (vários componentes apontando para o mesmo server.py) é ambíguo e fica fora das contas.
    """
    raiz = raiz_codigo.strip("/")
    pares = [(c, comp["ident"]) for comp in comps for cod in [comp["props"].get("codigo", "")]
             for c in caminhos_codigo(cod) if c.rstrip("/") != raiz]
    mapa, ambiguos, sem = {}, set(), set()
    for f in arquivos:
        melhor, donos = -1, set()
        for c, ident in pares:
            if _casa(c, f):
                esp = len(c.rstrip("/"))
                if esp > melhor:
                    melhor, donos = esp, {ident}
                elif esp == melhor:
                    donos.add(ident)
        if not donos:
            sem.add(f)
        elif len(donos) > 1:
            ambiguos.add(f)
        else:
            mapa[f] = next(iter(donos))
    return mapa, ambiguos, sem


# ------------------------------------------------------------------ fonte: CodeGraph

def caminho_db(repo: Path, db: Path | None = None) -> Path:
    """Índice do CodeGraph: o de --db, se dado, ou <repo>/.codegraph/codegraph.db."""
    return Path(db) if db else repo / ".codegraph" / "codegraph.db"


def abrir_db(db: Path) -> sqlite3.Connection:
    return sqlite3.connect(f"file:{db.resolve().as_posix()}?mode=ro", uri=True)


def arestas_codegraph(db: Path) -> dict[tuple[str, str], Counter]:
    con = abrir_db(db)
    try:
        q = ("SELECT s.file_path, t.file_path, e.kind, COUNT(*) FROM edges e "
             "JOIN nodes s ON s.id = e.source JOIN nodes t ON t.id = e.target "
             "WHERE e.kind IN ('calls','instantiates','imports') AND s.file_path <> t.file_path "
             "GROUP BY 1, 2, 3")
        out: dict[tuple[str, str], Counter] = defaultdict(Counter)
        for a, b, k, n in con.execute(q):
            out[(a, b)][TIPOS_CODEGRAPH[k]] += n
        return out
    finally:
        con.close()


# ------------------------------------------------------------------ fonte: ast (só biblioteca padrão)

def _varrer(repo: Path) -> tuple[list[str], list[str]]:
    """(arquivos-fonte, manifestos go.mod/Cargo.toml) do repositório, podando as pastas ignoradas sem entrar nelas."""
    fontes, manifestos = [], []
    for raiz, dirs, arqs in os.walk(repo):
        base = Path(raiz).relative_to(repo).as_posix()
        base = "" if base == "." else base + "/"

        def ignorada(d: str) -> bool:
            if d in IGNORAR or d.startswith("."):
                return True
            if d in IGNORAR_COM_MARCA and any(a in IGNORAR_COM_MARCA[d] for a in arqs):
                return True
            return d == "obj" and any(a.endswith(".csproj") for a in arqs)

        dirs[:] = sorted(d for d in dirs if not ignorada(d))
        for a in arqs:
            if a.startswith("."):
                continue
            if a in MANIFESTOS:
                manifestos.append(base + a)
            elif os.path.splitext(a)[1] in LINGUAGEM_EXT:
                fontes.append(base + a)
    return sorted(fontes), sorted(manifestos)


def listar_fontes(repo: Path) -> list[str]:
    return _varrer(repo)[0]


def _resolver_py(modulo: str, nivel: int, origem: str, existentes: set[str]) -> str | None:
    base = Path(origem).parent
    if nivel:
        for _ in range(nivel - 1):
            base = base.parent
        raizes = [base]
    else:
        raizes = [base, *base.parents]  # de onde o arquivo está até a raiz do repositório
    partes = modulo.split(".") if modulo else []
    for r in raizes:
        # `import types` em `app/core.py` (app/ é pacote, tem __init__.py) é a stdlib, não `app/types.py`: um pacote
        # importado como tal não põe a própria pasta em sys.path. Só vale para nome da stdlib: um irmão com nome próprio
        # (`import fontes_falsas` num teste que faz sys.path.insert da própria pasta) continua resolvendo.
        if (not nivel and partes and partes[0] in sys.stdlib_module_names and r.as_posix() != "."
                and f"{r.as_posix()}/__init__.py" in existentes):
            continue
        rel = r.joinpath(*partes).as_posix() if partes else r.as_posix()
        rel = "" if rel == "." else rel
        cands = [f"{rel}.py", f"{rel}/__init__.py"] if partes else [f"{rel}/__init__.py".lstrip("/")]
        for cand in cands:
            if cand in existentes:
                return cand
    # Monorepo com várias raízes de código (`packages/domain/ankirag_domain/` importado como `ankirag_domain` de `evals/`,
    # via instalação editável): sem esta etapa só enxergava imports dentro da mesma raiz. Só vale para pacote de topo
    # único no repositório e fora da stdlib; um nome ambíguo continua sem aresta (melhor perder que inventar).
    if not nivel and partes and partes[0] not in sys.stdlib_module_names:
        raiz_unica = _raizes_pacote_py(existentes).get(partes[0])
        if raiz_unica is not None:
            rel = "/".join(filter(None, [raiz_unica, *partes]))
            for cand in (f"{rel}.py", f"{rel}/__init__.py"):
                if cand in existentes:
                    return cand
    return None


_RAIZES_PY: dict[int, tuple[int, dict[str, str | None]]] = {}


def _raizes_pacote_py(existentes: set[str]) -> dict[str, str | None]:
    """nome de pacote de topo -> pasta que o contém (`""` = raiz do repo); `None` quando há mais de uma pasta candidata."""
    chave = id(existentes)
    guardado = _RAIZES_PY.get(chave)
    if guardado and guardado[0] == len(existentes):
        return guardado[1]
    mapa: dict[str, str | None] = {}
    for f in existentes:
        if not f.endswith("/__init__.py"):
            continue
        pasta = posixpath.dirname(f)
        pai = posixpath.dirname(pasta)
        if f"{pai}/__init__.py".lstrip("/") in existentes:
            continue  # não é pacote de topo
        nome = posixpath.basename(pasta)
        mapa[nome] = pai if mapa.get(nome, pai) == pai else None
    _RAIZES_PY.clear()  # um repositório por vez: não deixa crescer
    _RAIZES_PY[chave] = (len(existentes), mapa)
    return mapa


def arestas_ast_python(repo: Path, arquivo: str, existentes: set[str], saida) -> None:
    try:
        with warnings.catch_warnings():  # `"\l"` num arquivo analisado não é problema da ferramenta: sem ruído no stderr
            warnings.simplefilter("ignore")
            arvore = ast.parse((repo / arquivo).read_text(encoding="utf-8-sig", errors="replace"))
    except (SyntaxError, ValueError):
        return
    for no in ast.walk(arvore):
        alvos = []
        if isinstance(no, ast.Import):
            for a in no.names:
                alvos.append(_resolver_py(a.name, 0, arquivo, existentes))
        elif isinstance(no, ast.ImportFrom):
            mod = no.module or ""
            principal = _resolver_py(mod, no.level, arquivo, existentes)
            achou_sub = False
            for a in no.names:  # `from pacote import submodulo`
                sub = _resolver_py(f"{mod}.{a.name}" if mod else a.name, no.level, arquivo, existentes)
                if sub:
                    alvos.append(sub)
                    achou_sub = True
            if not achou_sub:
                alvos.append(principal)
        for alvo in alvos:
            if alvo and alvo != arquivo:
                saida[(arquivo, alvo)]["imports"] += 1


_JS_IMPORT = re.compile(r"""(?:import\s+(?:[^'"()]*?\s+from\s+)?|require\s*\(\s*|import\s*\(\s*|export\s+[^'"]*?\s+from\s+)['"](\.{1,2}/[^'"]*|\.{1,2})['"]""")


def _resolver_js(caminho: str, origem: str, existentes: set[str]) -> str | None:
    base = (Path(origem).parent / caminho).as_posix()
    partes: list[str] = []
    for p in base.split("/"):
        if p == "..":
            if partes:
                partes.pop()
        elif p not in ("", "."):
            partes.append(p)
    rel = "/".join(partes)
    cands = [rel] + [rel + e for e in sorted(EXT_JS) + [".json"]] + [f"{rel}/index{e}" for e in sorted(EXT_JS)]
    # TypeScript ESM escreve a extensão da saída: `./fetcher.js` aponta para `fetcher.ts` (e `.mjs`->`.mts`, `.cjs`->`.cts`).
    raiz, ext = posixpath.splitext(rel)
    cands += [raiz + e for e in _JS_PARA_TS.get(ext, ())]
    for c in cands:
        if c in existentes:
            return c
    return None


_JS_PARA_TS = {".js": (".ts", ".tsx"), ".jsx": (".tsx",), ".mjs": (".mts",), ".cjs": (".cts",)}
_JS_TOKEN = re.compile(r"""//[^\n]*|/\*[\s\S]*?(?:\*/|\Z)|'(?:\\[\s\S]|[^'\\\n])*'?|"(?:\\[\s\S]|[^"\\\n])*"?|`(?:\\[\s\S]|[^`\\])*`?""")
# onde uma string é o especificador de um import: `from '..'`, `import '..'`, `require('..')`, `import('..')`
_JS_CONTEXTO = re.compile(r"(?:\b(?:from|import)|\b(?:require|import)\s*\()\s*$")


def _limpar_js(texto: str) -> str:
    """Tira comentários e esvazia strings e templates, menos o especificador de import/require: um `import './x'` em
    comentário, em string ou em template nunca vira aresta. Regex literal com aspas dentro não é tratado."""
    out, pos, cauda = [], 0, ""
    for m in _JS_TOKEN.finditer(texto):
        antes = texto[pos:m.start()]
        out.append(antes)
        cauda = (cauda + antes)[-48:]
        tok = m.group(0)
        quebras = "\n" * tok.count("\n")
        if tok.startswith("//"):
            nova = ""
        elif tok.startswith("/*"):
            nova = quebras
        elif tok[0] in "'\"" and _JS_CONTEXTO.search(cauda):
            nova = tok
        else:
            nova = tok[0] * 2 + quebras
        out.append(nova)
        cauda = (cauda + nova)[-48:]
        pos = m.end()
    out.append(texto[pos:])
    return "".join(out)


def arestas_ast_js(repo: Path, arquivo: str, existentes: set[str], saida) -> None:
    texto = _limpar_js((repo / arquivo).read_text(encoding="utf-8-sig", errors="replace"))
    for m in _JS_IMPORT.finditer(texto):
        alvo = _resolver_js(m.group(1), arquivo, existentes)
        if alvo and alvo != arquivo:
            saida[(arquivo, alvo)]["imports"] += 1


# ------------------------------------------------------------------ fonte: ast, outras linguagens (regex)
#
# Cada linguagem tem um extrator de imports e um resolvedor para arquivo do repositório. Antes do regex o texto passa
# por `_limpar`, que tira comentários e esvazia strings: um `import "x"` dentro de comentário ou de string multilinha
# nunca vira aresta. Sem preprocessador, sem compilação e sem execução: o que depende disso fica de fora (ver
# references/arestas-codigo.md).

_PADROES_LIMPAR: dict[str, re.Pattern] = {}
_BLOCO_ABRE_FECHA = re.compile(r"/\*|\*/")
_BLOCO_FECHA = re.compile(r"\*/")
_ATRIBUTO_PATH = re.compile(r"#\s*\[\s*path\s*=\s*$")


def _padrao_limpar(ling: str) -> re.Pattern:
    if ling not in _PADROES_LIMPAR:
        alts = [r"(?P<lc>//[^\n]*)", r"(?P<bc>/\*)"]
        if ling == "rust":
            alts.append(r'(?P<raw>(?<!\w)b?r(?P<h>#*)")')
        if ling in ("java", "kotlin", "csharp"):
            alts.append(r'(?P<triplo>"{3,})')
        if ling == "csharp":
            alts.append(r'(?P<verb>(?:\$@|@\$|@)")')
        if ling == "go":
            alts.append(r"(?P<crua>`)")
        if ling == "c":
            alts.append(r'(?P<craw>(?<!\w)(?:u8|u|U|L)?R"(?P<d>[^()\\\s"]{0,16})\()')
        alts.append(r'(?P<s>"(?:\\[\s\S]|[^"\\\n])*"?)')
        alts.append(r"(?P<ch>'(?:\\[^'\n]+|[^'\\\n])')")
        _PADROES_LIMPAR[ling] = re.compile("|".join(alts))
    return _PADROES_LIMPAR[ling]


def _limpar(texto: str, ling: str) -> str:
    """Tira comentários e esvazia strings (vira `""`), preservando as quebras de linha. Go e C mantêm a string de uma
    linha só, porque o caminho do import está nela; Rust mantém a do `#[path = "..."]`."""
    pad = _padrao_limpar(ling)
    fecha = _BLOCO_ABRE_FECHA if ling in ("rust", "kotlin") else _BLOCO_FECHA  # Rust e Kotlin aninham /* */
    manter = ling in ("go", "c")
    out, pos = [], 0
    while True:
        m = pad.search(texto, pos)
        if not m:
            out.append(texto[pos:])
            break
        out.append(texto[pos:m.start()])
        tipo = m.lastgroup
        fim = m.end()
        if tipo == "lc":
            pass
        elif tipo == "bc":
            prof, i = 1, m.end()
            while prof:
                n = fecha.search(texto, i)
                if not n:
                    i = len(texto)
                    break
                prof += 1 if n.group() == "/*" else -1
                i = n.end()
            fim = i
            out.append(" " + "\n" * texto.count("\n", m.start(), fim))
        elif tipo == "ch":
            out.append("''")
        elif tipo == "s":
            if manter or (ling == "rust" and _ATRIBUTO_PATH.search(texto[max(0, m.start() - 40):m.start()])):
                out.append(m.group())
            else:
                out.append('""')
        else:  # strings brutas ou multilinha: o conteúdo some, as linhas ficam
            if tipo == "raw":
                f = texto.find('"' + m.group("h"), m.end())
                fim = len(texto) if f < 0 else f + 1 + len(m.group("h"))
            elif tipo == "triplo":
                f = texto.find(m.group(), m.end())
                fim = len(texto) if f < 0 else f + len(m.group())
            elif tipo == "verb":
                i = m.end()
                while True:
                    f = texto.find('"', i)
                    if f < 0:
                        fim = len(texto)
                        break
                    if texto[f + 1:f + 2] == '"':
                        i = f + 2
                        continue
                    fim = f + 1
                    break
            elif tipo == "craw":
                f = texto.find(")" + m.group("d") + '"', m.end())
                fim = len(texto) if f < 0 else f + len(m.group("d")) + 2
            else:  # crua: crase do Go
                f = texto.find("`", m.end())
                fim = len(texto) if f < 0 else f + 1
                lit = texto[m.start():fim]
                if manter and "\n" not in lit:
                    out.append(lit)
                    pos = fim
                    continue
            out.append('""' + "\n" * texto.count("\n", m.start(), fim))
        pos = fim
    return "".join(out)


class _Contexto:
    """O que os extratores compartilham: arquivos existentes, manifestos e o texto já limpo de cada arquivo."""

    def __init__(self, repo: Path, existentes: set[str], manifestos: list[str], saida):
        self.repo, self.existentes, self.manifestos, self.saida = repo, existentes, manifestos, saida
        self._textos: dict[str, str] = {}

    def bruto(self, rel: str) -> str:
        try:
            return (self.repo / rel).read_text(encoding="utf-8-sig", errors="replace")
        except OSError:
            return ""

    def texto(self, rel: str, ling: str) -> str:
        if rel not in self._textos:
            self._textos[rel] = _limpar(self.bruto(rel), ling)
        return self._textos[rel]

    def aresta(self, origem: str, destino: str | None) -> None:
        if destino and destino != origem:
            self.saida[(origem, destino)]["imports"] += 1


def _junta(base: str, nome: str) -> str:
    return f"{base}/{nome}" if base else nome


def _idents(texto: str) -> set[str]:
    return set(re.findall(r"[A-Za-z_]\w*", texto))


# ---- Go

_GO_IMPORT = re.compile(r'(?m)^[ \t]*import[ \t]*(?:\(([^)]*)\)|(?:([\w.]+)[ \t]+)?(["`])([^"`\n]+)\3)')
_GO_SPEC = re.compile(r'(?:([\w.]+)[ \t]+)?["`]([^"`\n]+)["`]')
_GO_MODULE = re.compile(r'(?m)^[ \t]*module[ \t]+"?([^\s"]+)"?')
_GO_PACOTE = re.compile(r"(?m)^[ \t]*package[ \t]+([A-Za-z_]\w*)")
_GO_STR_LINHA = re.compile(r'"(?:\\.|[^"\\\n])*"|`[^`\n]*`')  # o _limpar do Go deixa a string de uma linha (o import precisa dela)
_GO_ID = r"[A-Za-z_]\w*"
_GO_LISTA = rf"{_GO_ID}(?:[ \t]*,[ \t]*{_GO_ID})*"
_GO_IDENT = re.compile(_GO_ID)
_GO_IDENT_INICIO = re.compile(rf"(?<!\w){_GO_ID}")
_GO_TOPO_FUNC = re.compile(rf"func[ \t]+({_GO_ID})[ \t]*[\[(]")  # `func (r T) Nome(` é método: não casa
_GO_TOPO_TYPE = re.compile(rf"type[ \t]+({_GO_ID})")
_GO_TOPO_VAR = re.compile(rf"(?:var|const)[ \t]+({_GO_LISTA})")
_GO_GRUPO = re.compile(r"(var|const|type)[ \t]*\([ \t]*$")
_GO_ITEM = {"type": re.compile(rf"[ \t]*({_GO_ID})"), "var": re.compile(rf"[ \t]*({_GO_LISTA})")}
_GO_ITEM["const"] = _GO_ITEM["var"]
_GO_CONTINUA = (",", "+", "-", "*", "/", "%", "&", "|", "^", "<", ">", "=", ".")  # fim de linha que continua a expressão
_GO_CURTA = re.compile(rf"(?<![\w.])((?:{_GO_ID}\s*,\s*)*{_GO_ID})\s*:=")  # a, b := ...
_GO_VAR = re.compile(rf"(?<![\w.])(?:var|const)[ \t]+({_GO_LISTA})")
_GO_CAMPO = re.compile(rf"(?m)^[ \t]*({_GO_LISTA})[ \t]+(?=\*(?!=)|\[|\w|<-chan)")  # `nome Tipo` (campo, var local)
_GO_CHAVE = re.compile(rf"(?m)(?:^|[{{,])[ \t\r\n]*({_GO_ID})[ \t]*:(?!=)")  # `nome:` de literal composto
_GO_FUNC = re.compile(r"(?<![\w.])func\b")
_GO_METODO = re.compile(rf"(?<![\w.])func[ \t]*\([^)\n]*\)[ \t]*({_GO_ID})")  # `func (r T) Nome`: grupo 1 = Nome
_GO_CORPO = re.compile(r"(?<![\w.])(struct|interface)\s*\{")
_GO_MEMBRO_STRUCT = re.compile(rf"[ \t]*({_GO_LISTA})[ \t]+(?=\S)")
_GO_MEMBRO_INTERFACE = re.compile(rf"[ \t]*({_GO_ID})[ \t]*(?=[\[(])")


def _go_so_codigo(texto: str) -> str:
    """O texto limpo do Go sem o que não é uso de símbolo: a cláusula `package x` (o `main` de `package main` não é
    chamada de `main`), os `import` (alias e caminho) e o conteúdo das strings de uma linha. Mantém as quebras de linha."""
    def branco(m):
        return re.sub(r"[^\n]", " ", m.group())
    texto = _GO_IMPORT.sub(branco, texto)
    texto = _GO_PACOTE.sub(branco, texto, count=1)
    return _GO_STR_LINHA.sub('""', texto)


def _go_topo(t: str) -> set[str]:
    """Nomes declarados no topo do arquivo: `func Nome(`/`func Nome[`, `type`, `var`, `const` e os blocos `type (`,
    `var (`, `const (` (só o nível do bloco declara; struct/interface aninhados e argumentos multilinha ficam de fora).
    `t` vem sem comentários e sem strings; método (`func (r T) Nome(`), `_` e `init` não declaram nada."""
    nomes: set[str] = set()
    prof, grupo, anterior = 0, None, ""
    for linha in t.split("\n"):
        if prof == 0:
            grupo = None
            m = _GO_GRUPO.match(linha)
            if m:
                grupo = m.group(1)
            else:
                m = _GO_TOPO_FUNC.match(linha) or _GO_TOPO_TYPE.match(linha) or _GO_TOPO_VAR.match(linha)
                if m:
                    nomes.update(_GO_IDENT.findall(m.group(1)))
        elif prof == 1 and grupo and not anterior.endswith(_GO_CONTINUA):
            m = _GO_ITEM[grupo].match(linha)
            if m:
                nomes.update(_GO_IDENT.findall(m.group(1)))
        if linha.strip():
            anterior = linha.rstrip()
        prof = max(0, prof + sum(map(linha.count, "([{")) - sum(map(linha.count, ")]}")))
    nomes.discard("_")
    nomes.discard("init")
    return nomes


def _go_para_uso(t: str) -> str:
    """O texto de `_go_so_codigo` sem os nomes que só RÓTULAM, trocados por espaços (as linhas não mudam): nome de método
    depois do receptor (`func (r T) Nome(`), nome de campo de struct (`Nome Tipo`), nome de método de interface
    (`Nome(...)`) e chave de literal composto (`Nome: v`, fora de `case`). Sem isso `Route(...)` na interface ou `New: f`
    num literal contariam como uso de um `Route`/`New` declarado em outro arquivo."""
    buf = list(t)

    def apaga(a: int, b: int) -> None:
        for i in range(a, b):
            if buf[i] != "\n":
                buf[i] = " "

    for m in _GO_METODO.finditer(t):
        apaga(*m.span(1))
    for m in _GO_CORPO.finditer(t):
        abre = m.end() - 1
        corpo = t[abre + 1:_go_fechar(t, abre, "{", "}")]
        membro = _GO_MEMBRO_INTERFACE if m.group(1) == "interface" else _GO_MEMBRO_STRUCT
        pos, prof = abre + 1, 0
        for linha in corpo.split("\n"):
            if prof == 0:
                mm = membro.match(linha)
                if mm:
                    apaga(pos + mm.start(1), pos + mm.end(1))
            prof += sum(map(linha.count, "([{")) - sum(map(linha.count, ")]}"))
            pos += len(linha) + 1
    for m in _GO_CHAVE.finditer(t):
        if not t[t.rfind("\n", 0, m.start(1)) + 1:m.start(1)].lstrip().startswith("case"):
            apaga(*m.span(1))
    return "".join(buf)


def _go_usos(t: str) -> dict[str, int]:
    """Identificadores usados no texto -> posição do primeiro uso. `.Nome` (seletor de campo, método ou de outro pacote,
    com ou sem quebra de linha antes do nome) não é uso; `...Tipo` (variádico) é."""
    usos: dict[str, int] = {}
    for m in _GO_IDENT_INICIO.finditer(t):
        i = m.start() - 1
        while i >= 0 and t[i] in " \t\r\n":
            i -= 1
        if i >= 0 and t[i] == "." and not (i > 0 and t[i - 1] == "."):
            continue
        usos.setdefault(m.group(), m.start())
    return usos


def _go_fechar(t: str, i: int, abre: str, fecha: str) -> int:
    prof = 0
    for j in range(i, len(t)):
        if t[j] == abre:
            prof += 1
        elif t[j] == fecha:
            prof -= 1
            if prof == 0:
                return j
    return len(t)


def _go_assinaturas(t: str):
    """Os parênteses (receptor, parâmetros, resultados) e os colchetes de tipos de cada `func`, sem o delimitador."""
    n = len(t)
    for m in _GO_FUNC.finditer(t):
        i, grupos, nome = m.end(), 0, False
        while grupos < 4:
            while i < n and t[i] in " \t\r\n":
                i += 1
            if i >= n:
                break
            c = t[i]
            if c == "(" or (c == "[" and nome and t[i - 1] not in " \t\r\n"):
                j = _go_fechar(t, i, c, ")" if c == "(" else "]")
                yield t[i + 1:j]
                i, grupos = j + 1, grupos + 1
            elif not nome and _GO_IDENT.match(t, i):
                i, nome = _GO_IDENT.match(t, i).end(), True
            else:
                break


def _go_nomes_de_parametros(grupo: str) -> set[str]:
    """`(a, b int, c string)` -> {a, b, c}. Só vale se algum item tem nome E tipo; `(int, error)` não liga nada."""
    partes, atual, prof = [], [], 0
    for c in grupo:
        prof += c in "([{"
        prof -= c in ")]}"
        if c == "," and prof == 0:
            partes.append("".join(atual))
            atual = []
        else:
            atual.append(c)
    partes.append("".join(atual))
    if not any(len(p.split()) >= 2 for p in partes):
        return set()
    return {p.split()[0] for p in partes if p.split() and re.fullmatch(_GO_ID, p.split()[0])}


def _go_ligados(t: str) -> set[str]:
    """Nomes que o arquivo liga localmente: `nome :=`, `var nome`, `nome Tipo` (campo ou var), parâmetro e resultado
    de assinatura, `nome:` de literal. Usado só para ignorar nome NÃO exportado (prefere perder aresta a inventar)."""
    nomes: set[str] = set()
    for rx in (_GO_CURTA, _GO_VAR, _GO_CAMPO):
        for m in rx.finditer(t):
            nomes.update(_GO_IDENT.findall(m.group(1)))
    nomes.update(m.group(1) for m in _GO_CHAVE.finditer(t))
    for g in _go_assinaturas(t):
        nomes |= _go_nomes_de_parametros(g)
    return nomes


def _arestas_go(ctx: _Contexto, arquivos: list[str]) -> None:
    """Arquivo .go -> arquivo .go, por SÍMBOLO. Teste (`_test.go`) nunca recebe aresta; quem declara é o topo do arquivo.
    - Mesmo pacote (mesma pasta e mesmo `package`, sem go.mod): f usa um nome declarado no topo de outro arquivo g.
    - Import interno (module path do go.mod): `alias.Nome` vai para o arquivo da pasta alvo que declara `Nome`; o
      qualificador é o alias explícito ou o `package` declarado lá (não o nome da pasta). Se nada resolve (import `.`,
      `_`, só métodos), a aresta vai para o representante da pasta, como antes."""
    pastas: dict[str, list[str]] = defaultdict(list)  # pasta -> arquivos .go que não são de teste
    sem_str: dict[str, str] = {}  # texto só de código (sem comentários, strings, import e cláusula package)
    pacote: dict[str, str] = {}
    decl: dict[str, set[str]] = {}
    for f in sorted(arquivos):
        if f.endswith("_test.go"):
            continue
        pastas[posixpath.dirname(f)].append(f)
        t = sem_str[f] = _go_so_codigo(ctx.texto(f, "go"))
        m = _GO_PACOTE.search(ctx.texto(f, "go"))
        pacote[f] = m.group(1) if m else ""
        decl[f] = _go_topo(t)

    # mesmo pacote
    donos: dict[tuple[str, str], dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    for f, nomes in decl.items():
        for nome in nomes:
            donos[(posixpath.dirname(f), pacote[f])][nome].append(f)
    for f, t in sem_str.items():
        por_nome = donos[(posixpath.dirname(f), pacote[f])]
        ligados = None
        alvos = set()
        for nome in _go_usos(_go_para_uso(t)):
            outros = [g for g in por_nome.get(nome, ()) if g != f]
            if len(nome) < 2 or not outros or nome in decl[f]:
                continue
            if not nome[0].isupper():
                ligados = _go_ligados(t) if ligados is None else ligados
                if nome in ligados:
                    continue
            alvos.update(outros)
        for g in sorted(alvos):
            ctx.aresta(f, g)

    # import de pacote interno
    modulos = []  # (module path, pasta do go.mod); vale o mais longo que for prefixo do import
    for man in ctx.manifestos:
        if posixpath.basename(man) != "go.mod":
            continue
        m = _GO_MODULE.search(re.sub(r"//[^\n]*", "", ctx.bruto(man)))
        if m:
            modulos.append((m.group(1), posixpath.dirname(man)))
    if not modulos:
        return  # sem go.mod não há module path para reconhecer o que é interno
    modulos.sort(key=lambda x: -len(x[0]))

    def representante(pasta: str) -> str:
        """Sem símbolo que resolva, a aresta vai para um arquivo da pasta, como `from pkg import x` vai para o
        __init__.py: o que tem o nome da pasta, senão o primeiro em ordem alfabética."""
        fs = sorted(pastas[pasta])
        nome = _junta(pasta, posixpath.basename(pasta) + ".go")
        return nome if nome in fs else fs[0]

    def pasta_de(caminho: str) -> str | None:
        for mpath, mdir in modulos:
            if caminho == mpath or caminho.startswith(mpath + "/"):
                resto = caminho[len(mpath) + 1:]
                pasta = _junta(mdir, resto) if resto else mdir
                if pastas.get(pasta):
                    return pasta
        return None

    for f in arquivos:
        texto = ctx.texto(f, "go")
        t = sem_str.get(f) or _go_so_codigo(texto)
        alvos = set()
        for m in _GO_IMPORT.finditer(texto):
            specs = _GO_SPEC.findall(m.group(1)) if m.group(1) is not None else [(m.group(2) or "", m.group(4))]
            for alias, caminho in specs:
                pasta = pasta_de(caminho)
                if pasta is None:
                    continue
                if alias in ("_", "."):
                    alvos.add(representante(pasta))
                    continue
                if alias:
                    quals = {alias: pastas[pasta]}
                else:
                    quals = defaultdict(list)
                    for g in pastas[pasta]:
                        if pacote[g]:
                            quals[pacote[g]].append(g)
                achou = set()
                if quals:
                    rx = re.compile(r"(?<![\w.])(%s)\s*\.\s*(%s)" % ("|".join(map(re.escape, quals)), _GO_ID))
                    for q, nome in rx.findall(t):
                        achou.update(g for g in quals[q] if nome in decl[g])
                alvos |= achou or {representante(pasta)}
        for g in sorted(alvos):
            ctx.aresta(f, g)


# ---- Rust

_RS_MOD = re.compile(r'(?:#\s*\[\s*path\s*=\s*"([^"]+)"\s*\]\s*)?(?:pub(?:\s*\([^)]*\))?\s+)?(?<!\w)mod\s+(\w+)\s*;')
_RS_USE = re.compile(r"(?<![\w:])use\s+([^;]+);")
_RS_RAIZ = re.compile(r"src/main\.rs|src/bin/[^/]+\.rs|src/bin/[^/]+/main\.rs|build\.rs|"
                      r"(?:tests|examples|benches)/[^/]+\.rs|(?:tests|examples|benches)/[^/]+/main\.rs")


def _expandir_use(texto: str, limite: int = 2000) -> list[list[str]]:
    """`a::{b, c::{d, self}, e as f, g::*}` -> [[a,b], [a,c,d], [a,c], [a,e], [a,g,*]]. O alias é descartado."""
    toks = re.findall(r"::|[{},*]|[A-Za-z_]\w*", texto)
    n, saida = len(toks), []

    def arvore(i: int, prefixo: list[str]) -> int:
        segs = list(prefixo)
        tocou = False
        while i < n and len(saida) < limite:
            t = toks[i]
            if t == "::":
                i += 1
            elif t == "{":
                i += 1
                while i < n and toks[i] != "}":
                    ant = i
                    i = arvore(i, segs)
                    if i < n and toks[i] == ",":
                        i += 1
                    elif i == ant:
                        i += 1
                return i + 1
            elif t == "as":
                i += 2
            elif t in (",", "}"):
                break
            else:
                segs.append(t)
                tocou = True
                i += 1
        if len(segs) > 1 and segs[-1] == "self":
            segs = segs[:-1]
        if tocou:
            saida.append(segs)
        return i

    arvore(0, [])
    return saida


_RS_CHAVE = re.compile(r"(?<!\w)(mod\s+\w+\s*\{)|\{|\}")


def _prof_modulos_em_linha(txt: str) -> tuple[list[int], list[int]]:
    """Posições onde muda a profundidade de módulos em linha (`mod tests { ... }`) e a profundidade a partir dali.
    Dentro de `mod tests { use super::*; }` o `super` é o módulo do próprio arquivo, não o pai dele."""
    pilha: list[bool] = []
    pos, prof = [0], [0]
    for m in _RS_CHAVE.finditer(txt):
        if m.group(0) == "}":
            if pilha:
                pilha.pop()
        else:
            pilha.append(bool(m.group(1)))
        pos.append(m.end())
        prof.append(sum(pilha))
    return pos, prof


def _arestas_rust(ctx: _Contexto, arquivos: list[str]) -> None:
    existentes = set(arquivos)
    pacotes: dict[str, dict] = {}  # pasta do Cargo.toml -> nome e raiz da lib, raízes declaradas à mão
    for man in ctx.manifestos:
        if posixpath.basename(man) != "Cargo.toml":
            continue
        try:
            cfg = tomllib.loads(ctx.bruto(man))
        except ValueError:
            continue
        pkg = cfg.get("package")
        if not isinstance(pkg, dict):
            continue  # raiz de workspace sem pacote
        pasta = posixpath.dirname(man)
        lib = cfg.get("lib") if isinstance(cfg.get("lib"), dict) else {}
        nome = str(pkg.get("name", "")).replace("-", "_")
        extras = {posixpath.normpath(_junta(pasta, str(a["path"])))
                  for k in ("bin", "test", "example", "bench") for a in (cfg.get(k) or [])
                  if isinstance(a, dict) and a.get("path")}
        pacotes[pasta] = {"lib_nome": str(lib.get("name") or nome).replace("-", "_"),
                          "lib": posixpath.normpath(_junta(pasta, str(lib.get("path") or "src/lib.rs"))),
                          "extras": extras}
    por_tamanho = sorted(pacotes, key=lambda p: -len(p))

    def pacote_de(f: str) -> str | None:
        return next((p for p in por_tamanho if p == "" or f.startswith(p + "/")), None)

    raizes: dict[str, bool] = {}  # arquivo-raiz do crate -> é lib?
    libs: dict[str, str] = {}     # nome do crate (com _) -> arquivo-raiz da lib
    for p, info in pacotes.items():
        if info["lib"] in existentes:
            raizes[info["lib"]] = True
            libs[info["lib_nome"]] = info["lib"]
    for f in arquivos:
        p = pacote_de(f)
        if p is None:  # fora de qualquer Cargo.toml: lib.rs e main.rs ainda são raízes de crate
            nome = posixpath.basename(f)
            if nome in ("lib.rs", "main.rs"):
                raizes[f] = nome == "lib.rs"
                if raizes[f]:
                    pasta = posixpath.dirname(f)
                    pasta = posixpath.dirname(pasta) if posixpath.basename(pasta) == "src" else pasta
                    libs.setdefault(re.sub(r"\W", "_", posixpath.basename(pasta) or "crate"), f)
            continue
        rel = f[len(p) + 1:] if p else f
        if _RS_RAIZ.fullmatch(rel) or f in pacotes[p]["extras"]:
            raizes.setdefault(f, False)
    ordem = sorted(raizes, key=lambda r: (not raizes[r], r))  # lib antes de bin na hora de desempatar
    dono_cache: dict[str, str | None] = {}

    def dono(f: str) -> str | None:
        """Raiz do crate de f: ela mesma, ou a raiz cuja pasta é o ancestral mais próximo."""
        if f not in dono_cache:
            melhor = f if f in raizes else None
            for r in ordem if melhor is None else ():
                d = posixpath.dirname(r)
                if (d == "" or f.startswith(d + "/")) and (melhor is None or len(d) > len(posixpath.dirname(melhor))):
                    melhor = r
            dono_cache[f] = melhor
        return dono_cache[f]

    def base(f: str, r: str | None) -> str:
        """Pasta dos filhos `mod x;` de f: a do próprio arquivo para a raiz e para mod.rs; nos outros, a pasta com o
        nome do arquivo (a.rs -> a/)."""
        if f == r or posixpath.basename(f) == "mod.rs":
            return posixpath.dirname(f)
        return f[:-3]

    def filho(f: str, r: str | None, nome: str) -> str | None:
        b = base(f, r)
        return next((c for c in (_junta(b, nome + ".rs"), _junta(b, nome + "/mod.rs")) if c in existentes), None)

    def descer(r: str | None, ini: str, segs: list[str]) -> str:
        """Segue os módulos de ini pelos segmentos enquanto existir arquivo; o resto é item (fn, struct) ou módulo
        em linha, e fica no último arquivo achado."""
        atual = ini
        for s in segs:
            f = filho(atual, r, s) if s != "*" else None
            if not f:
                break
            atual = f
        return atual

    def caminho_mod(f: str, r: str) -> list[str]:
        if f == r:
            return []
        d = posixpath.dirname(r)
        partes = (f[len(d) + 1:] if d else f).split("/")
        return partes[:-1] if partes[-1] == "mod.rs" else partes[:-1] + [partes[-1][:-3]]

    def resolver(f: str, r: str | None, segs: list[str], em_linha: int = 0) -> str | None:
        """`em_linha`: quantos `mod x { }` em linha envolvem o `use`; self/super contam a partir do mais interno."""
        if segs and segs[0] == "":
            segs = segs[1:]
        if not segs:
            return None
        p = segs[0]
        if p == "crate":
            return descer(r, r, segs[1:]) if r else None
        if p == "self":
            return f if em_linha else descer(r, f, segs[1:])
        if p == "super":
            if not r:
                return None
            k = 0
            while k < len(segs) and segs[k] == "super":
                k += 1
            if k <= em_linha:  # ainda dentro do arquivo: `mod tests { use super::*; }` enxerga o próprio arquivo
                return f if k < em_linha else descer(r, f, segs[k:])
            sobe = k - em_linha  # quantos módulos-arquivo acima do próprio arquivo
            mod = caminho_mod(f, r)
            if sobe > len(mod):
                return None
            return descer(r, descer(r, r, mod[:len(mod) - sobe]), segs[k:])
        ch = None if em_linha else filho(f, r, p)  # módulo filho em escopo (num mod em linha, o escopo é outro)
        if ch:
            return descer(r, ch, segs[1:])
        if p in libs:  # crate do workspace
            return descer(libs[p], libs[p], segs[1:])
        ch = filho(r, r, p) if r else None  # edição 2015: use relativo à raiz do crate
        return descer(r, ch, segs[1:]) if ch else None

    for f in arquivos:
        r = dono(f)
        txt = ctx.texto(f, "rust")
        alvos = []
        for m in _RS_MOD.finditer(txt):
            if m.group(1):
                c = posixpath.normpath(_junta(posixpath.dirname(f), m.group(1)))
                alvos.append(c if c in existentes else None)
            else:
                alvos.append(filho(f, r, m.group(2)))
        pos_prof, prof = _prof_modulos_em_linha(txt)
        for m in _RS_USE.finditer(txt):
            em_linha = prof[bisect.bisect_right(pos_prof, m.start()) - 1]
            alvos.extend({resolver(f, r, segs, em_linha) for segs in _expandir_use(m.group(1))})
        for alvo in alvos:
            ctx.aresta(f, alvo)


# ---- Java e Kotlin

_JVM_PACOTE = re.compile(r"(?m)^[ \t]*package[ \t]+([\w.`]+)")
_JVM_IMPORT = re.compile(r"(?m)^[ \t]*import[ \t]+(?:static[ \t]+)?([\w.`]+?)(\.\*)?(?:[ \t]+as[ \t]+(\w+))?[ \t]*;?[ \t\r]*$")
_JVM_LINHAS = re.compile(r"(?m)^[ \t]*(?:import|package)\b[^\n]*")
_JVM_RAIZ = re.compile(r"(?:^|/)src/(?:[\w-]+/)?(?:java|kotlin)/(.*)/[^/]+$|(?:^|/)(?:java|kotlin)/(.*)/[^/]+$|"
                       r"(?:^|/)src/(.*)/[^/]+$")
_JVM_DECL = re.compile(
    r"^[ \t]*(?:(?:@[\w.]+(?:\([^)]*\))?|public|private|protected|internal|static|final|abstract|open|sealed|non-sealed|"
    r"strictfp|data|enum|annotation|inline|value|const|lateinit|suspend|tailrec|operator|infix|expect|actual|external|fun)"
    r"[ \t]+)*(?:@interface|class|interface|record|object|typealias|fun|val|var)[ \t]+(?:<[^>\n]*>[ \t]*)?"
    r"(?:[\w.<>?,* ]+?\.)?(\w+)")


def _nomes_topo(txt: str) -> set[str]:
    """Nomes declarados fora de qualquer chave: classes, interfaces, objetos e, no Kotlin, funções e valores soltos."""
    nomes, prof = set(), 0
    for linha in txt.splitlines():
        if prof == 0:
            m = _JVM_DECL.match(linha)
            if m:
                nomes.add(m.group(1))
        prof = max(prof + linha.count("{") - linha.count("}"), 0)
    return nomes


def _pacote_do_caminho(f: str) -> str:
    """Sem `package` no arquivo: o pacote vem da árvore (src/main/java/a/b/C.java -> a.b)."""
    m = _JVM_RAIZ.search(f)
    pasta = next((g for g in m.groups() if g), "") if m else ""
    return pasta.replace("/", ".")


def _tipo_em(partes: list[str], decl: dict) -> list[str]:
    """`a.b.Classe.membro` -> arquivos que declaram (a.b, Classe): o prefixo mais longo que é pacote + nome."""
    for i in range(len(partes) - 1, 0, -1):
        alvo = decl.get((".".join(partes[:i]), partes[i]))
        if alvo:
            igual = {t for t in alvo if posixpath.splitext(posixpath.basename(t))[0] == partes[i]}
            return sorted(igual or alvo)
    return []


def _arestas_jvm(ctx: _Contexto, arquivos: list[str]) -> None:
    decl: dict[tuple[str, str], set[str]] = defaultdict(set)
    por_pacote: dict[str, dict[str, set[str]]] = defaultdict(dict)
    textos: dict[str, str] = {}
    for f in arquivos:
        txt = textos[f] = ctx.texto(f, "kotlin" if posixpath.splitext(f)[1] in EXT_KT else "java")
        m = _JVM_PACOTE.search(txt)
        pacote = m.group(1).replace("`", "") if m else _pacote_do_caminho(f)
        nomes = {posixpath.splitext(posixpath.basename(f))[0]} | _nomes_topo(txt)
        for n in nomes:
            decl[(pacote, n)].add(f)
        por_pacote[pacote][f] = nomes
    for f in arquivos:
        usados = None
        importes = list(_JVM_IMPORT.finditer(textos[f]))
        # Um import explícito (sem alias) de `a.b.Nome` — de dentro ou de fora do repositório — encobre qualquer `Nome`
        # trazido por curinga: o `import java.util.List` não puxa `util/List.java` só porque há `import util.*`.
        explicitos = {m.group(1).replace("`", "").rsplit(".", 1)[-1] for m in importes if not m.group(2) and not m.group(3)}
        for m in importes:
            nome = m.group(1).replace("`", "")
            if m.group(2) and nome in por_pacote:  # import pacote.*: só conta o arquivo cujo nome o código usa
                if usados is None:
                    usados = _idents(_JVM_LINHAS.sub("", textos[f])) - explicitos
                alvos = [g for g, ns in por_pacote[nome].items() if g != f and ns & usados]
            else:  # import a.b.Classe, import static a.b.Classe.membro, import a.b.Classe.*
                alvos = _tipo_em(nome.split("."), decl)
            for alvo in set(alvos):
                ctx.aresta(f, alvo)


# ---- C#

_CS_NS = re.compile(r"\bnamespace\s+([\w.]+)\s*([;{])|[{}]")
_CS_TIPO = re.compile(r"\b(?:class|struct|interface|enum|record(?:\s+(?:class|struct))?)\s+(\w+)")
_CS_USING = re.compile(r"(?m)^[ \t]*(?:global[ \t]+)?using[ \t]+(static[ \t]+)?(?:(\w+)[ \t]*=[ \t]*)?(?:global::)?([\w.]+)"
                       r"(?:<[^;>\n]*>)?[ \t]*;")
_CS_LINHAS = re.compile(r"(?m)^[ \t]*(?:(?:global[ \t]+)?using[ \t]+(?:static[ \t]+)?(?:\w+[ \t]*=[ \t]*)?[\w.:]+"
                        r"(?:<[^;>\n]*>)?[ \t]*;|namespace[ \t]+[\w.]+[ \t]*[;{]?)")
_CS_NAO_TIPO = {"where", "new", "class", "struct", "interface", "enum", "record"}


def _namespaces_cs(txt: str) -> set[str]:
    """Namespaces declarados, com o aninhamento (`namespace A { namespace B {` vira A.B) e a forma `namespace A.B;`."""
    achados, pilha, prof = set(), [], 0
    for m in _CS_NS.finditer(txt):
        if m.group(1):
            completo = f"{pilha[-1][0]}.{m.group(1)}" if pilha else m.group(1)
            achados.add(completo)
            if m.group(2) == ";":
                pilha.append((completo, -1))  # escopo de arquivo: nunca fecha
            else:
                pilha.append((completo, prof))
                prof += 1
        elif m.group() == "{":
            prof += 1
        else:
            prof -= 1
            while pilha and pilha[-1][1] == prof:
                pilha.pop()
    return achados


def _arestas_cs(ctx: _Contexto, arquivos: list[str]) -> None:
    ns_arquivos: dict[str, set[str]] = defaultdict(set)
    decl: dict[tuple[str, str], set[str]] = defaultdict(set)
    tipos_de: dict[str, set[str]] = {}
    textos: dict[str, str] = {}
    for f in arquivos:
        txt = textos[f] = ctx.texto(f, "csharp")
        tipos = tipos_de[f] = {t for t in _CS_TIPO.findall(txt) if t not in _CS_NAO_TIPO}
        for ns in _namespaces_cs(txt):
            ns_arquivos[ns].add(f)
            for t in tipos:
                decl[(ns, t)].add(f)
    for f in arquivos:
        usados = None
        for m in _CS_USING.finditer(textos[f]):
            estatico, alias, nome = m.group(1), m.group(2), m.group(3)
            alvos = _tipo_em(nome.split("."), decl) if (estatico or alias) else []
            if not alvos and not estatico:  # using Namespace;: só os arquivos cujo tipo o código usa
                if usados is None:
                    usados = _idents(_CS_LINHAS.sub("", textos[f]))
                alvos = [g for g in ns_arquivos.get(nome, ()) if g != f and tipos_de[g] & usados]
            for alvo in set(alvos):
                ctx.aresta(f, alvo)


# ---- C e C++

_C_INCLUDE = re.compile(r'(?m)^[ \t]*#[ \t]*(?:include|import)(?:_next)?[ \t]*"([^"\n]+)"')


def _arestas_c(ctx: _Contexto, arquivos: list[str]) -> None:
    por_nome: dict[str, list[str]] = defaultdict(list)
    for f in arquivos:
        por_nome[posixpath.basename(f)].append(f)

    def resolver(origem: str, inc: str) -> str | None:
        inc = inc.replace("\\", "/")
        pasta = posixpath.dirname(origem)
        while True:  # a pasta do arquivo primeiro, depois cada ancestral até a raiz (os -I mais comuns)
            c = posixpath.normpath(_junta(pasta, inc))  # "../x.h" sai da pasta: só vale se ainda cair dentro do repo
            if c in ctx.existentes:
                return c
            if not pasta:
                break
            pasta = posixpath.dirname(pasta)
        inc = posixpath.normpath(inc)
        if inc.startswith(".."):
            return None
        achados = [c for c in por_nome.get(posixpath.basename(inc), []) if c == inc or c.endswith("/" + inc)]
        return achados[0] if len(achados) == 1 else None  # include/ ou src/: só se for inequívoco

    for f in arquivos:
        for m in _C_INCLUDE.finditer(ctx.texto(f, "c")):
            ctx.aresta(f, resolver(f, m.group(1)))


def arestas_ast(repo: Path) -> dict[tuple[str, str], Counter]:
    fontes, manifestos = _varrer(repo)
    existentes = set(fontes)
    saida: dict[tuple[str, str], Counter] = defaultdict(Counter)
    por_ling: dict[str, list[str]] = defaultdict(list)
    for f in fontes:
        ling = LINGUAGEM_EXT[os.path.splitext(f)[1]]
        por_ling["c" if ling == "cpp" else ling].append(f)
    for f in por_ling["python"]:
        arestas_ast_python(repo, f, existentes, saida)
    for f in por_ling["javascript"]:
        arestas_ast_js(repo, f, existentes, saida)
    ctx = _Contexto(repo, existentes, manifestos, saida)
    _arestas_go(ctx, por_ling["go"])
    _arestas_rust(ctx, por_ling["rust"])
    _arestas_jvm(ctx, sorted(por_ling["java"] + por_ling["kotlin"]))
    _arestas_cs(ctx, por_ling["csharp"])
    _arestas_c(ctx, por_ling["c"])
    return saida


def escolher_fonte(repo: Path, fonte: str = "auto", db: Path | None = None) -> str:
    if fonte == "auto":
        return "codegraph" if caminho_db(repo, db).is_file() else "ast"
    if fonte == "codegraph" and not caminho_db(repo, db).is_file():
        raise SystemExit(f"codegraph_ponte: sem índice em {caminho_db(repo, db)} (use --fonte ast; "
                         "indexar com `codegraph init` é decisão do dono)")
    return fonte


def carregar_arestas(repo: Path, fonte: str = "auto", db: Path | None = None) -> tuple[dict[tuple[str, str], Counter], str]:
    usada = escolher_fonte(repo, fonte, db)
    return (arestas_codegraph(caminho_db(repo, db)) if usada == "codegraph" else arestas_ast(repo)), usada


# ------------------------------------------------------------------ pares componente -> componente

def confianca(tipos: Counter, fonte: str = "codegraph") -> str:
    """alta = 3+ chamadas; media = 2+ arestas; baixa = 1 aresta. No modo `ast` o `import` é um fato literal do
    código (não há referência não resolvida), então um import já vale media; sem isso, quase todo par de um
    projeto Python sairia baixa e o recall do qualidade.py contaria 1 par em 1, sem dizer nada."""
    total = sum(tipos.values())
    if fonte == "ast" and tipos.get("imports", 0) >= 1 and tipos.get("calls", 0) == 0:
        return "media"
    if total <= 1:
        return "baixa"
    if tipos.get("calls", 0) >= 3:
        return "alta"
    return "media"


def relacoes_do_modelo(ws: dict) -> dict[tuple[str, str], dict]:
    """(origem, destino) entre componentes -> relação declarada (descricao, tecnologia). Usa o ident do DSL."""
    ident_de = {c["id"]: c["ident"] for c in componentes(ws)}
    out = {}

    def visitar(el):
        for r in el.get("relationships", []):
            if r.get("linkedRelationshipId"):
                continue
            a, b = ident_de.get(r["sourceId"]), ident_de.get(r["destinationId"])
            if a and b and a != b:
                out[(a, b)] = {"descricao": r.get("description", ""), "tecnologia": r.get("technology", "")}

    m = ws.get("model", {})
    for p in m.get("people", []):
        visitar(p)
    for s in m.get("softwareSystems", []):
        visitar(s)
        for c in s.get("containers", []):
            visitar(c)
            for k in c.get("components", []):
                visitar(k)
    return out


def pares_componentes(arestas, mapa: dict[str, str]) -> dict[tuple[str, str], Counter]:
    pares: dict[tuple[str, str], Counter] = defaultdict(Counter)
    for (a, b), tipos in arestas.items():
        ca, cb = mapa.get(a), mapa.get(b)
        if ca and cb and ca != cb:
            pares[(ca, cb)].update(tipos)
    return pares


def analisar(arq: Path, repo: Path | None = None, fonte: str = "auto", db: Path | None = None) -> dict:
    """Tudo que a ponte sabe sobre um projeto: pares, mapa de arquivos e a leitura do modelo."""
    arq = arq.resolve()
    repo = (repo or raiz_repo(arq)).resolve()
    ws_arq = achar_workspace(arq)
    if not ws_arq:
        raise SystemExit("codegraph_ponte: sem workspace.json (rode o atualizar.ps1 antes)")
    ws = json.loads(ws_arq.read_text(encoding="utf-8-sig"))
    cfg_arq = arq / "lodemap.json"
    cfg = json.loads(cfg_arq.read_text(encoding="utf-8-sig")) if cfg_arq.is_file() else {}
    comps = componentes(ws)
    arestas, usada = carregar_arestas(repo, fonte, db)
    if usada == "codegraph":
        con = abrir_db(caminho_db(repo, db))
        try:
            arquivos = {r[0] for r in con.execute("SELECT path FROM files")}
        finally:
            con.close()
    else:
        arquivos = set(listar_fontes(repo))
    arquivos |= {a for par in arestas for a in par}
    # "ignorar" do lodemap.json: arquivo que casa um glob (ex. teste ao lado do código) não é módulo em lugar nenhum,
    # então também não gera aresta, não conta como "sem componente" e não entra no impacto.
    ignorar = _globs_ignorar(arq)
    if ignorar:
        arestas = {par: t for par, t in arestas.items() if not any(_ignorado(a, ignorar) for a in par)}
        arquivos = {a for a in arquivos if not _ignorado(a, ignorar)}
    mapa, ambiguos, sem = mapear_arquivos(arquivos, comps, cfg.get("raiz_codigo", ""))
    return {"repo": repo, "ws": ws, "cfg": cfg, "comps": comps, "arestas": arestas, "fonte": usada, "mapa": mapa,
            "ambiguos": ambiguos, "sem": sem, "pares": pares_componentes(arestas, mapa),
            "modelo": relacoes_do_modelo(ws)}


def relatorio_relacoes(info: dict, minimo: int = 1) -> dict:
    modelo = info["modelo"]
    pares = []
    for (a, b), tipos in sorted(info["pares"].items(), key=lambda kv: -sum(kv[1].values())):
        total = sum(tipos.values())
        if total < minimo:
            continue
        dec = modelo.get((a, b)) or modelo.get((b, a))
        pares.append({
            "de": a, "para": b, "tipo": "calls" if tipos.get("calls", 0) >= tipos.get("imports", 0) else "imports",
            "tipos": dict(tipos), "arestas": total, "confianca": confianca(tipos, info["fonte"]), "noModelo": dec is not None,
            "relacaoModelo": dec or None,
        })
    return {
        "fonte": info["fonte"], "geradoEm": datetime.now().astimezone().isoformat(timespec="seconds"),
        "aviso": ("Sugestões, não verdade: o modelador confirma e dá o verbo. Confiança: alta = calls com 3 arestas "
                  "ou mais; media = imports (ou 2 arestas; no modo ast, qualquer import); baixa = 1 aresta."),
        "arquivosAmbiguos": len(info["ambiguos"]), "arquivosSemComponente": len(info["sem"]),
        "pares": pares,
        "resumo": {"pares": len(pares), "noModelo": sum(p["noModelo"] for p in pares),
                   "faltandoNoModelo": sum(not p["noModelo"] for p in pares)},
    }


# ------------------------------------------------------------------ impacto

def impacto(info: dict, arquivo: str, profundidade: int = 1) -> dict:
    entrada: dict[str, Counter] = defaultdict(Counter)  # arquivo -> quem depende dele
    for (a, b), tipos in info["arestas"].items():
        entrada[b][a] += sum(tipos.values())
    mapa = info["mapa"]
    vistos, fronteira = {arquivo: 0}, [arquivo]
    for nivel in range(1, profundidade + 1):
        prox = []
        for f in fronteira:
            for dep in entrada.get(f, {}):
                if dep not in vistos:
                    vistos[dep] = nivel
                    prox.append(dep)
        fronteira = prox
    donos = sorted({mapa[arquivo]} if arquivo in mapa else set())
    afetados: dict[str, dict] = {}
    for f, nivel in vistos.items():
        ident = mapa.get(f)
        if not ident or f == arquivo:
            continue
        a = afetados.setdefault(ident, {"componente": ident, "distancia": nivel, "arquivos": []})
        a["distancia"] = min(a["distancia"], nivel)
        a["arquivos"].append(f)
    return {"arquivo": arquivo, "fonte": info["fonte"], "componenteDono": donos,
            "ambiguo": arquivo in info["ambiguos"], "profundidade": profundidade,
            "afetados": sorted(afetados.values(), key=lambda x: (x["distancia"], x["componente"]))}


# ------------------------------------------------------------------ inventário (rascunho)

def _primeira_frase(texto: str | None, limite: int = 160) -> str:
    if not texto:
        return ""
    linha = next((l.strip() for l in texto.strip().splitlines() if l.strip()), "")
    return linha[:limite]


def _globs_modulos(arq: Path | None) -> list[str]:
    if arq and (arq / "lodemap.json").is_file():
        return json.loads((arq / "lodemap.json").read_text(encoding="utf-8-sig")).get("modulos", [])
    return []


@functools.lru_cache(maxsize=256)
def _glob_regex(glob: str) -> re.Pattern:
    """Glob de arquivo com a semântica do Path.glob: `**/` casa zero ou mais pastas, `*` e `?` não atravessam `/`.

    O fnmatch não serve: nele `lib/**/*.js` exige ao menos uma pasta e deixava `lib/axios.js` sem módulo, o que
    apagava toda aresta de e para os arquivos da raiz do código.
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
            out.append(glob[i:j + 1])
            i = j + 1
        else:
            out.append(re.escape(glob[i]))
            i += 1
    return re.compile("".join(out), re.IGNORECASE if os.name == "nt" else 0)


def _ignorar_da_config(cfg: dict | None) -> list[str]:
    """Os globs de "ignorar" de um lodemap.json já lido (ausente ou vazio = nada é ignorado), sem barra final."""
    bruto = (cfg or {}).get("ignorar") or []
    if isinstance(bruto, str):
        bruto = [bruto]
    return [g.strip().rstrip("/") for g in bruto if isinstance(g, str) and g.strip().rstrip("/")]


def _globs_ignorar(arq: Path | None) -> list[str]:
    """Os globs de "ignorar" do <arq>/lodemap.json (a lista vazia se o arquivo não existe)."""
    if not (arq and (arq / "lodemap.json").is_file()):
        return []
    return _ignorar_da_config(json.loads((arq / "lodemap.json").read_text(encoding="utf-8-sig")))


def _ignorado(caminho: str, ignorar) -> bool:
    """O candidato a módulo (posix relativo ao repositório; pasta sem a barra final) casa algum glob de "ignorar"?
    Mesma semântica dos globs de "modulos" (`_glob_regex`)."""
    if not ignorar:
        return False
    c = caminho.rstrip("/")
    return any(_glob_regex(g.rstrip("/")).fullmatch(c) for g in ignorar)


def _modulo_de(arquivo: str, globs: list[str], ignorar: list[str] | None = None) -> str | None:
    """Módulo dono do arquivo, com a semântica do Path.glob do teste de cobertura: `*` não atravessa `/`.

    Candidato que casa algum glob de `ignorar` não é módulo; o glob seguinte ainda pode casar o arquivo.
    """
    partes = arquivo.split("/")
    for g in globs:
        if g.endswith("/"):
            base = g.rstrip("/")
            n = base.count("/") + 1
            if len(partes) > n and fnmatch.fnmatch("/".join(partes[:n]), base):
                if _ignorado("/".join(partes[:n]), ignorar):
                    continue
                return "/".join(partes[:n]) + "/"
        elif _glob_regex(g).fullmatch(arquivo):
            if _ignorado(arquivo, ignorar):
                continue
            return arquivo
    return None


def inventario_codegraph(db: Path, max_simbolos: int = 25) -> list[dict]:
    con = abrir_db(db)
    try:
        arquivos = con.execute("SELECT path, language, node_count FROM files WHERE generated = 0 ORDER BY path").fetchall()
        fim = dict(con.execute("SELECT file_path, MAX(end_line) FROM nodes GROUP BY file_path"))
        simbolos: dict[str, list] = defaultdict(list)
        doc_modulo: dict[str, str] = {}
        for path, kind, nome, linha, doc in con.execute(
                "SELECT file_path, kind, name, start_line, docstring FROM nodes "
                "WHERE kind IN ('file','class','function','interface','type_alias') ORDER BY file_path, start_line"):
            if kind == "file":
                if doc:
                    doc_modulo[path] = _primeira_frase(doc)
                continue
            simbolos[path].append({"nome": nome, "tipo": kind, "linha": linha, "doc": _primeira_frase(doc, 100)})
        out = []
        for path, lang, nos in arquivos:
            sims = simbolos.get(path, [])
            primeiro = next((s["doc"] for s in sims if s["doc"] and s["tipo"] in ("class", "function")), "")
            out.append({"caminho": path, "linguagem": lang, "linhas": fim.get(path, 0), "nos": nos,
                        "docstringModulo": doc_modulo.get(path, ""), "docstringPrimeiro": primeiro,
                        "simbolos": [{k: v for k, v in s.items() if k != "doc"} for s in sims[:max_simbolos]],
                        "totalSimbolos": len(sims)})
        return out
    finally:
        con.close()


_SIMBOLOS_RE = {
    "go": re.compile(r"^(?P<tipo>func|type)[ \t]+(?:\([^)]*\)[ \t]*)?(?P<nome>\w+)", re.M),
    "rust": re.compile(r"^[ \t]*(?:pub(?:\([^)]*\))?[ \t]+)?(?:async[ \t]+|const[ \t]+|unsafe[ \t]+)*"
                       r"(?P<tipo>fn|struct|enum|trait)[ \t]+(?P<nome>\w+)", re.M),
    "java": re.compile(r"^[ \t]*(?:(?:public|protected|private|abstract|final|static|sealed)[ \t]+)*"
                       r"(?P<tipo>class|interface|enum|record)[ \t]+(?P<nome>\w+)", re.M),
    "kotlin": re.compile(r"^[ \t]*(?:(?:public|private|internal|open|abstract|data|sealed|enum|suspend)[ \t]+)*"
                         r"(?P<tipo>class|interface|object|fun)[ \t]+(?:<[^>]*>[ \t]*)?(?P<nome>\w+)", re.M),
    "csharp": re.compile(r"^[ \t]*(?:(?:public|internal|private|protected|abstract|sealed|static|partial)[ \t]+)*"
                         r"(?P<tipo>class|interface|struct|enum|record)[ \t]+(?P<nome>\w+)", re.M),
    "c": re.compile(r"^(?P<tipo>struct|class)[ \t]+(?P<nome>\w+)[ \t]*(?:\{|:)", re.M),
    "cpp": re.compile(r"^(?P<tipo>struct|class)[ \t]+(?P<nome>\w+)[ \t]*(?:\{|:)", re.M),
}


def inventario_ast(repo: Path, max_simbolos: int = 25) -> list[dict]:
    out = []
    for f in listar_fontes(repo):
        texto = (repo / f).read_text(encoding="utf-8-sig", errors="replace")
        ling = LINGUAGEM_EXT[os.path.splitext(f)[1]]
        item = {"caminho": f, "linguagem": ling,
                "linhas": texto.count("\n") + 1, "docstringModulo": "", "docstringPrimeiro": "", "simbolos": []}
        if f.endswith(".py"):
            try:
                arv = ast.parse(texto)
            except (SyntaxError, ValueError):
                out.append(item)
                continue
            item["docstringModulo"] = _primeira_frase(ast.get_docstring(arv))
            for no in arv.body:
                if isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    item["simbolos"].append({"nome": no.name, "tipo": "class" if isinstance(no, ast.ClassDef) else "function",
                                             "linha": no.lineno})
                    if not item["docstringPrimeiro"]:
                        item["docstringPrimeiro"] = _primeira_frase(ast.get_docstring(no), 100)
        elif ling == "javascript":
            for m in re.finditer(r"^(?:export\s+)?(?:async\s+)?(function|class)\s+(\w+)", texto, re.M):
                item["simbolos"].append({"nome": m.group(2), "tipo": m.group(1), "linha": texto[:m.start()].count("\n") + 1})
        elif ling in _SIMBOLOS_RE:
            # texto sem comentários nem strings, com as mesmas linhas: o nome achado é declaração de verdade
            limpo = _limpar(texto, "c" if ling == "cpp" else ling)
            for m in _SIMBOLOS_RE[ling].finditer(limpo):
                tipo = "function" if m.group("tipo") in ("fn", "func", "fun") else "class"
                item["simbolos"].append({"nome": m.group("nome"), "tipo": tipo, "linha": limpo[:m.start()].count("\n") + 1})
            for linha in texto.splitlines()[:30]:  # primeiro comentário do topo é o propósito do módulo
                t = linha.strip()
                if t.startswith(("//", "/*", "*")) and len(t.lstrip("/*! ").strip()) > 15:
                    item["docstringModulo"] = _primeira_frase(t.lstrip("/*! ").strip())
                    break
                if t and not t.startswith(("//", "/*", "*", "#", "package", "using", "import")):
                    break
        item["totalSimbolos"] = len(item["simbolos"])
        item["simbolos"] = item["simbolos"][:max_simbolos]
        out.append(item)
    return out


def rascunho_inventario(repo: Path, arq: Path | None, fonte: str = "auto", db: Path | None = None) -> dict:
    usada = escolher_fonte(repo, fonte, db)
    itens = inventario_codegraph(caminho_db(repo, db)) if usada == "codegraph" else inventario_ast(repo)
    globs = _globs_modulos(arq)
    ignorar = _globs_ignorar(arq)
    if globs:
        for it in itens:
            it["modulo"] = _modulo_de(it["caminho"], globs, ignorar)
        itens = [i for i in itens if i["modulo"]]
    return {"fonte": usada, "geradoEm": datetime.now().astimezone().isoformat(timespec="seconds"),
            "observacao": "Rascunho sem leitura de arquivos; o lodemap-inventario completa pontos de entrada, rotas e serviços.",
            "arquivos": itens}


# ------------------------------------------------------------------ CLI

def main(argv=None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    modo = ap.add_mutually_exclusive_group(required=True)
    modo.add_argument("--inventario", action="store_true")
    modo.add_argument("--relacoes", action="store_true")
    modo.add_argument("--impacto", metavar="ARQUIVO")
    ap.add_argument("--arq", help="pasta structurizr do projeto")
    ap.add_argument("--repo", help="raiz do repositório (padrão: raiz do git de --arq ou do diretório atual)")
    ap.add_argument("--db", help="índice do CodeGraph em outro lugar (padrão: <repo>/.codegraph/codegraph.db)")
    ap.add_argument("--fonte", choices=["auto", "codegraph", "ast"], default="auto")
    ap.add_argument("--json", help="inventário: onde gravar (padrão: stdout)")
    ap.add_argument("--saida", help="relações: onde gravar (padrão: <arq>/relacoes-codigo.json)")
    ap.add_argument("--minimo", type=int, default=1, help="relações: mínimo de arestas por par")
    ap.add_argument("--profundidade", type=int, default=1)
    a = ap.parse_args(argv)
    arq = Path(a.arq).resolve() if a.arq else None
    repo = Path(a.repo).resolve() if a.repo else raiz_repo(arq or Path.cwd())

    if a.inventario:
        dados = rascunho_inventario(repo, arq, a.fonte, Path(a.db) if a.db else None)
        texto = json.dumps(dados, ensure_ascii=False, indent=1)
        if a.json:
            Path(a.json).write_text(texto + "\n", encoding="utf-8")
            print(f"inventário ({dados['fonte']}): {len(dados['arquivos'])} arquivos -> {a.json}")
        else:
            print(texto)
        return 0
    if not arq:
        ap.error("--arq é obrigatório em --relacoes e --impacto")
    info = analisar(arq, repo, a.fonte, Path(a.db) if a.db else None)
    if a.relacoes:
        rel = relatorio_relacoes(info, a.minimo)
        destino = Path(a.saida) if a.saida else arq / "relacoes-codigo.json"
        destino.write_text(json.dumps(rel, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(f"relações ({rel['fonte']}): {rel['resumo']} -> {destino}")
        return 0
    rel_path = a.impacto.replace("\\", "/")
    print(json.dumps(impacto(info, rel_path, a.profundidade), ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
