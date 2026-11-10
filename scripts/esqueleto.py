"""Esqueleto do modelo C4 por script: o modelador decide em JSON curto, o script escreve o DSL.

Três subcomandos, só biblioteca padrão e 0 tokens (`pendencias` faz o mesmo cálculo do `rascunho`, mas só imprime
o que está pendente em JSON e não grava nada; é o que o lodemap_decidir.py lê):

- `rascunho`: lê os globs de `lodemap.json`, o inventário (CodeGraph ou ast) e as arestas do código, e grava
  `<arq>/.lodemap/decisoes-modelo.json` com um componente sugerido por módulo (id, caminho, linhas, dica tirada da
  docstring, símbolos) e uma relação sugerida por par de módulos com arestas no código. Os campos de decisão vêm
  vazios. Rodar de novo preserva o que já foi decidido: módulos novos entram vazios e módulos que sumiram vão para
  `removidos` (é assim que a atualização do modelo fica restrita ao que mudou).
- `renderizar`: confere que toda decisão foi tomada e escreve `model/containers.dsl`,
  `model/componentes-<container>.dsl` e `model/relacoes-componentes.dsl` (incluído por `model/relacoes.dsl`).
  Também escreve `views/visoes-geradas.dsl` (contexto, containers, componentes por container e por área e por
  status). Pessoas, sistemas externos, relações com eles e os fluxos (visões dinâmicas) ficam com o modelador.

O modelador nunca escreve o boilerplate do DSL (properties, tags, grupos): preenche nome, descrição, container,
área, status e o verbo de cada relação que confirmou no código.
"""
from __future__ import annotations

import argparse
import ast
import bisect
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import codegraph_ponte as cp  # noqa: E402
from lodemap.idioma import opcao, t, usar_mapa  # noqa: E402

STATUS = ("Pronto", "EmAndamento", "Aguardando", "Planejado", "ForaDoFoco")
TAGS_EXTRAS = {"Dados", "Gate", "Privacidade", "Barramento", "WebBrowser", "Janela", "Modelo", "Externo", "Nuvem"}
CABECALHO = "// Gerado por scripts/esqueleto.py a partir de .lodemap/decisoes-modelo.json. Edite o JSON, não este arquivo.\n"
LINGUAGEM = {"python": "Python", "javascript": "JavaScript", "typescript": "TypeScript", "tsx": "TypeScript",
             "jsx": "JavaScript", "rust": "Rust", "go": "Go", "java": "Java", "csharp": "C#",
             "kotlin": "Kotlin", "c": "C", "cpp": "C++"}
CAMPOS_COMPONENTE = ("nome", "descricao", "container", "area", "status")
# A tag não tem espaço; a propriedade "status" leva o rótulo que o explorador e os documentos mostram.
ROTULO = {"EmAndamento": "Em andamento", "ForaDoFoco": "Fora do foco"}
# Com "idioma": "en" no lodemap.json, a propriedade sai em inglês (o arq_comum aceita os dois idiomas).
ROTULO_EN = {"Pronto": "Done", "EmAndamento": "In progress", "Aguardando": "Waiting", "Planejado": "Planned",
             "ForaDoFoco": "Out of focus"}


def _idioma(arq: Path) -> str:
    try:
        cfg = json.loads((arq / "lodemap.json").read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return "pt"
    return "en" if cfg.get("idioma") == "en" else "pt"
EXTENSAO = {".py": "python", ".js": "javascript", ".ts": "typescript", ".sh": "Bash", ".ps1": "PowerShell",
            ".html": "HTML", ".rs": "rust", ".go": "go"}
IGNORAR = {"__pycache__", "node_modules", ".git", ".venv", "dist", "build"}


def modulos_dos_globs(repo: Path, globs: list[str], ignorar: list[str] | None = None) -> list[str]:
    """Os mesmos alvos do teste de cobertura: Path.glob, glob com '/' no fim casa pasta, o resto casa arquivo.

    `ignorar` (globs de "ignorar" do lodemap.json): candidato que casa algum não é módulo.
    """
    alvos = set()
    for padrao in globs:
        pasta = padrao.endswith("/")
        for p in repo.glob(padrao.rstrip("/")):
            rel = p.relative_to(repo)
            if any(x in IGNORAR or x.startswith(".") for x in rel.parts) or pasta != p.is_dir():
                continue
            if cp._ignorado(rel.as_posix(), ignorar):
                continue
            alvos.add(rel.as_posix() + ("/" if pasta else ""))
    return sorted(alvos)


def _id_sugerido(modulo: str, usados: set[str]) -> str:
    partes = [p for p in re.split(r"[/\\._\-]+", modulo.rstrip("/")) if p and p not in {"src", "py", "js", "ts", "tsx"}]
    partes = partes[-2:] or ["modulo"]
    base = partes[0].lower() + "".join(p[:1].upper() + p[1:] for p in partes[1:])
    base = re.sub(r"\W", "", base) or "modulo"
    if base[0].isdigit():
        base = "m" + base
    ident, n = base, 2
    while ident in usados:
        ident, n = f"{base}{n}", n + 1
    usados.add(ident)
    return ident


def _escapar(texto: str) -> str:
    # Aspas duplas viram simples: o DSL e o teste de cobertura leem strings como "[^"]*".
    return str(texto).replace('"', "'").replace("\n", " ").strip()


# Impressão digital semântica: só a superfície pública do módulo (o que uma descrição pode citar). Corpo de função,
# comentário interno e formatação não contam; medido em releases reais do rich (v13.0.0 a v13.9.4): 78 arquivos
# mudados, 29 com a digital mudada (63% de revisões a menos). Ver references/digital-semantica.md.
_DECL = re.compile(r"(?:export\s+|pub(?:\([^)]*\))?\s+|public\s+|protected\s+|internal\s+|async\s+|static\s+|abstract\s+|"
                   r"final\s+|default\s+)*(?:import|from|use|require|package|module|using|#include|function|class|"
                   r"interface|struct|enum|trait|impl|type|fn|func|def|const|let|var|val|object|record|namespace)\b")
_COMENTARIO = re.compile(r"\s*(?:#|//|/\*|\*|<#|--)")


def _digital_py_v1(texto: str) -> str | None:
    """Algoritmo da digital v1, congelado: os mapas feitos antes da v2 guardam o hash que ele produz."""
    try:
        arv = ast.parse(texto)
    except SyntaxError:
        return None
    partes = [ast.get_docstring(arv) or ""]
    for n in arv.body:
        if isinstance(n, (ast.Import, ast.ImportFrom)):
            partes.append(ast.dump(n, include_attributes=False))
        elif isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and not n.name.startswith("_"):
            doc = (ast.get_docstring(n) or "").strip().splitlines()
            if isinstance(n, ast.ClassDef):
                assin = "[" + ", ".join(ast.unparse(b) for b in n.bases) + "] " + " ".join(
                    f"{m.name}({ast.unparse(m.args)})" for m in n.body
                    if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef)) and not m.name.startswith("_"))
            else:
                assin = f"({ast.unparse(n.args)})"
            partes.append(f"{type(n).__name__} {n.name}{assin} {doc[0] if doc else ''}")
        elif isinstance(n, (ast.Assign, ast.AnnAssign)):
            alvos = n.targets if isinstance(n, ast.Assign) else [n.target]
            nomes = [a.id for a in alvos if isinstance(a, ast.Name) and (a.id.isupper() or a.id == "__all__")]
            if nomes:
                partes.append("const " + ",".join(nomes) + (" " + ast.unparse(n.value) if "__all__" in nomes else ""))
    return "\n".join(partes)


def _digital_texto_v1(texto: str) -> str:
    """Algoritmo da digital v1, congelado. Outras linguagens: o primeiro bloco de comentário (a doc do arquivo) e as
    linhas de declaração ou import no topo do arquivo (sem recuo), mais métodos públicos com recuo (Java, C#, Rust
    impl). Espaços normalizados."""
    linhas = texto.splitlines()
    partes, cabeca = [], True
    for linha in linhas:
        nua = linha.strip()
        if not nua:
            continue
        if cabeca and _COMENTARIO.match(linha):
            partes.append(" ".join(nua.split()))
            continue
        cabeca = False
        recuo = len(linha) - len(linha.lstrip())
        if (recuo == 0 and _DECL.match(nua)) or (recuo and re.match(r"(?:public|pub\s+fn|protected)\b", nua)):
            partes.append(" ".join(nua.rstrip("{").split()))
    return "\n".join(partes)


# ---- Digital v2 = v1 + regras de ADIÇÃO estruturais. Só nomes e assinaturas, nunca valor, corpo, decorador nem
# anotação de retorno; nada que a v1 mostrava sai. Python por ast; JS/TS por texto (sem parser).

def _folhas(alvos) -> list:
    """Os alvos de uma atribuição, abrindo tupla, lista e `*resto`."""
    saida = []
    for a in alvos:
        if isinstance(a, (ast.Tuple, ast.List)):
            saida += _folhas(a.elts)
        elif isinstance(a, ast.Starred):
            saida += _folhas([a.value])
        else:
            saida.append(a)
    return saida


def _alvos_de(n) -> list:
    if isinstance(n, ast.Assign):
        return _folhas(n.targets)
    if isinstance(n, ast.AnnAssign):
        return _folhas([n.target])
    return []


def _atributos_do_self(no, eu: str, saida: set[str]) -> None:
    """`self.x = ...` e `self.x: T = ...` no corpo do `__init__`, sem entrar em def, class ou lambda aninhados."""
    for f in ast.iter_child_nodes(no):
        if isinstance(f, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
            continue
        for a in _alvos_de(f):
            if isinstance(a, ast.Attribute) and isinstance(a.value, ast.Name) and a.value.id == eu \
                    and not a.attr.startswith("_"):
                saida.add(a.attr)
        _atributos_do_self(f, eu, saida)


def _metodos_publicos(c: ast.ClassDef) -> list[str]:
    return sorted(m.name for m in c.body if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef))
                  and not m.name.startswith("_"))


def _extras_classe_py(c: ast.ClassDef, prefixo: str, aninhada: bool = False) -> list[str]:
    saida = []
    if not aninhada:
        attrs = sorted({a.id for m in c.body for a in _alvos_de(m)
                        if isinstance(a, ast.Name) and not a.id.startswith("_")})
        if attrs:
            saida.append(f"attrs {prefixo} {','.join(attrs)}")
        for m in c.body:
            if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef)) and m.name == "__init__":
                saida.append(f"init {prefixo}({ast.unparse(m.args)})")
                eu = (m.args.posonlyargs + m.args.args or [None])[0]
                inst: set[str] = set()
                if eu is not None:
                    _atributos_do_self(m, eu.arg, inst)
                if inst:
                    saida.append(f"iattrs {prefixo} {','.join(sorted(inst))}")
                break
    for m in c.body:
        if isinstance(m, ast.ClassDef) and not m.name.startswith("_"):
            saida.append(f"nested {prefixo}.{m.name} {','.join(_metodos_publicos(m))}")
            saida += [s for s in _extras_classe_py(m, f"{prefixo}.{m.name}", True) if s.startswith("nested ")]
    return saida


def _digital_py(texto: str) -> str | None:
    base = _digital_py_v1(texto)
    if base is None:
        return None
    arv = ast.parse(texto)
    extras, nomes = [], set()
    for n in arv.body:
        if isinstance(n, ast.ClassDef) and not n.name.startswith("_"):
            extras += _extras_classe_py(n, n.name)
        else:
            nomes.update(a.id for a in _alvos_de(n) if isinstance(a, ast.Name) and not a.id.startswith("_")
                         and not a.id.isupper() and a.id != "__all__")
    if nomes:
        extras.insert(0, "var " + ",".join(sorted(nomes)))
    return base + "".join("\n" + e for e in extras)


_JS_EXT = {".js", ".mjs", ".cjs", ".jsx", ".ts", ".tsx"}
_PONTUACAO = re.compile(r" ?([,;:(){}\[\]=<>!?&|+*/%.\-]) ?")
_ABRE = {")": "(", "]": "[", "}": "{"}
_IDENT = r"[A-Za-z_$][\w$]*"
_MODS_MEMBRO = r"(?:(?:public|protected|private|static|async|readonly|override|abstract|declare)\s+)*"
_PALAVRAS = {"function", "class", "async", "new", "await", "null", "true", "false", "undefined", "this", "typeof"}


def _norm_decl(s: str) -> str:
    """Espaço dentro de uma declaração não muda a digital: espaços em volta de pontuação somem, o resto vira um só."""
    return _PONTUACAO.sub(r"\1", " ".join(s.split()))


# comentário, string, template e uma barra solta (que pode abrir uma regex); a regex entra em _REGEX_JS
_JS_TOKEN2 = re.compile(r"""//[^\n]*|/\*[\s\S]*?(?:\*/|\Z)|'(?:\\[\s\S]|[^'\\\n])*'?|"(?:\\[\s\S]|[^"\\\n])*"?|`(?:\\[\s\S]|[^`\\])*`?|/""")
_REGEX_JS = re.compile(r"/(?![/*])(?:\\.|\[(?:\\.|[^\]\\\n])*\]|[^/\\\[\n])+/[a-z]*")
# antes de uma regex vem um destes sinais ou uma destas palavras; depois de um nome, número ou `)` a barra divide
_ANTES_DE_REGEX = re.compile(r"(?:^|[(,=:\[!&|?{};+\-*%<>~^]|\b(?:return|typeof|case|in|of|delete|void|throw|new|else|do|yield|await))\s*$")


def _mascara_js(texto: str) -> tuple[str, str]:
    """Duas cópias do texto com os mesmos deslocamentos: `limpo` (comentários viram espaço, strings intactas) e `masc`
    (também com cada string e cada regex trocadas por `_`; é onde se casam chaves, parênteses e palavras-chave). Quebras
    ficam. A regex entra porque um `'` ou uma crase dentro dela abriria uma "string" que engole o resto do arquivo."""
    limpo, masc, pos, busca, valor = [], [], 0, 0, False   # valor: o último token foi string ou regex (barra = divisão)
    while True:
        m = _JS_TOKEN2.search(texto, busca)
        if m is None:
            break
        tok = m.group(0)
        if tok == "/":
            ctx = texto[max(pos, m.start() - 24):m.start()]
            r = _REGEX_JS.match(texto, m.start())
            if r is None or not _ANTES_DE_REGEX.search(ctx) or (valor and not ctx.strip()):
                busca = m.end()
                continue
            m, tok = r, r.group(0)
        antes = texto[pos:m.start()]
        limpo.append(antes)
        masc.append(antes)
        valor = not tok.startswith(("//", "/*"))
        if not valor:
            vazio = re.sub(r"[^\n]", " ", tok)
            limpo.append(vazio)
            masc.append(vazio)
        else:
            limpo.append(tok)
            masc.append(re.sub(r"[^\n]", "_", tok))
        pos = busca = m.end()
    limpo.append(texto[pos:])
    masc.append(texto[pos:])
    return "".join(limpo), "".join(masc)


class _Colchetes:
    """Pares de (), [] e {} do texto mascarado e a profundidade em cada posição. Desbalanceado: o colchete sem par é
    ignorado (nunca levanta)."""

    def __init__(self, masc: str):
        self.par: dict[int, int] = {}
        self._pos: list[int] = []
        self._prof: list[int] = []
        pilha: list[tuple[str, int]] = []
        for m in re.finditer(r"[()\[\]{}]", masc):
            ch, i = m.group(0), m.start()
            if ch in "([{":
                pilha.append((ch, i))
            elif pilha and pilha[-1][0] == _ABRE[ch]:
                self.par[pilha.pop()[1]] = i
            else:
                continue
            self._pos.append(i)
            self._prof.append(len(pilha))

    def prof(self, i: int) -> int:
        """Quantos colchetes abertos há antes da posição `i` (para um colchete de abertura, a profundidade de fora)."""
        k = bisect.bisect_left(self._pos, i)
        return self._prof[k - 1] if k else 0


def _valor_nome(limpo: str, a: int, b: int) -> str:
    return " ".join(limpo[a:b].split()).strip("'\"`")


def _chaves_do_objeto(limpo: str, masc: str, abre: int, fecha: int) -> list[str]:
    """Nomes das chaves de primeiro nível do objeto literal em masc[abre:fecha+1] (abreviada, método, spread e
    computada incluídos; nunca o valor)."""
    nomes, prof, ini = [], 0, abre + 1
    cortes = []
    for m in re.finditer(r"[,()\[\]{}]", masc[abre + 1:fecha]):
        ch = m.group(0)
        if ch in "([{":
            prof += 1
        elif ch in ")]}":
            prof -= 1
        elif ch == "," and prof == 0:
            cortes.append(abre + 1 + m.start())
    for fim in [*cortes, fecha]:
        seg = masc[ini:fim]
        m = re.match(rf"\s*(\.\.\.\s*)?((?:async|get|set)\s+)?(\*\s*)?({_IDENT}|\d+|\[[^\]]*\])", seg)
        if m:
            nome = _valor_nome(limpo, ini + m.start(4), ini + m.end(4))
            nomes.append(("..." if m.group(1) else "") + " ".join(x for x in (
                (m.group(2) or "").strip(), "*" if m.group(3) else "", nome) if x))
        ini = fim + 1
    return sorted(set(nomes))


def _lista_de_exports(limpo: str, ini: int, fim: int) -> list[str]:
    return sorted({" ".join(x.split()) for x in limpo[ini:fim].split(",") if x.strip()})


def _extras_js(texto: str) -> list[str]:
    limpo, masc = _mascara_js(texto)
    col = _Colchetes(masc)
    saida: list[str] = []
    flags = re.M

    # nomes exportados por `export default X`, `export { X, Y as Z }` e `module.exports = X`
    exportados: set[str] = set()
    for m in re.finditer(rf"^[ \t]*export\s+default\s+({_IDENT})\s*(?:;|$)", masc, flags):
        if m.group(1) not in _PALAVRAS:
            exportados.add(m.group(1))
    for m in re.finditer(rf"^[ \t]*module\.exports\s*=\s*({_IDENT})\s*(?:;|$)", masc, flags):
        if m.group(1) not in _PALAVRAS:
            exportados.add(m.group(1))
    for m in re.finditer(r"^[ \t]*export\s*(?:type\s+)?\{([^}]*)\}(?!\s*from\b)", masc, flags):
        for item in limpo[m.start(1):m.end(1)].split(","):
            partes = item.split()
            if partes and partes[0] == "type" and len(partes) > 1:
                partes = partes[1:]
            if partes:
                exportados.add(partes[0])

    def topo(m) -> bool:
        return col.prof(m.start()) == 0

    # listas de export e `export * from`
    for m in re.finditer(r"^[ \t]*export\s*(?:type\s+)?\{([^}]*)\}\s*(?:from\s*(_+))?", masc, flags):
        if topo(m):
            de = " from " + _valor_nome(limpo, m.start(2), m.end(2)) if m.group(2) else ""
            saida.append("+export {" + "|".join(_lista_de_exports(limpo, m.start(1), m.end(1))) + "}" + de)
    for m in re.finditer(rf"^[ \t]*export\s*\*\s*(?:as\s+({_IDENT})\s*)?from\s*(_+)", masc, flags):
        if topo(m):
            saida.append(f"+export * {m.group(1) or ''} from " + _valor_nome(limpo, m.start(2), m.end(2)))

    # objetos literais exportados: só as chaves de primeiro nível
    def objeto(nome: str, abre: int) -> None:
        fecha = col.par.get(abre)
        if fecha is not None:
            saida.append(f"+obj {nome} " + ";".join(_chaves_do_objeto(limpo, masc, abre, fecha)))

    for m in re.finditer(r"^[ \t]*export\s+default\s*(\{)", masc, flags):
        if topo(m):
            objeto("default", m.start(1))
    for m in re.finditer(r"^[ \t]*module\.exports\s*=\s*(\{)", masc, flags):
        if topo(m):
            objeto("module.exports", m.start(1))
    atrib = rf"^[ \t]*(export\s+)?(?:const|let|var)\s+({_IDENT})\s*(?::[^=\n]*?)?=\s*"
    for m in re.finditer(atrib + r"(\{)", masc, flags):
        if topo(m) and (m.group(1) or m.group(2) in exportados):
            objeto(m.group(2), m.start(3))

    # funções exportadas: a lista de parâmetros inteira, mesmo quebrada em várias linhas
    def funcao(nome: str, abre: int) -> None:
        fecha = col.par.get(abre)
        if fecha is not None:
            saida.append(f"+fn {nome}" + _norm_decl(limpo[abre:fecha + 1]))

    for m in re.finditer(rf"^[ \t]*(export\s+(?:default\s+)?)?(?:declare\s+)?(?:async\s+)?function\s*\*?\s*({_IDENT})?"
                         r"\s*(?:<[^>(]*>)?\s*(\()", masc, flags):
        if topo(m) and (m.group(1) or (m.group(2) in exportados)):
            funcao(m.group(2) or "default", m.start(3))
    for m in re.finditer(atrib + r"(?:async\s+)?(\()", masc, flags):
        fecha = col.par.get(m.start(3))
        if topo(m) and (m.group(1) or m.group(2) in exportados) and fecha is not None \
                and re.match(r"\s*(?::[^=;]*)?=>", masc[fecha + 1:fecha + 400]):
            funcao(m.group(2), m.start(3))
    for m in re.finditer(atrib + rf"(?:async\s+)?({_IDENT})\s*=>", masc, flags):
        if topo(m) and (m.group(1) or m.group(2) in exportados):
            saida.append(f"+fn {m.group(2)}(" + _valor_nome(limpo, m.start(3), m.end(3)) + ")")

    # membros de classe exportada: construtor e métodos com assinatura inteira, campos só pelo nome
    for m in re.finditer(rf"^[ \t]*(export\s+(?:default\s+)?)?(?:declare\s+)?(?:abstract\s+)?class\b([^{{]*)\{{", masc, flags):
        if not topo(m):
            continue
        cab = re.match(rf"\s*({_IDENT})", m.group(2))
        nome = cab.group(1) if cab and cab.group(1) not in ("extends", "implements") else "default"
        fecha = col.par.get(m.end() - 1)
        if fecha is None or not (m.group(1) or nome in exportados):
            continue
        saida += _membros_da_classe(limpo, masc, col, nome, m.end(), fecha)
    return saida


def _membros_da_classe(limpo: str, masc: str, col: _Colchetes, classe: str, ini: int, fim: int) -> list[str]:
    corpo = masc[ini:fim]
    fundo = col.prof(ini - 1) + 1
    saida = []

    def comeco_de_membro(a: int) -> bool:
        antes = corpo[:a].rstrip()
        return col.prof(ini + a) == fundo and (not antes or antes[-1] in "{};")

    metodo = re.compile(rf"^[ \t]*({_MODS_MEMBRO})(get\s+|set\s+)?(\*\s*)?(#?{_IDENT}|\[[^\]]*\])\s*(?:<[^>(]*>)?\s*(\()", re.M)
    for m in metodo.finditer(corpo):
        a = m.start(1)
        mods, nome = m.group(1), _valor_nome(limpo, ini + m.start(4), ini + m.end(4))
        fecha = col.par.get(ini + m.start(5))
        if fecha is None or not comeco_de_membro(a) or nome.startswith(("#", "_")) or "private" in mods.split():
            continue
        quals = [w for w in mods.split() if w in ("static", "async")]
        quals += [m.group(2).strip()] if m.group(2) else []
        quals += ["*"] if m.group(3) else []
        saida.append(f"+member {classe} {' '.join(quals + [nome])}" + _norm_decl(limpo[ini + m.start(5):fecha + 1]))
    campo = re.compile(rf"^[ \t]*({_MODS_MEMBRO})(#?{_IDENT})\s*[?!]?\s*(?::[^=;\n]*)?(?:=|;|$)", re.M)
    for m in campo.finditer(corpo):
        nome = m.group(2)
        if nome.startswith(("#", "_")) or "private" in m.group(1).split() or not comeco_de_membro(m.start(1)):
            continue
        if nome in ("constructor",):
            continue
        saida.append(f"+field {classe} {nome}")
    return saida


_GO_DECL = re.compile(r"(?:func\s+(?:\([^)]*\)\s*)?([A-Za-z_]\w*)|type\s+([A-Za-z_]\w*))")


def _extras_go(texto: str) -> list[str]:
    """Go: a primeira linha do comentário de doc colado acima de func, método ou type exportado (a frase que o godoc
    mostra, o mesmo papel da primeira linha da docstring em Python) e a marca `Deprecated:`. A v1 só lia o comentário
    do topo do arquivo, e em Go a documentação mora em cima de cada função: na v5.5.0 do go-chi/chi o `Sunset` deixou
    de escrever o cabeçalho Deprecation, só o comentário dizia, e a digital não mudava."""
    saida, bloco = [], []
    for linha in texto.splitlines():
        if linha.startswith("//"):
            if not linha.startswith("//go:"):
                bloco.append(" ".join(linha[2:].split()))
            continue
        m = _GO_DECL.match(linha)
        if m and bloco:
            nome = m.group(1) or m.group(2)
            if nome[:1].isupper():
                primeira = next((b for b in bloco if b), "")
                if primeira:
                    saida.append(f"+doc {nome} {primeira}")
                if any(b.startswith("Deprecated:") for b in bloco):
                    saida.append(f"+deprecated {nome}")
        bloco = []
    return saida


def _digital_texto(texto: str, sufixo: str = "") -> str:
    """v2. Igual à v1; em JS/TS as linhas de declaração perdem a diferença de espaço e entram as regras de adição
    (chaves de objeto exportado, listas de export, parâmetros inteiros, membros de classe); em Go entra a primeira
    linha do comentário de doc de cada símbolo exportado."""
    sup = _digital_texto_v1(texto)
    if sufixo == ".go":
        return "\n".join(([sup] if sup else []) + sorted(set(_extras_go(texto))))
    if sufixo not in _JS_EXT:
        return sup
    linhas = [ln if _COMENTARIO.match(ln) else _norm_decl(ln) for ln in sup.split("\n")] if sup else []
    return "\n".join(linhas + sorted(set(_extras_js(texto))))


def _calcular_digital(repo: Path, modulo: str, f_py, f_texto) -> str | None:
    alvo = repo / modulo.rstrip("/")
    if alvo.is_file():
        arquivos = [alvo]
    elif alvo.is_dir():
        arquivos = sorted(p for p in alvo.rglob("*") if p.is_file() and not IGNORAR & set(p.relative_to(alvo).parts))
    else:
        return None
    h = hashlib.sha256()
    for p in arquivos:
        texto = p.read_text(encoding="utf-8-sig", errors="replace")
        sup = f_py(texto) if p.suffix == ".py" else None
        sup = f_texto(texto, p.suffix.lower()) if sup is None else sup
        h.update(p.relative_to(alvo if alvo.is_dir() else alvo.parent).as_posix().encode() + b"\0" + sup.encode() + b"\0")
    return h.hexdigest()[:16]


def digital_modulo_v1(repo: Path, modulo: str) -> str:
    """Digital do algoritmo antigo (16 hex, sem prefixo): serve só para comparar com o que um mapa antigo guardou."""
    return _calcular_digital(repo, modulo, _digital_py_v1, lambda t, s: _digital_texto_v1(t)) or ""


def digital_modulo(repo: Path, modulo: str) -> str:
    """Versão 2: "2:" + sha256 curto da superfície pública do módulo (arquivo, ou pasta com '/' no fim); "" se o módulo
    não existe."""
    d = _calcular_digital(repo, modulo, _digital_py, _digital_texto)
    return "2:" + d if d else ""


def _unir(a: list[str], b: list[str]) -> list[str]:
    """As duas listas numa só, sem repetir e na ordem em que aparecem."""
    return list(dict.fromkeys([*a, *b]))


def caminho_decisoes(arq: Path) -> Path:
    return arq / ".lodemap" / "decisoes-modelo.json"


def sugerir(repo: Path, arq: Path, fonte: str = "auto", db: Path | None = None) -> dict:
    """Componentes e relações sugeridos pelo código, sem decisão nenhuma."""
    globs = cp._globs_modulos(arq)
    if not globs:
        raise ValueError(t(f"{arq / 'lodemap.json'} não tem 'modulos': rode novo_mapa.py antes",
                           f"{arq / 'lodemap.json'} has no 'modulos': run novo_mapa.py first"))
    inv = cp.rascunho_inventario(repo, arq, fonte, db)
    # Todo módulo dos globs entra, mesmo os que o inventário não lê (.sh, .ps1, .html): é o que o gate de cobertura cobra.
    ignorar = cp._globs_ignorar(arq)
    por_modulo: dict[str, list[dict]] = {m: [] for m in modulos_dos_globs(repo, globs, ignorar)}
    for it in inv["arquivos"]:
        if it["modulo"] in por_modulo:
            por_modulo[it["modulo"]].append(it)
    arestas, usada = cp.carregar_arestas(repo, fonte, db)
    pares: dict[tuple[str, str], Counter] = defaultdict(Counter)
    for (a, b), tipos in arestas.items():
        ma, mb = cp._modulo_de(a, globs, ignorar), cp._modulo_de(b, globs, ignorar)
        if ma and mb and ma != mb and ma in por_modulo and mb in por_modulo:
            pares[(ma, mb)].update(tipos)
    usados: set[str] = set()
    comps = []
    for modulo in sorted(por_modulo):
        arqs = por_modulo[modulo]
        dica = next((a["docstringModulo"] for a in arqs if a.get("docstringModulo")), "") or \
            next((a["docstringPrimeiro"] for a in arqs if a.get("docstringPrimeiro")), "")
        simbolos = [s["nome"] for a in arqs for s in a.get("simbolos", [])][:8]
        langs = Counter(a.get("linguagem") or "" for a in arqs).most_common(1)
        linguagem = langs[0][0] if langs else EXTENSAO.get(Path(modulo.rstrip("/")).suffix, "")
        linhas = sum(a.get("linhas", 0) for a in arqs)
        if not arqs and not modulo.endswith("/") and (repo / modulo).is_file():
            linhas = (repo / modulo).read_bytes().count(b"\n") + 1
        comps.append({"id": _id_sugerido(modulo, usados), "modulo": modulo, "arquivos": max(len(arqs), 1),
                      "linhas": linhas, "linguagem": linguagem, "dica": dica, "simbolos": simbolos,
                      "lido_pelo_inventario": bool(arqs)})
    rels = [{"de": a, "para": b, "arestas": sum(t.values()), "tipos": dict(t)} for (a, b), t in sorted(pares.items())]
    return {"fonte": usada, "componentes": comps, "relacoes": rels}


def rascunho(repo: Path, arq: Path, fonte: str = "auto", db: Path | None = None, gravar: bool = True) -> dict:
    """Junta as sugestões com as decisões já tomadas e grava o arquivo de decisões (com gravar=False, só calcula)."""
    sug = sugerir(repo, arq, fonte, db)
    destino = caminho_decisoes(arq)
    antigo = json.loads(destino.read_text(encoding="utf-8")) if destino.is_file() else {}
    antigos_c = {c["modulo"]: c for c in antigo.get("componentes", [])}
    antigos_r = {(r["de"], r["para"]): r for r in antigo.get("relacoes", [])}
    usados = {c["id"] for c in antigos_c.values()}
    comps, novos, revisar = [], [], []
    for c in sug["componentes"]:
        velho = antigos_c.get(c["modulo"])
        c["digital"] = digital_modulo(repo, c["modulo"])
        if velho:
            # A superfície pública mudou e havia descrição decidida: o modelador revisa só este. Decisão sem
            # digital (mapa anterior a esta versão) só ganha a digital, sem virar revisão. Digital guardada sem o
            # prefixo "2:" é da v1: compara com a v1 do código atual, para o mapa antigo não virar revisão em massa
            # (o que só a v2 enxerga entra na primeira rodada e vale a partir da seguinte).
            guardada = velho.get("digital")
            if guardada and velho.get("descricao"):
                atual = c["digital"] if guardada.startswith("2:") else digital_modulo_v1(repo, c["modulo"])
                if guardada != atual:
                    revisar.append(c["modulo"])
            item = {**velho, **{k: c[k] for k in ("arquivos", "linhas", "linguagem", "dica", "simbolos",
                                                  "lido_pelo_inventario", "digital")}}
        else:
            if c["id"] in usados:
                c["id"] = _id_sugerido(c["modulo"] + "/x", usados)
            usados.add(c["id"])
            item = {**c, **{k: "" for k in CAMPOS_COMPONENTE}, "tecnologia": "", "tags": [], "propriedades": {}}
            novos.append(c["modulo"])
        comps.append(item)
    vivos = {c["modulo"] for c in comps}
    removidos = sorted(set(antigos_c) - vivos)
    rels, rels_novas = [], []
    for r in sug["relacoes"]:
        velha = antigos_r.get((r["de"], r["para"]))
        if velha:
            velha = {k: v for k, v in velha.items() if k != "manual"}  # o código mostra: deixou de ser manual
            rels.append({**velha, "arestas": r["arestas"], "tipos": r["tipos"], "sumiu_do_codigo": False})
            if velha.get("manter") is None:  # sugerida num rascunho anterior e ainda sem decisão: continua pendente
                rels_novas.append(f"{r['de']} -> {r['para']}")
        else:
            rels.append({**r, "verbo": "", "tecnologia": "", "manter": None})
            rels_novas.append(f"{r['de']} -> {r['para']}")
    # Relação decidida que o código não mostra mais: fica, marcada, para o modelador decidir (pode ser HTTP, subprocess).
    # A que nunca foi decidida (manter vazio) era só sugestão do código: sem o código, some.
    sug_pares = {(r["de"], r["para"]) for r in sug["relacoes"]}
    for par, velha in antigos_r.items():
        if par not in sug_pares and par[0] in vivos and par[1] in vivos and velha.get("manter") is True:
            # `manual`: o modelador a acrescentou sabendo que o código não a mostra (HTTP, config, import tardio).
            rels.append({**velha, "arestas": 0, "sumiu_do_codigo": not velha.get("manual")})
    # Pendência que ninguém resolveu continua pendente: rodar o rascunho duas vezes não apaga o que falta fazer
    # (a digital já foi regravada na primeira vez). Quem limpa: o descrever.py ao descrever, o renderizar ao aceitar.
    pend_velho = antigo.get("pendentes", {})
    sem_descricao = {c["modulo"] for c in comps if not (c.get("descricao") or c.get("fundir_em"))}
    # "novo" é o componente que ainda não tem descrição: o que o modelador já descreveu não volta para a lista.
    novos = _unir(novos, [m for m in pend_velho.get("componentes_novos", []) if m in sem_descricao])
    revisar = _unir(revisar, [m for m in pend_velho.get("componentes_revisar", []) if m in vivos])
    para_modelador = [x for x in pend_velho.get("descricoes_para_modelador", [])
                      if isinstance(x, dict) and x.get("modulo") in sem_descricao]
    dados = {
        "versao": 1,
        "geradoEm": datetime.now().astimezone().isoformat(timespec="seconds"),
        "fonte_arestas": sug["fonte"],
        "como_preencher": "Componente: fundir_em=<id> para juntar o módulo a outro componente, ou nome, descricao (uma frase do que faz), container (id em 'containers'), area "
                          "(chave em 'areas'), status (" + ", ".join(STATUS) + "). Relação: confirme no código; "
                          "manter=true com verbo no presente, ou manter=false. Relação real que os imports não mostram (HTTP, "
                          "escolha por configuração, import tardio): acrescente {de, para, verbo, manter: true, "
                          "manual: true}, com de e para iguais ao 'modulo' dos componentes. "
                          "Depois: esqueleto.py renderizar.",
        "containers": antigo.get("containers", []),
        "areas": antigo.get("areas", {}),
        "componentes": comps,
        "relacoes": rels,
        "removidos": removidos,
        "pendentes": {"componentes_novos": novos, "componentes_revisar": revisar, "relacoes_novas": rels_novas,
                      **({"descricoes_para_modelador": para_modelador} if para_modelador else {}),
                      "componentes_sem_container_ou_status": sorted(
                          c["modulo"] for c in comps
                          if not c.get("fundir_em") and not (c.get("container") and c.get("status")))},
    }
    if gravar:
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(json.dumps(dados, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    return dados


def validar(d: dict) -> list[str]:
    erros = []
    conts = {c.get("id") for c in d.get("containers", [])}
    if not conts:
        erros.append(t("nenhum container em 'containers'", "no container in 'containers'"))
    for c in d.get("containers", []):
        for campo in ("id", "nome", "descricao", "tecnologia", "status"):
            if not c.get(campo):
                erros.append(t(f"container {c.get('id', '?')}: falta '{campo}'",
                               f"container {c.get('id', '?')}: missing '{campo}'"))
        if c.get("status") and c["status"] not in STATUS:
            erros.append(t(f"container {c.get('id')}: status '{c['status']}' fora de {STATUS}",
                           f"container {c.get('id')}: status '{c['status']}' not in {STATUS}"))
    areas = d.get("areas", {})
    ids = Counter(c["id"] for c in d.get("componentes", []))
    erros += [t(f"id repetido: {i}", f"duplicate id: {i}") for i, n in ids.items() if n > 1]
    donos = {c["id"] for c in d.get("componentes", []) if not c.get("fundir_em")}
    for c in d.get("componentes", []):
        if c.get("fundir_em"):
            if c["fundir_em"] not in donos:
                erros.append(t(f"{c['modulo']}: fundir_em '{c['fundir_em']}' não é um componente que fica",
                               f"{c['modulo']}: fundir_em '{c['fundir_em']}' is not a component that stays"))
            continue
        faltam = [k for k in CAMPOS_COMPONENTE if not c.get(k)]
        if faltam:
            erros.append(t(f"{c['modulo']}: falta {', '.join(faltam)}", f"{c['modulo']}: missing {', '.join(faltam)}"))
            continue
        if c["container"] not in conts:
            erros.append(t(f"{c['modulo']}: container '{c['container']}' não existe",
                           f"{c['modulo']}: container '{c['container']}' does not exist"))
        if c["area"] not in areas:
            erros.append(t(f"{c['modulo']}: área '{c['area']}' não está em 'areas'",
                           f"{c['modulo']}: area '{c['area']}' is not in 'areas'"))
        if c["status"] not in STATUS:
            erros.append(t(f"{c['modulo']}: status '{c['status']}' fora de {STATUS}",
                           f"{c['modulo']}: status '{c['status']}' not in {STATUS}"))
        ruins = set(c.get("tags", [])) - TAGS_EXTRAS
        if ruins:
            erros.append(t(f"{c['modulo']}: tags desconhecidas {sorted(ruins)}",
                           f"{c['modulo']}: unknown tags {sorted(ruins)}"))
    for r in d.get("relacoes", []):
        if r.get("manter") is None:
            erros.append(t(f"relação {r['de']} -> {r['para']}: decida manter=true ou false",
                           f"relationship {r['de']} -> {r['para']}: decide manter=true or false"))
        elif r["manter"] and not r.get("verbo"):
            erros.append(t(f"relação {r['de']} -> {r['para']}: falta o verbo",
                           f"relationship {r['de']} -> {r['para']}: missing the verb"))
    return erros


def _props(props: dict, recuo: str) -> str:
    linhas = [f'{recuo}properties {{']
    linhas += [f'{recuo}    "{_escapar(k)}" "{_escapar(v)}"' for k, v in props.items() if v not in (None, "")]
    return "\n".join(linhas + [f"{recuo}}}"])


def _tecnologia(c: dict) -> str:
    if c.get("tecnologia"):
        return c["tecnologia"]
    nome = c["modulo"].rstrip("/").rsplit("/", 1)[-1] + ("/" if c["modulo"].endswith("/") else "")
    return f"{LINGUAGEM.get(c.get('linguagem', ''), c.get('linguagem', '') or 'Código')} {nome}".strip()


PENDENTES_DE_MODELO = ("componentes_novos", "componentes_revisar", "relacoes_novas", "descricoes_para_modelador",
                       "componentes_sem_container_ou_status")


def renderizar(arq: Path, decisoes: Path | None = None) -> dict:
    d = json.loads((decisoes or caminho_decisoes(arq)).read_text(encoding="utf-8"))
    erros = validar(d)
    if erros:
        raise ValueError(t("decisões incompletas:", "incomplete decisions:") + "\n  - " + "\n  - ".join(erros))
    modelo = arq / "model"
    modelo.mkdir(parents=True, exist_ok=True)
    por_cont: dict[str, dict[str, list]] = defaultdict(lambda: defaultdict(list))
    fundidos: dict[str, list[str]] = defaultdict(list)
    for c in d["componentes"]:
        if c.get("fundir_em"):
            fundidos[c["fundir_em"]].append(c["modulo"])
        else:
            por_cont[c["container"]][c["area"]].append(c)
    rot = ROTULO_EN if _idioma(arq) == "en" else ROTULO
    escritos = []
    blocos = [CABECALHO]
    for k in d["containers"]:
        tags = ",".join([k["status"], *k.get("tags", [])])
        blocos.append(f'{k["id"]} = container "{_escapar(k["nome"])}" "{_escapar(k["descricao"])}" '
                      f'"{_escapar(k["tecnologia"])}" "{tags}" {{')
        blocos.append(_props({"status": rot.get(k["status"], k["status"]), "codigo": k.get("codigo", ""), **k.get("propriedades", {})}, "    "))
        if k["id"] in por_cont:
            blocos.append(f"    !include componentes-{k['id']}.dsl")
        blocos.append("}\n")
    (modelo / "containers.dsl").write_text("\n".join(blocos), encoding="utf-8", newline="\n")
    escritos.append("model/containers.dsl")
    for cont, areas in por_cont.items():
        out = [CABECALHO]
        for area in sorted(areas, key=lambda a: list(d["areas"]).index(a)):
            out.append(f'group "{_escapar(d["areas"][area])}" {{')
            for c in sorted(areas[area], key=lambda x: x["modulo"]):
                tags = ",".join([c["status"], area, *c.get("tags", [])])
                out.append(f'    {c["id"]} = component "{_escapar(c["nome"])}" "{_escapar(c["descricao"])}" '
                           f'"{_escapar(_tecnologia(c))}" "{tags}" {{')
                out.append(_props({"status": rot.get(c["status"], c["status"]), "area": area, "codigo": ", ".join([c["modulo"], *sorted(fundidos[c["id"]])]),
                                   **c.get("propriedades", {})}, "        "))
                out.append("    }")
            out.append("}\n")
        nome = f"componentes-{cont}.dsl"
        (modelo / nome).write_text("\n".join(out), encoding="utf-8", newline="\n")
        escritos.append(f"model/{nome}")
    # Arquivo de componentes que não vale mais: o gerado por nós e o exemplo do template saem; o escrito à mão fica.
    avisos = []
    validos = {f"componentes-{c}.dsl" for c in por_cont}
    for f in sorted(modelo.glob("componentes-*.dsl")):
        if f.name in validos:
            continue
        texto = f.read_text(encoding="utf-8-sig")
        if texto.startswith(CABECALHO.strip()[:40]) or "Troque pelo módulo real" in texto:
            f.unlink()
            escritos.append(f"model/{f.name} (removido)")
        else:
            avisos.append(t(f"model/{f.name} foi escrito à mão e não é incluído por containers.dsl",
                            f"model/{f.name} was written by hand and is not included by containers.dsl"))
    ids = {c["modulo"]: c.get("fundir_em") or c["id"] for c in d["componentes"]}
    linhas = [CABECALHO]
    mantidas = 0
    vistos: set[tuple[str, str]] = set()
    for r in sorted(d["relacoes"], key=lambda x: (x["de"], x["para"])):
        if not r.get("manter") or r["de"] not in ids or r["para"] not in ids:
            continue
        par = (ids[r["de"]], ids[r["para"]])
        if par[0] == par[1] or par in vistos:
            continue  # fusão virou laço ou repetiu um par: uma seta por par de componentes
        vistos.add(par)
        tag = f' "{r["tag"]}"' if r.get("tag") else ""
        linhas.append(f'{ids[r["de"]]} -> {ids[r["para"]]} "{_escapar(r["verbo"])}" '
                      f'"{_escapar(r.get("tecnologia") or "chamada direta")}"{tag}')
        mantidas += 1
    (modelo / "relacoes-componentes.dsl").write_text("\n".join(linhas) + "\n", encoding="utf-8", newline="\n")
    escritos.append("model/relacoes-componentes.dsl")
    rel = modelo / "relacoes.dsl"
    texto = rel.read_text(encoding="utf-8-sig") if rel.is_file() else ""
    if "!include relacoes-componentes.dsl" not in texto:
        rel.write_text(texto.rstrip("\n") + "\n\n        !include relacoes-componentes.dsl\n", encoding="utf-8",
                       newline="\n")
        escritos.append("model/relacoes.dsl (include)")
    escritos += _renderizar_visoes(arq, d, por_cont, _idioma(arq), avisos)
    # As decisões passaram na validação e viraram DSL: o que estava pendente de modelo deixa de estar.
    pend = d.get("pendentes") or {}
    if any(pend.get(k) for k in PENDENTES_DE_MODELO):
        d["pendentes"] = {**pend, **{k: [] for k in PENDENTES_DE_MODELO if k in pend}}
        (decisoes or caminho_decisoes(arq)).write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n",
                                                       encoding="utf-8", newline="\n")
    if re.search(r"->\s*appEntrada\b", texto) and "appEntrada" not in ids.values():
        avisos.append(t("model/relacoes.dsl ainda tem as setas de exemplo do template (appEntrada): troque pelas reais",
                        "model/relacoes.dsl still has the template's example arrows (appEntrada): replace them with "
                        "the real ones"))
    return {"componentes": sum(not c.get("fundir_em") for c in d["componentes"]), "containers": len(d["containers"]), "relacoes": mantidas,
            "escritos": escritos, "avisos": avisos}

# Visões estáticas por regra (contexto, containers, componentes por container e por área, status). Os fluxos
# (visões dinâmicas) pedem julgamento e continuam com o modelador, em views/visoes.dsl.
TEXTO_VISOES = {
    "pt": {"ctx": ("Contexto", "Quem usa o sistema e com o que ele conversa."),
           "cont": ("Containers", "Os processos e os dados."),
           "comp": ("{n}: componentes", "Todos os componentes de {n}."),
           "area": ("{n}: {a}", "Componentes da área {a} em {n}."),
           "st": "Componentes de {n} com status {s}.",
           "cab": "// Visões estáticas em views/visoes-geradas.dsl (esqueleto.py). Aqui ficam só os fluxos (visões\n"
                  "// dinâmicas), escritos pelo modelador. Cada passo precisa de uma relação que exista no modelo.\n"},
    "en": {"ctx": ("Context", "Who uses the system and what it talks to."),
           "cont": ("Containers", "The processes and the data."),
           "comp": ("{n}: components", "Every component of {n}."),
           "area": ("{n}: {a}", "Components of the {a} area in {n}."),
           "st": "Components of {n} with status {s}.",
           "cab": "// Static views in views/visoes-geradas.dsl (esqueleto.py). Only the flows (dynamic views) live\n"
                  "// here, written by the modeler. Every step needs a relationship that exists in the model.\n"},
}
MIN_COMPONENTES_POR_AREA = 12  # abaixo disso a visão do container inteiro já se lê
CABECALHO_VISOES = "// Gerado por scripts/esqueleto.py a partir de .lodemap/decisoes-modelo.json. Fluxos: views/visoes.dsl.\n"


def _visao(tipo: str, alvo: str, chave: str, titulo: str, desc: str, include: str = "*") -> str:
    return (f'{tipo} {alvo} "{chave}" "{_escapar(desc)}" {{\n    include {include}\n    autoLayout lr 150 50\n'
            f'    title "{_escapar(titulo)}"\n}}\n')


def _renderizar_visoes(arq: Path, d: dict, por_cont: dict, idioma: str, avisos: list) -> list[str]:
    tx = TEXTO_VISOES[idioma]
    rot = ROTULO_EN if idioma == "en" else ROTULO
    out = [CABECALHO_VISOES,
           _visao("systemContext", "sistema", "Contexto", *tx["ctx"]),
           _visao("container", "sistema", "Containers", *tx["cont"])]
    nomes = {k["id"]: k["nome"] for k in d["containers"]}
    ordem_areas = list(d["areas"])
    for cid in [k["id"] for k in d["containers"] if k["id"] in por_cont]:
        areas = por_cont[cid]
        n = nomes.get(cid, cid)
        base = f"Componentes-{cid}"
        out.append(_visao("component", cid, base, tx["comp"][0].format(n=n), tx["comp"][1].format(n=n)))
        total = sum(len(v) for v in areas.values())
        if len(areas) > 1 and total >= MIN_COMPONENTES_POR_AREA:
            for area in sorted(areas, key=ordem_areas.index):
                rotulo = d["areas"][area]
                out.append(_visao("component", cid, f"Area-{cid}-{area.removeprefix('Area')}",
                                  tx["area"][0].format(n=n, a=rotulo), tx["area"][1].format(n=n, a=rotulo),
                                  f'"element.tag=={area}"'))
        presentes = {c["status"] for v in areas.values() for c in v}
        if len(presentes) > 1:
            for st in STATUS:
                if st in presentes:
                    out.append(f'filtered "{base}" include "{st}" "Status-{cid}-{st}" '
                               f'"{_escapar(tx["st"].format(n=n, s=rot.get(st, st)))}"\n')
    pasta = arq / "views"
    pasta.mkdir(parents=True, exist_ok=True)
    (pasta / "visoes-geradas.dsl").write_text("\n".join(out), encoding="utf-8", newline="\n")
    escritos = ["views/visoes-geradas.dsl"]
    manual = pasta / "visoes.dsl"
    texto = manual.read_text(encoding="utf-8-sig") if manual.is_file() else ""
    if "!include visoes-geradas.dsl" in texto:
        return escritos
    if not texto.strip() or ("appEntrada" in texto and "Fluxo-principal" in texto):
        corpo = "".join("        " + l + "\n" for l in tx["cab"].splitlines())
        manual.write_text("        !include visoes-geradas.dsl\n\n" + corpo, encoding="utf-8", newline="\n")
        escritos.append("views/visoes.dsl (include, sem o exemplo)")
    else:
        avisos.append(t("views/visoes.dsl foi escrito à mão: para usar as visões geradas, tire de lá as estáticas "
                        "e acrescente '!include visoes-geradas.dsl'",
                        "views/visoes.dsl was written by hand: to use the generated views, remove the static ones "
                        "from it and add '!include visoes-geradas.dsl'"))
    return escritos



def main(argv=None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    ap = argparse.ArgumentParser(description=t("Esqueleto do modelo C4 por script: o modelador decide em JSON curto, "
                                               "o script escreve o DSL.",
                                               "C4 model skeleton by script: the modeler decides in short JSON, "
                                               "the script writes the DSL."))
    sub = ap.add_subparsers(dest="cmd", required=True, title=t("subcomandos", "subcommands"),
                            metavar=t("{rascunho,pendencias,renderizar}", "{draft,pending,render}"))

    def comando(en: str, pt: str, ajuda: str):
        nome, apelido = opcao(en, pt)
        return sub.add_parser(nome, aliases=[apelido], help=ajuda, description=ajuda)

    def pasta(p, obrigatorio=True):
        p.add_argument("--arq", "--arch", required=obrigatorio,
                       help=t("pasta structurizr do projeto", "the project's structurizr folder"))

    def origem(p):
        pasta(p)
        p.add_argument("--repo", help=t("raiz do repositório (padrão: raiz do git de --arq)",
                                        "repository root (default: the git root of --arq)"))
        p.add_argument(*opcao("--source", "--fonte"), dest="fonte", choices=["auto", "codegraph", "ast"],
                       default="auto", help=t("de onde vêm as arestas do código", "where the code edges come from"))
        p.add_argument("--db", help=t("índice do CodeGraph em outro lugar", "CodeGraph index somewhere else"))

    r = comando("draft", "rascunho", t("grava/atualiza .lodemap/decisoes-modelo.json",
                                       "write/update .lodemap/decisoes-modelo.json"))
    origem(r)
    q = comando("pending", "pendencias", t("o que o rascunho acharia pendente, em JSON, sem gravar nada",
                                           "what the draft would find pending, as JSON, writing nothing"))
    origem(q)
    v = comando("render", "renderizar", t("escreve o DSL a partir das decisões", "write the DSL from the decisions"))
    pasta(v)
    v.add_argument(*opcao("--decisions", "--decisoes"), dest="decisoes",
                   help=t("arquivo de decisões (padrão: <arq>/.lodemap/decisoes-modelo.json)",
                          "decisions file (default: <arq>/.lodemap/decisoes-modelo.json)"))
    a = ap.parse_args(argv)
    arq = Path(a.arq).resolve()
    usar_mapa(arq)
    a.cmd = {"draft": "rascunho", "pending": "pendencias", "render": "renderizar"}.get(a.cmd, a.cmd)
    if a.cmd == "pendencias":
        repo = Path(a.repo).resolve() if a.repo else cp.raiz_repo(arq)
        sem_decisoes = not caminho_decisoes(arq).is_file()
        try:
            d = rascunho(repo, arq, a.fonte, Path(a.db) if a.db else None, gravar=False)
        except ValueError as e:
            print(t("erro:", "error:"), e, file=sys.stderr)
            return 2
        p = d["pendentes"]
        saida = {"componentes_novos": p["componentes_novos"], "componentes_revisar": p["componentes_revisar"],
                 "relacoes_novas": p["relacoes_novas"], "removidos": d["removidos"]}
        if sem_decisoes:  # sem decisões anteriores todo módulo conta como novo: os números não dizem nada
            saida["sem_decisoes"] = True
        print(json.dumps(saida, ensure_ascii=False, indent=1))
        return 0
    if a.cmd == "rascunho":
        repo = Path(a.repo).resolve() if a.repo else cp.raiz_repo(arq)
        try:
            d = rascunho(repo, arq, a.fonte, Path(a.db) if a.db else None)
        except ValueError as e:
            print(t("erro:", "error:"), e)
            return 2
        p = d["pendentes"]
        if t("pt", "en") == "en":
            print(f"decisions ({d['fonte_arestas']}): {len(d['componentes'])} components, {len(d['relacoes'])} "
                  f"suggested relationships; new {len(p['componentes_novos'])}, to review (public surface changed) "
                  f"{len(p['componentes_revisar'])}, new relationships {len(p['relacoes_novas'])}, "
                  f"removed {len(d['removidos'])} -> {caminho_decisoes(arq)}")
        else:
            print(f"decisões ({d['fonte_arestas']}): {len(d['componentes'])} componentes, {len(d['relacoes'])} relações "
                  f"sugeridas; novos {len(p['componentes_novos'])}, a revisar (superfície mudou) "
                  f"{len(p['componentes_revisar'])}, relações novas {len(p['relacoes_novas'])}, "
                  f"removidos {len(d['removidos'])} -> {caminho_decisoes(arq)}")
        return 0
    try:
        res = renderizar(arq, Path(a.decisoes) if a.decisoes else None)
    except ValueError as e:
        print(t("erro:", "error:"), e)
        return 3
    if t("pt", "en") == "en":
        print(f"DSL: {res['containers']} containers, {res['componentes']} components, {res['relacoes']} "
              "relationships -> " + ", ".join(res["escritos"]))
    else:
        print(f"DSL: {res['containers']} containers, {res['componentes']} componentes, {res['relacoes']} relações -> "
              + ", ".join(res["escritos"]))
    for aviso in res["avisos"]:
        print(t("aviso:", "warning:"), aviso)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
