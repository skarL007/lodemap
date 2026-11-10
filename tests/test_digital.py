"""Impressão digital semântica por módulo (esqueleto.digital_modulo): só a superfície pública conta.

Mudou o corpo de uma função, um comentário ou a formatação: a digital fica igual e a descrição decidida continua
valendo (0 chamadas de modelo). Mudou docstring, import, assinatura, símbolo público ou constante de topo: o módulo
entra em pendentes.componentes_revisar.
"""
from __future__ import annotations

import json
import re

from test_esqueleto import _arq, _preencher, esqueleto, projeto  # noqa: F401  (fixture)


def _py(tmp_path, texto):
    p = tmp_path / "m.py"
    p.write_text(texto, encoding="utf-8")
    return esqueleto.digital_modulo(tmp_path, "m.py")


def test_corpo_comentario_e_formatacao_nao_mudam_a_digital(tmp_path):
    base = '"""Doc."""\nimport os\n\nLIMITE = 3\n\n\ndef f(a, b=1):\n    """Soma."""\n    return a + b\n'
    corpo = '"""Doc."""\nimport os\n\nLIMITE = 3\n\n\ndef f(a, b=1):\n    """Soma."""\n    # explica\n    x = a\n    return x + b\n'
    assert _py(tmp_path, base) == _py(tmp_path, corpo)


def test_superficie_publica_muda_a_digital(tmp_path):
    base = _py(tmp_path, '"""Doc."""\nimport os\n\n\ndef f(a):\n    return a\n')
    variantes = [
        '"""Outra doc."""\nimport os\n\n\ndef f(a):\n    return a\n',
        '"""Doc."""\nimport sys\n\n\ndef f(a):\n    return a\n',
        '"""Doc."""\nimport os\n\n\ndef f(a, b):\n    return a\n',
        '"""Doc."""\nimport os\n\n\ndef f(a):\n    return a\n\n\ndef g():\n    pass\n',
        '"""Doc."""\nimport os\n\nTETO = 1\n\n\ndef f(a):\n    return a\n',
    ]
    for v in variantes:
        assert _py(tmp_path, v) != base, v


def test_outras_linguagens_olham_declaracoes_e_imports(tmp_path):
    def js(t):
        (tmp_path / "m.js").write_text(t, encoding="utf-8")
        return esqueleto.digital_modulo(tmp_path, "m.js")
    base = js("import { a } from './a';\nexport function soma(x, y) {\n  return x + y;\n}\n")
    assert js("import { a } from './a';\nexport function soma(x, y) {\n  const z = x;\n  return z + y;\n}\n") == base
    assert js("import { a } from './a';\nexport function soma(x, y, w) {\n  return x + y;\n}\n") != base
    assert js("import { b } from './b';\nexport function soma(x, y) {\n  return x + y;\n}\n") != base


def test_pasta_combina_os_arquivos_e_ausente_e_vazio(tmp_path):
    (tmp_path / "p").mkdir()
    (tmp_path / "p" / "a.py").write_text("def a():\n    pass\n", encoding="utf-8")
    d1 = esqueleto.digital_modulo(tmp_path, "p/")
    (tmp_path / "p" / "b.py").write_text("def b():\n    pass\n", encoding="utf-8")
    assert esqueleto.digital_modulo(tmp_path, "p/") != d1
    assert esqueleto.digital_modulo(tmp_path, "nao/existe.py") == ""


def test_rascunho_so_pede_revisao_quando_a_superficie_muda(projeto):  # noqa: F811
    arq = _arq(projeto)
    d = _preencher(esqueleto.rascunho(projeto, arq, fonte="ast"))
    assert all(c.get("digital") for c in d["componentes"]), "cada componente guarda a digital"
    esqueleto.caminho_decisoes(arq).write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    # só corpo: nada a revisar, decisão intacta
    api = projeto / "app" / "api.py"
    api.write_text(api.read_text(encoding="utf-8").replace("return regras.calcular()",
                                                           "v = regras.calcular()\n    return v"), encoding="utf-8")
    d2 = esqueleto.rascunho(projeto, arq, fonte="ast")
    assert d2["pendentes"]["componentes_revisar"] == []
    assert next(c for c in d2["componentes"] if c["modulo"] == "app/api.py")["nome"] == "app/api.py"
    # superfície: função pública nova no regras.py
    regras = projeto / "app" / "regras.py"
    regras.write_text(regras.read_text(encoding="utf-8") + "\n\ndef auditar():\n    return 0\n", encoding="utf-8")
    d3 = esqueleto.rascunho(projeto, arq, fonte="ast")
    assert d3["pendentes"]["componentes_revisar"] == ["app/regras.py"]
    rev = next(c for c in d3["componentes"] if c["modulo"] == "app/regras.py")
    assert rev["descricao"], "a decisão antiga fica até o modelador revisar"


# ---------------------------------------------------------------------------------------------------------------
# Digital v2: formato, v1 congelada e as regras de adição (só nomes e assinaturas, nunca valor, corpo ou decorador).
# ---------------------------------------------------------------------------------------------------------------

def _arquivo(tmp_path, nome, texto):
    p = tmp_path / nome
    p.write_text(texto, encoding="utf-8")
    return esqueleto.digital_modulo(tmp_path, nome)


def _muda(tmp_path, nome, base, *variantes):
    """Todas as variantes têm digital diferente da base."""
    d0 = _arquivo(tmp_path, nome, base)
    for v in variantes:
        assert _arquivo(tmp_path, nome, v) != d0, v


def _igual(tmp_path, nome, base, *variantes):
    """Nenhuma variante muda a digital da base."""
    d0 = _arquivo(tmp_path, nome, base)
    for v in variantes:
        assert _arquivo(tmp_path, nome, v) == d0, v


def test_formato_da_v2_e_v1_congelada(tmp_path):
    py = '"""Doc."""\nimport os\n\nLIMITE = 3\n\n\ndef f(a, b=1):\n    """Soma."""\n    return a + b\n\n\nclass K(object):\n    def m(self, x):\n        pass\n'
    js = "import { a } from './a';\nexport function soma(x, y) {\n  return x + y;\n}\n"
    go = "package m\n\nfunc Soma(a int, b int) int {\n\treturn a + b\n}\n"
    for nome, texto, v1 in (("m.py", py, "e21205203d02f694"), ("m.js", js, "ce384616c02da71d"),
                            ("m.go", go, "9bb55f61e31225f4")):
        (tmp_path / nome).write_text(texto, encoding="utf-8")
        v2 = esqueleto.digital_modulo(tmp_path, nome)
        assert re.fullmatch(r"2:[0-9a-f]{16}", v2), v2
        # o algoritmo antigo continua byte a byte o mesmo (valores medidos antes da v2)
        assert esqueleto.digital_modulo_v1(tmp_path, nome) == v1
    assert esqueleto.digital_modulo(tmp_path, "nao/existe.py") == ""
    assert esqueleto.digital_modulo_v1(tmp_path, "nao/existe.py") == ""


def test_outras_linguagens_ficam_com_as_regras_de_hoje(tmp_path):
    for nome, texto in (("m.go", "package m\n\nfunc Soma(a int, b int) int {\n\treturn a + b\n}\n"),
                        ("M.java", "public class M {\n    public int soma(int a, int b) { return a + b; }\n}\n"),
                        ("m.rs", "pub fn soma(a: i32, b: i32) -> i32 {\n    a + b\n}\n")):
        (tmp_path / nome).write_text(texto, encoding="utf-8")
        assert esqueleto.digital_modulo(tmp_path, nome) == "2:" + esqueleto.digital_modulo_v1(tmp_path, nome), nome
    # espaço dentro da declaração continua contando fora do JS/TS (regra de hoje)
    _muda(tmp_path, "m.go", "func Soma(a int, b int) int {\n}\n", "func Soma(a int,b int) int {\n}\n")


# ---- Python

def test_py_variavel_publica_de_topo_com_qualquer_caixa(tmp_path):
    base = "def f():\n    pass\n"
    # caso real do rich (tree.py): alias de tipo público novo
    _muda(tmp_path, "m.py", base,
          base + "\nGuideType = Tuple[str, str, str, str]\n",
          base + "\nconfig = {}\n",
          base + "\nlimite: int = 3\n",
          base + "\nPadrao: int\n",
          base + "\na, b = 1, 2\n")
    com = base + "\nGuideType = Tuple[str, str, str, str]\nconfig = {'a': 1}\n"
    _igual(tmp_path, "m.py", com,
           com.replace("{'a': 1}", "{'a': 2, 'b': 3}"),           # valor não conta
           com.replace("Tuple[str, str, str, str]", "Tuple[int]"),  # nem o valor do alias
           com + "\n_privada = 1\n")                                 # nome privado fica fora
    # __all__ continua com o valor e constante MAIÚSCULA continua só pelo nome (regras de hoje)
    _muda(tmp_path, "m.py", "__all__ = ['a']\n", "__all__ = ['a', 'b']\n")
    _igual(tmp_path, "m.py", "LIMITE = 3\n", "LIMITE = 4\n")


def test_py_atributo_de_classe_publico(tmp_path):
    base = "class Tree:\n    def render(self):\n        pass\n"
    # caso real do rich (tree.py): ASCII_GUIDES novo em classe
    novo = "class Tree:\n    ASCII_GUIDES = ('    ', '|   ')\n\n    def render(self):\n        pass\n"
    _muda(tmp_path, "m.py", base, novo,
          "class Tree:\n    nome: str\n\n    def render(self):\n        pass\n",
          "class Tree:\n    nome: str = 'x'\n\n    def render(self):\n        pass\n",
          "class Tree:\n    a, b = 1, 2\n\n    def render(self):\n        pass\n")
    _igual(tmp_path, "m.py", novo,
           novo.replace("('    ', '|   ')", "('  ', '| ')"),                      # valor não conta
           novo.replace("pass", "return None  # corpo"),                           # corpo não conta
           novo.replace("    def render", "    _oculto = 1\n\n    def render"))     # privado fica fora
    # classe privada continua fora
    _igual(tmp_path, "m.py", "class _P:\n    pass\n", "class _P:\n    x = 1\n")


def test_py_atributo_de_instancia_do_init(tmp_path):
    base = "class H:\n    def __init__(self, a):\n        self.a = a\n"
    # caso real do rich (logging.py): self.tracebacks_code_width novo (sem mexer na assinatura)
    novo = base + "        self.tracebacks_code_width = 88\n"
    _muda(tmp_path, "m.py", base, novo,
          base + "        self.largura: int = 88\n",
          base + "        self.x, self.y = 1, 2\n",
          base + "        if a:\n            self.cond = 1\n")
    _igual(tmp_path, "m.py", novo,
           novo.replace("= 88", "= 120"),                      # valor não conta
           novo + "        self._interno = 1\n",              # privado fica fora
           novo + "        self.a.b = 3\n",                   # atributo de outro objeto não é da instância
           novo + "        print(self.a)\n")                  # corpo não conta
    # atribuição fora do __init__ não entra
    _igual(tmp_path, "m.py", base, base + "\n    def _abre(self):\n        self.aberto = True\n")


def test_py_assinatura_do_init_e_classes_aninhadas(tmp_path):
    base = "class H:\n    def __init__(self, a):\n        pass\n"
    _muda(tmp_path, "m.py", base,
          base.replace("(self, a)", "(self, a, b)"),
          base.replace("(self, a)", "(self, a, *, b=None)"),
          base.replace("(self, a)", "(self)"))
    _igual(tmp_path, "m.py", base, base.replace("pass", "x = 1\n        y = 2"))
    ninho = "class H:\n    class Meta:\n        def campo(self):\n            pass\n"
    _muda(tmp_path, "m.py", "class H:\n    def m(self):\n        pass\n",
          "class H:\n    class Meta:\n        pass\n\n    def m(self):\n        pass\n")
    _muda(tmp_path, "m.py", ninho,
          ninho.replace("    class Meta", "    class Outro:\n        pass\n\n    class Meta"),
          ninho + "        def novo(self):\n            pass\n",
          ninho.replace("campo", "campo2"))
    _igual(tmp_path, "m.py", ninho,
           ninho.replace("pass", "return 1"),
           ninho + "        def _privado(self):\n            pass\n",
           ninho + "\n    class _Interna:\n        pass\n")


def test_py_o_que_nao_muda_hoje_continua_sem_mudar(tmp_path):
    base = ('"""Doc."""\nimport os\n\nLIMITE = 3\n_cache = {}\n\n\nclass K:\n    X = 1\n\n    def __init__(self, a):\n'
            '        self.a = a\n\n    def m(self, x):\n        """Faz."""\n        return x\n\n\ndef _aux(v):\n    return v\n\n\n'
            'def f(a, b=1):\n    """Soma."""\n    s = "texto"\n    return a + b\n')
    _igual(tmp_path, "m.py", base,
           base.replace('    s = "texto"\n', '    # comentário interno\n    s = "outro texto"\n    n = 42\n'),
           base.replace("return x\n", "y = x\n        return y\n"),
           base.replace("def _aux", "def _auxiliar"),
           base.replace("_cache = {}", "_cache = {1: 2}"),
           base.replace("\n\n\n", "\n\n\n\n\n\n"),
           base.replace("(a, b=1)", "(a,b=1)"))


# ---- JavaScript / TypeScript

TRANSITIONAL = ("export default {\n  silentJSONParsing: true,\n  forcedJSONParsing: true,\n"
                "  clarifyTimeoutError: false,\n};\n")


def test_js_chaves_do_primeiro_nivel_de_objeto_exportado(tmp_path):
    # caso real do axios (lib/defaults/transitional.js): chave nova em `export default {...}`
    _muda(tmp_path, "t.js", TRANSITIONAL,
          TRANSITIONAL.replace("};", "  advertiseZstdAcceptEncoding: false,\n};"),
          TRANSITIONAL.replace("  clarifyTimeoutError: false,\n", ""),
          TRANSITIONAL.replace("clarifyTimeoutError", "clarifyTimeout"))
    _igual(tmp_path, "t.js", TRANSITIONAL,
           TRANSITIONAL.replace("true", "false"),                                  # valor não conta
           TRANSITIONAL.replace("  forcedJSONParsing: true,\n  silentJSONParsing: true,\n", "")
           .replace("export default {\n", "export default {\n  forcedJSONParsing: true,\n  silentJSONParsing: true,\n"),  # ordem
           TRANSITIONAL.replace("  clarifyTimeoutError", "  // legado: oculto: 1,\n  clarifyTimeoutError"),  # comentário
           TRANSITIONAL.replace("false,", "{ aninhada: 1, outra: 2 },"))          # só o primeiro nível


def test_js_formas_do_objeto_exportado(tmp_path):
    corpo = ["  a: 1,", "  b,", "  c() { return 1; },", "  async d() {},", "  get e() { return 2; },", "  'f-g': 3,", "  [h]: 4,",
             "  ...base,"]
    obj = "{\n" + "\n".join(corpo) + "\n}"
    mais = obj[:-2] + "\n  novo: 1,\n}"
    # export default, export const, module.exports
    for cab in ("export default ", "export const X = ", "module.exports = ", "export const X: Config = "):
        base = f"{cab}{obj};\n"
        _muda(tmp_path, "o.ts" if "Config" in cab else "o.js", base, f"{cab}{mais};\n",
              base.replace("  b,", "  bb,"), base.replace("'f-g'", "'f-h'"), base.replace("c() {", "cc() {"),
              base.replace("...base", "...outra"))
        _igual(tmp_path, "o.ts" if "Config" in cab else "o.js", base,
               base.replace("a: 1", "a: 2").replace("return 1;", "return 3;").replace("3,", "4,"))
    # const X = {...} só conta quando X é exportado depois
    for fim in ("export default X;\n", "export { X };\n", "export { X as Y };\n", "module.exports = X;\n"):
        base = f"const X = {obj};\n{fim}"
        _muda(tmp_path, "o.js", base, f"const X = {mais};\n{fim}")
    solto = f"const X = {obj};\n"
    _igual(tmp_path, "o.js", solto, f"const X = {mais};\n")


def test_js_listas_de_export_e_export_estrela(tmp_path):
    base = "const a = 1;\nconst b = 2;\nexport {\n  a,\n  b as c,\n};\n"
    _muda(tmp_path, "e.js", base,
          base.replace("  b as c,\n", "  b as c,\n  d,\n"),
          base.replace("b as c", "b as z"),
          base.replace("  a,\n", ""))
    _igual(tmp_path, "e.js", base,
           base.replace("{\n  a,\n  b as c,\n}", "{ a, b as c }"),   # quebra de linha não conta
           base.replace("{\n  a,\n  b as c,\n}", "{ b as c, a }"))  # ordem não conta
    star = "export * from './a.js';\n"
    _muda(tmp_path, "e.js", star, star + "export * from './b.js';\n", "export * from './z.js';\n",
          star + "export * as ns from './b.js';\n", star + "export { x } from './b.js';\n")
    _igual(tmp_path, "e.js", star, "export  *  from  './a.js'  ;\n")


def test_js_lista_completa_de_parametros_da_funcao_exportada(tmp_path):
    # caso real do axios (progressEventReducer.js): `(fn)` ganhou `scheduler` numa declaração que quebra de linha
    base = "export const asyncDecorator =\n  (fn) =>\n  (...args) =>\n    utils.asap(() => fn(...args));\n"
    novo = ("export const asyncDecorator =\n  (fn, scheduler = utils.asap) =>\n  (...args) =>\n"
            "    scheduler(() => fn(...args));\n")
    _muda(tmp_path, "p.js", base, novo)
    # a forma do enunciado: `(fn)` -> `(fn,\n scheduler)` na própria linha da declaração
    _muda(tmp_path, "p.js", "export function asyncDecorator(fn) {\n  return fn;\n}\n",
          "export function asyncDecorator(fn,\n  scheduler) {\n  return fn;\n}\n")
    f = "export function f(\n  a,\n  b,\n) {\n  return a;\n}\n"
    _muda(tmp_path, "p.js", f, f.replace("  b,\n", "  b,\n  c,\n"), f.replace("  a,\n", "  a2,\n"))
    _igual(tmp_path, "p.js", f, f.replace("return a;", "return a + 1;"),
           f.replace("  a,\n", "  a, // primeiro\n"))
    # função exportada só depois, e `export default function`
    g = "function g(\n  a,\n  b\n) {\n  return a;\n}\nexport { g };\n"
    _muda(tmp_path, "p.js", g, g.replace("  b\n", "  b,\n  c\n"))
    h = "export default function h(\n  a\n) {\n}\n"
    _muda(tmp_path, "p.js", h, h.replace("  a\n", "  a,\n  z\n"))
    # função que não é exportada não entra (só a primeira linha, como hoje)
    i = "function i(\n  a,\n  b\n) {\n}\n"
    _igual(tmp_path, "p.js", i, i.replace("  b\n", "  b,\n  c\n"))


def test_js_membros_de_classe_exportada(tmp_path):
    base = ("export class Servico extends Base {\n  static padrao = 1;\n  nome;\n\n  constructor(a, b) {\n    super();\n    this.a = a;\n  }\n\n"
            "  static criar(x) {\n    return new Servico(x);\n  }\n\n  async buscar(id) {\n    return id;\n  }\n\n"
            "  get tamanho() {\n    return 1;\n  }\n\n  set tamanho(v) {\n  }\n\n  #segredo = 1;\n  _oculto = 2;\n"
            "  #priv() {\n  }\n  _interno(z) {\n  }\n}\n")
    _muda(tmp_path, "c.js", base,
          base.replace("constructor(a, b)", "constructor(a, b, c)"),       # constructor
          base.replace("buscar(id)", "buscar(id, opcoes)"),                # parâmetro de método
          base.replace("criar(x)", "criar(x, y)"),
          base.replace("async buscar", "buscar"),                          # modificador async
          base.replace("static criar", "criar"),                           # modificador static
          base.replace("get tamanho", "get tamanho2"),                     # getter renomeado
          base.replace("  nome;\n", "  nome;\n  extra = 3;\n"),            # campo novo
          base.replace("  nome;\n", ""),                                   # campo removido
          base.replace("  async buscar(id) {", "  novo(a) {\n  }\n\n  async buscar(id) {"))  # método novo
    _igual(tmp_path, "c.js", base,
           base.replace("super();", "super(); // base").replace("return id;", "console.log(id);\n    return id;"),
           base.replace("padrao = 1", "padrao = 2").replace("#segredo = 1", "#segredo = 9"),
           base.replace("_interno(z)", "_interno(z, w)"),                  # membro `_` fora
           base.replace("#priv() {", "#priv2() {"),                        # membro `#` fora
           base.replace("  _oculto = 2;\n", "  _oculto = 2;\n  _novo = 3;\n  #novo = 4;\n"),
           base.replace("  constructor(a, b)", "  constructor( a,   b )"))
    # classe exportada depois, `export default class` e classe não exportada
    solta = "class S {\n  m(a) {\n  }\n}\n"
    _igual(tmp_path, "c.js", solta, solta.replace("m(a)", "m(a, b)"))
    _muda(tmp_path, "c.js", solta + "export default S;\n", (solta + "export default S;\n").replace("m(a)", "m(a, b)"))
    _muda(tmp_path, "c.js", "export default class {\n  m(a) {\n  }\n}\n", "export default class {\n  m(a, b) {\n  }\n}\n")
    # TypeScript: membro `private` não é superfície
    ts = "export class T {\n  private x = 1;\n  public y = 2;\n  constructor(public z: number) {}\n}\n"
    _igual(tmp_path, "c.ts", ts, ts.replace("private x", "private w"))
    _muda(tmp_path, "c.ts", ts, ts.replace("public y", "public y2"), ts.replace("z: number", "z: string, k: number"))


def test_js_literal_de_regex_com_aspas_nao_engole_o_resto_do_arquivo(tmp_path):
    # o `'` e a crase dentro da regex abriam uma "string" que ia até a próxima crase e escondia a classe
    base = ("const nome = /^[!#$%&'*+\\-.^_`|~0-9A-Za-z]+$/;\nconst partes = /([^\\s,;=]+)\\s*(?:=\\s*([^,;]+))?/g;\n"
            "const metade = total / 2 / 3;\nconst txt = 'abre\\'';\n\nclass H {\n  m(a) {\n    return /`/.test(a);\n  }\n}\n"
            "export default H;\n")
    _muda(tmp_path, "r.js", base, base.replace("m(a)", "m(a, b)"), base.replace("  m(a) {", "  n(a) {\n  }\n\n  m(a) {"))
    _igual(tmp_path, "r.js", base, base.replace("test(a)", "test(a) && 1"), base.replace("/`/", "/'/"))
    obj = "export default {\n  a: /'/,\n  b: 1,\n};\n"
    _muda(tmp_path, "r.js", obj, obj.replace("  b: 1,", "  b: 1,\n  c: 2,"))
    # a barra de divisão e a de um comentário não viram regex
    _muda(tmp_path, "r.js", "const r = (a + b) / 2; // ' `\nexport default {\n  a: 1,\n};\n",
          "const r = (a + b) / 2; // ' `\nexport default {\n  a: 1,\n  b: 2,\n};\n")


def test_js_espaco_dentro_da_declaracao_nao_muda(tmp_path):
    base = ("import { a, b } from './a';\nexport function soma(x, y) {\n  return x + y;\n}\n"
            "export const dobro = (n, m) => n * 2;\nexport const K = { a: 1 };\n")
    _igual(tmp_path, "s.js", base,
           base.replace("{ a, b }", "{a,b}").replace("(x, y)", "(x,y)").replace("(n, m)", "( n ,m )"),
           base.replace("function soma", "function  soma").replace("export const dobro =", "export const dobro="),
           base.replace(") {\n  return x", ")   {\n  return x"),
           base.replace("{ a: 1 }", "{a:1}"))
    # nome ou ordem dos parâmetros continuam contando
    _muda(tmp_path, "s.js", base, base.replace("(x, y)", "(y, x)"), base.replace("(x, y)", "(x, y, z)"))


def test_js_o_que_nao_muda_hoje_continua_sem_mudar(tmp_path):
    base = ("import { a } from './a';\n\nexport default {\n  um: 1,\n  dois() {\n    return 2;\n  },\n};\n\n"
            "export function soma(x, y) {\n  const z = 'texto';\n  return x + y;\n}\n\nexport class C {\n  m(a) {\n    return a;\n  }\n}\n")
    _igual(tmp_path, "n.js", base,
           base.replace("const z = 'texto';", "// explica\n  const z = 'outro';\n  const n = 7;"),
           base.replace("return 2;", "return 3;"),
           base.replace("return a;", "return a + 1;"),
           base.replace("\n\n", "\n\n\n\n"),
           base.replace("export function", "// soma\nexport function"))


def test_js_texto_quebrado_ou_vazio_nao_levanta(tmp_path):
    for t in ("", "export default {\n  a: ", "export {", "class X { m(", "export const X = { a: `\n", "}}}))((", "export * from"):
        assert re.fullmatch(r"2:[0-9a-f]{16}", _arquivo(tmp_path, "q.js", t)), t


# ---- migração v1 -> v2 no rascunho

def _decidir_com_v1(projeto, arq):
    """Mapa feito antes da v2: toda decisão guarda a digital v1 (16 hex, sem prefixo)."""
    d = _preencher(esqueleto.rascunho(projeto, arq, fonte="ast"))
    for c in d["componentes"]:
        c["digital"] = esqueleto.digital_modulo_v1(projeto, c["modulo"])
        assert not c["digital"].startswith("2:")
    esqueleto.caminho_decisoes(arq).write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")


def _digital_de(d, modulo):
    return next(c for c in d["componentes"] if c["modulo"] == modulo)["digital"]


def test_migracao_v1_codigo_igual_nao_vira_revisao_e_passa_a_guardar_v2(projeto):  # noqa: F811
    arq = _arq(projeto)
    _decidir_com_v1(projeto, arq)
    d = esqueleto.rascunho(projeto, arq, fonte="ast")
    assert d["pendentes"]["componentes_revisar"] == []
    assert all(c["digital"].startswith("2:") for c in d["componentes"])
    assert all(c["descricao"] for c in d["componentes"]), "nenhuma descrição decidida se perde"
    # a segunda rodada compara v2 com v2, sem revisão
    assert esqueleto.rascunho(projeto, arq, fonte="ast")["pendentes"]["componentes_revisar"] == []


def test_migracao_v1_com_superficie_v1_mudada_vira_revisao(projeto):  # noqa: F811
    arq = _arq(projeto)
    _decidir_com_v1(projeto, arq)
    regras = projeto / "app" / "regras.py"
    regras.write_text(regras.read_text(encoding="utf-8") + "\n\ndef auditar():\n    return 0\n", encoding="utf-8")
    d = esqueleto.rascunho(projeto, arq, fonte="ast")
    assert d["pendentes"]["componentes_revisar"] == ["app/regras.py"]
    assert _digital_de(d, "app/regras.py").startswith("2:")
    assert next(c for c in d["componentes"] if c["modulo"] == "app/regras.py")["descricao"]


def test_migracao_v1_mudanca_que_so_a_v2_enxerga_espera_a_proxima_rodada(projeto):  # noqa: F811
    arq = _arq(projeto)
    regras = projeto / "app" / "regras.py"
    regras.write_text(regras.read_text(encoding="utf-8") + "\n\nclass Cfg:\n    def ler(self):\n        return 1\n",
                      encoding="utf-8")
    _decidir_com_v1(projeto, arq)
    # atributo de classe novo: invisível para a v1, visível para a v2
    regras.write_text(regras.read_text(encoding="utf-8").replace("class Cfg:\n", "class Cfg:\n    limite = 1\n"),
                      encoding="utf-8")
    guardada = next(c for c in json.loads(esqueleto.caminho_decisoes(arq).read_text(encoding="utf-8"))["componentes"]
                    if c["modulo"] == "app/regras.py")["digital"]
    assert esqueleto.digital_modulo_v1(projeto, "app/regras.py") == guardada, "a v1 não enxerga o atributo novo"
    d1 = esqueleto.rascunho(projeto, arq, fonte="ast")
    assert d1["pendentes"]["componentes_revisar"] == [], "primeira rodada depois da atualização: sem revisão em massa"
    assert _digital_de(d1, "app/regras.py").startswith("2:")
    # outra mudança de superfície na rodada seguinte: agora vira revisão
    regras.write_text(regras.read_text(encoding="utf-8").replace("limite = 1\n", "limite = 1\n    teto = 2\n"),
                      encoding="utf-8")
    d2 = esqueleto.rascunho(projeto, arq, fonte="ast")
    assert d2["pendentes"]["componentes_revisar"] == ["app/regras.py"]
    assert next(c for c in d2["componentes"] if c["modulo"] == "app/regras.py")["descricao"]


def test_v2_mudanca_so_de_valor_ou_corpo_nao_vira_revisao_depois_da_migracao(projeto):  # noqa: F811
    arq = _arq(projeto)
    regras = projeto / "app" / "regras.py"
    regras.write_text(regras.read_text(encoding="utf-8") + "\n\nclass Cfg:\n    limite = 1\n", encoding="utf-8")
    _decidir_com_v1(projeto, arq)
    assert esqueleto.rascunho(projeto, arq, fonte="ast")["pendentes"]["componentes_revisar"] == []
    regras.write_text(regras.read_text(encoding="utf-8").replace("limite = 1", "limite = 99"), encoding="utf-8")
    assert esqueleto.rascunho(projeto, arq, fonte="ast")["pendentes"]["componentes_revisar"] == []


def test_decisoes_antigas_sem_digital_nao_viram_revisao(projeto):  # noqa: F811
    arq = _arq(projeto)
    d = _preencher(esqueleto.rascunho(projeto, arq, fonte="ast"))
    for c in d["componentes"]:
        c.pop("digital", None)
    esqueleto.caminho_decisoes(arq).write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    d2 = esqueleto.rascunho(projeto, arq, fonte="ast")
    assert d2["pendentes"]["componentes_revisar"] == []
    assert all(c.get("digital") for c in d2["componentes"])


# ---------------------------------------------------------------------------------------------------------------
# Go: a primeira linha do comentário de doc de símbolo exportado conta (achado na v5.5.0 do go-chi/chi).
# ---------------------------------------------------------------------------------------------------------------

GO_BASE = ("package middleware\n\nimport \"net/http\"\n\n"
           "// Sunset set Deprecation/Sunset header to response\n// This can be used in a route group\n"
           "func Sunset(at int) func(http.Handler) http.Handler {\n\treturn nil\n}\n\n"
           "// ajuda formata a data.\nfunc ajuda() string {\n\treturn \"\"\n}\n")


def test_go_primeira_linha_do_doc_de_simbolo_exportado_muda_a_digital(tmp_path):
    _muda(tmp_path, "m.go", GO_BASE,
          GO_BASE.replace("// Sunset set Deprecation/Sunset header to response", "// Sunset announces when a route stops working."),
          GO_BASE.replace("// This can be used in a route group\n", "// This can be used in a route group\n//\n// Deprecated: use Other.\n"),
          GO_BASE.replace("func ajuda() string {", "// Limite is the cap.\ntype Limite struct{}\n\nfunc ajuda() string {"))
    metodo = GO_BASE + "\n// Use appends a middleware.\nfunc (mx *Mux) Use(m int) {\n}\n"
    _muda(tmp_path, "m.go", metodo, metodo.replace("// Use appends a middleware.", "// Use replaces the stack."))


def test_go_corpo_segunda_linha_do_doc_e_simbolo_interno_nao_mudam(tmp_path):
    _igual(tmp_path, "m.go", GO_BASE,
           GO_BASE.replace("\treturn nil\n", "\tx := 1\n\t_ = x\n\treturn nil\n"),
           GO_BASE.replace("// This can be used in a route group", "// It can be mounted on one route or on a group"),
           GO_BASE.replace("// ajuda formata a data.", "// ajuda devolve a data no formato HTTP."),
           GO_BASE.replace("func Sunset(at int)", "//go:noinline\nfunc Sunset(at int)"))
    # comentário separado da declaração por linha em branco não é doc dela
    solto = GO_BASE.replace("// This can be used in a route group\nfunc Sunset", "// This can be used in a route group\n\nfunc Sunset")
    _igual(tmp_path, "m.go", solto, solto.replace("// Sunset set Deprecation/Sunset header to response", "// Outra frase solta."))


def test_go_sem_doc_a_v2_e_a_v1_com_prefixo(tmp_path):
    texto = "package m\n\nfunc Soma(a int, b int) int {\n\treturn a + b\n}\n"
    (tmp_path / "m.go").write_text(texto, encoding="utf-8")
    assert esqueleto.digital_modulo(tmp_path, "m.go") == "2:" + esqueleto.digital_modulo_v1(tmp_path, "m.go")
