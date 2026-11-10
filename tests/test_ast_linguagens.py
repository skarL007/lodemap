"""Modo ast da ponte (scripts/codegraph_ponte.py) para Go, Rust, Java, Kotlin, C# e C/C++.

Cada teste monta um mini-repositório em tmp_path e confere as arestas EXATAS arquivo -> arquivo. Todos têm um import
externo (que não pode virar aresta) e um import falso dentro de comentário (que também não)."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from lodemap import RAIZ

sys.path.insert(0, str(RAIZ / "scripts"))
import codegraph_ponte as cp  # noqa: E402
import esqueleto  # noqa: E402


def _escrever(raiz: Path, arquivos: dict[str, str]) -> Path:
    for rel, texto in arquivos.items():
        p = raiz / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(texto, encoding="utf-8", newline="\n")
    return raiz


def _arestas(raiz: Path) -> dict[tuple[str, str], int]:
    return {par: dict(c)["imports"] for par, c in cp.arestas_ast(raiz).items()}


def test_go_resolve_module_path_e_ignora_externo_e_comentario(tmp_path):
    r = _escrever(tmp_path, {
        "go.mod": "module example.com/app\n\ngo 1.22\n",
        "main.go": ('package main\n\nimport (\n\t"fmt"\n\tu "example.com/app/internal/util"\n\t"github.com/x/y"\n)\n\n'
                    '// import "example.com/app/internal/store"\n/* import "example.com/app/internal/store" */\n'
                    'var texto = `\nimport "example.com/app/internal/store"\n`\n\nfunc main() { fmt.Println(u.Ola(), y.Z) }\n'),
        "internal/util/util.go": 'package util\n\nimport "example.com/app/internal/store"\n\nfunc Ola() string { return store.Nome }\n',
        "internal/store/store.go": 'package store\n\nconst Nome = "x"\n',
    })
    assert _arestas(r) == {("main.go", "internal/util/util.go"): 1,
                           ("internal/util/util.go", "internal/store/store.go"): 1}


def test_go_import_sem_simbolo_resolvido_cai_no_representante_e_simbolo_resolvido_vai_para_quem_declara(tmp_path):
    r = _escrever(tmp_path, {
        "go.mod": "module m\n",
        "a/a.go": 'package a\n\nimport "m/b"\n\nfunc A() { b.Z() }\n',
        "a/sem_uso.go": 'package a\n\nimport "m/b"\n',
        "a/so_teste.go": 'package a\n\nimport "m/b"\n\nfunc S() { b.SoNoTeste() }\n',
        "b/zzz.go": "package b\n\nfunc Z() {}\n",
        "b/b.go": "package b\n\nfunc B() {}\n",
        "b/b_test.go": 'package b\n\nimport "m/a"\n\nfunc SoNoTeste() { a.A() }\n',
    })
    assert _arestas(r) == {
        ("a/a.go", "b/zzz.go"): 1,          # b.Z é declarado em zzz.go: vai para ele, não para o representante
        ("a/sem_uso.go", "b/b.go"): 1,      # nada resolve: representante (arquivo com o nome da pasta)
        ("a/so_teste.go", "b/b.go"): 1,     # o símbolo só existe num _test.go, que nunca recebe aresta: representante
        ("b/b_test.go", "a/a.go"): 1,       # o teste importa a e usa a.A (origem válida); ninguém aponta para um _test.go
    }


def test_go_import_resolve_pelo_simbolo_com_alias_e_pelo_nome_do_pacote_nao_da_pasta(tmp_path):
    r = _escrever(tmp_path, {
        "go.mod": "module github.com/go-chi/chi/v5\n",
        "chi.go": "package chi\n\nfunc Chain() {}\n",
        "context.go": "package chi\n\nfunc RouteContext() {}\n",
        "mux.go": "package chi\n\nfunc NewRouter() {}\n",
        "middleware/m.go": ('package middleware\n\nimport (\n\t"net/http"\n\t"github.com/go-chi/chi/v5"\n)\n\n'
                            "func M() { _ = chi.RouteContext; chi.NewRouter(); http.Get() }\n"),
        "loja/a.go": "package store\n\nfunc Abre() {}\n",
        "loja/b.go": "package store\n\ntype Conn struct{}\n",
        "loja/z.go": "package store\n\nfunc Outra() {}\n",
        "app/main.go": ('package main\n\nimport s "github.com/go-chi/chi/v5/loja"\n\n'
                        "func main() { s.Abre(); var _ s.Conn }\n"),
        "app/errado.go": ('package main\n\nimport "github.com/go-chi/chi/v5/loja"\n\n'
                          "func errado() { loja.Abre() }\n"),      # o qualificador é `store`, não `loja`: nada resolve
    })
    assert _arestas(r) == {
        ("middleware/m.go", "context.go"): 1,
        ("middleware/m.go", "mux.go"): 1,
        ("app/main.go", "loja/a.go"): 1,
        ("app/main.go", "loja/b.go"): 1,
        ("app/errado.go", "loja/a.go"): 1,  # sem alias e com qualificador que não é o do pacote: representante (primeiro)
    }


def test_go_import_com_ponto_underscore_ou_so_metodo_mantem_o_representante(tmp_path):
    r = _escrever(tmp_path, {
        "go.mod": "module m\n",
        "u/u.go": "package u\n\nfunc Faz() {}\n\nfunc (T) Metodo() {}\n",
        "u/outro.go": "package u\n\ntype T struct{}\n",
        "ponto.go": 'package main\n\nimport . "m/u"\n\nfunc ponto() { Faz() }\n',
        "sublinhado.go": 'package main\n\nimport _ "m/u"\n',
        "so_metodo.go": 'package main\n\nimport "m/u"\n\nfunc soMetodo(t any) { u.Metodo() }\n',
        "misto.go": 'package main\n\nimport "m/u"\n\nfunc misto(t u.T) { u.Metodo() }\n',
    })
    assert _arestas(r) == {
        ("ponto.go", "u/u.go"): 1,          # import `.`: não há qualificador, fica o representante (u/u.go)
        ("sublinhado.go", "u/u.go"): 1,     # import `_`: idem
        ("so_metodo.go", "u/u.go"): 1,      # u.Metodo não é declaração de topo: representante
        ("misto.go", "u/outro.go"): 1,      # u.T resolve (outro.go) e basta: sem aresta extra para o representante
    }


def _go_mesmo_pacote(tmp_path, decl: str, uso: str, extra: dict[str, str] | None = None) -> dict:
    return _arestas(_escrever(tmp_path, {
        "p/d.go": "package p\n\n" + decl + "\n",
        "p/u.go": "package p\n\nfunc usa() {\n\t" + uso + "\n}\n",
        **(extra or {}),
    }))


_LIGA = {("p/u.go", "p/d.go"): 1}


@pytest.mark.parametrize("decl, uso", [
    ("func Faz() {}", "Faz()"),
    ("func Faz[T any](x T) {}", "Faz[int](1)"),
    ("type Tipo struct{}", "var _ Tipo"),
    ("var Global = 1", "_ = Global"),
    ("var Alfa, Beta = 1, 2", "_ = Beta"),
    ("const Max = 3", "_ = Max"),
    ("type (\n\tAlfa struct {\n\t\tCampo int\n\t}\n\tBeta = int\n)", "var _ Beta"),
    ("type (\n\tAlfa struct {\n\t\tCampo int\n\t}\n\tBeta = int\n)", "var _ Alfa"),
    ("var (\n\tV1, V2 = 1, 2\n\tV3    int\n)", "_ = V2"),
    ("var (\n\tV1, V2 = 1, 2\n\tV3    int\n)", "_ = V3"),
    ("const (\n\tC1 = iota\n\tC2\n)", "_ = C2"),
    ("func (t Tipo) Metodo() {}\n\ntype Tipo struct{}", "var _ Tipo"),
], ids=["func", "func-generica", "type", "var", "var-lista", "const", "bloco-type-2o", "bloco-type-1o", "bloco-var-lista",
        "bloco-var-sem-valor", "bloco-const", "metodo-nao-atrapalha-type"])
def test_go_mesmo_pacote_declaracao_de_topo_liga_arquivos_sem_import_nem_go_mod(tmp_path, decl, uso):
    assert _go_mesmo_pacote(tmp_path, decl, uso) == _LIGA


@pytest.mark.parametrize("decl, uso", [
    ("func (t Tipo) Metodo() {}", "Metodo()"),                              # método não declara nada no topo
    ("func Faz() {}", "x.Faz()"),                                           # seletor: método/campo/pacote de fora
    ("func Faz() {}", "x.\n\t\tFaz()"),                                     # seletor com quebra de linha
    ("type (\n\tAlfa struct {\n\t\tCampo int\n\t}\n)", "_ = Campo"),       # campo de struct aninhado em type ( ... )
    ("type (\n\tAlfa interface {\n\t\tFaz()\n\t}\n)", "Faz()"),            # método de interface aninhado
    ("var (\n\tV = f(\n\t\tOutro,\n\t)\n)", "_ = Outro"),                  # argumento multilinha não declara
    ("type error2 struct{}", "_ = error(nil); _ = errors.New; _ = error"),  # builtin e vizinhos não viram lixo
    ("func (t Tipo) Metodo() {}\n\nvar Metodo2 = 1", "_ = Metodo"),
    ("func init() {}", "init()"),                                          # init não é referenciável
], ids=["metodo", "seletor", "seletor-quebra", "campo-aninhado", "interface-aninhada", "arg-multilinha", "error2", "prefixo",
        "init"])
def test_go_mesmo_pacote_nao_declara_ou_nao_conta_nao_gera_aresta(tmp_path, decl, uso):
    assert _go_mesmo_pacote(tmp_path, decl, uso) == {}


@pytest.mark.parametrize("uso", [
    "conta := 1; _ = conta",
    "a, conta := 1, 2; _, _ = a, conta",
    "var conta int; _ = conta",
    "for _, conta := range []int{} { _ = conta }",
    "_ = struct{ conta int }{conta: 1}",
    "_ = func(conta int) int { return conta }",
    "_ = func() (conta int) { return conta }",
    "_ = func(x, conta int) {}",
], ids=["curta", "curta-lista", "var", "for", "campo-e-chave", "parametro", "resultado-nomeado", "parametro-agrupado"])
def test_go_mesmo_pacote_nome_nao_exportado_com_ligacao_local_e_ignorado(tmp_path, uso):
    assert _go_mesmo_pacote(tmp_path, "func conta() int { return 0 }", uso) == {}


def test_go_mesmo_pacote_nao_exportado_sem_ligacao_local_liga_e_exportado_nao_e_poupado(tmp_path):
    assert _go_mesmo_pacote(tmp_path, "func conta() int { return 0 }", "_ = conta()") == _LIGA
    # exportado: não há a poda das ligações locais
    assert _go_mesmo_pacote(tmp_path / "x", "func Conta() int { return 0 }", "Conta := 1; _ = Conta") == _LIGA


def test_go_mesmo_pacote_campo_declarado_em_struct_de_varias_linhas_nao_e_uso(tmp_path):
    extra = {"p/u.go": "package p\n\ntype S struct {\n\tconta int\n}\n"}
    assert _go_mesmo_pacote(tmp_path, "func conta() int { return 0 }", "", extra) == {}


@pytest.mark.parametrize("corpo", [
    "type I interface {\n\tFaz()\n}\n",                                    # nome de método numa interface
    "type I interface{ Faz(x int) error }\n",                              # idem, numa linha
    "type S struct {\n\tFaz int\n}\n",                                    # campo exportado de struct
    "type S struct {\n\tA, Faz int\n}\n",                                 # lista de campos
    "type T int\n\nfunc (t T) Faz() {}\n",                                # nome de método depois do receptor
    "var V = struct{ Faz int }{Faz: 1}\n",                                # campo e chave de literal composto
    "var V = []T{\n\t{\n\t\tFaz: 1,\n\t},\n}\n",                          # chave em linha própria
], ids=["interface", "interface-1-linha", "campo", "campo-lista", "metodo", "literal", "literal-multilinha"])
def test_go_mesmo_pacote_rotulo_de_metodo_campo_ou_chave_nao_e_uso_do_simbolo_de_outro_arquivo(tmp_path, corpo):
    assert _go_mesmo_pacote(tmp_path, "func Faz() {}", "", {"p/u.go": "package p\n\n" + corpo}) == {}


@pytest.mark.parametrize("corpo", [
    "type I interface {\n\tFaz\n}\n",                                      # tipo embutido na interface: é uso
    "type S struct {\n\tFaz\n}\n",                                        # tipo embutido na struct: é uso
    "type S struct {\n\tA Faz\n}\n",                                      # o TIPO do campo é uso, o nome não
    "type I interface {\n\tM(Faz)\n}\n",                                 # argumento do método de interface
    "var V = map[string]int{\n\tk: Faz,\n}\n",                           # valor da chave é uso
    "func usa(x int) {\n\tswitch x {\n\tcase Faz:\n\t}\n}\n",           # `case Faz:` não é chave de literal
], ids=["interface-embutida", "struct-embutida", "tipo-do-campo", "argumento", "valor", "case"])
def test_go_mesmo_pacote_uso_real_perto_de_rotulo_continua_ligando(tmp_path, corpo):
    decl = "const Faz = 1" if "case" in corpo or "map" in corpo else "type Faz struct{}"
    assert _go_mesmo_pacote(tmp_path, decl, "", {"p/u.go": "package p\n\n" + corpo}) == _LIGA


def test_go_mesmo_pacote_so_na_mesma_pasta_e_mesmo_package_e_nunca_com_test_go(tmp_path):
    r = _escrever(tmp_path, {
        "p/a.go": "package p\n\nfunc Alfa() { Beta(); Fora(); DeTeste(); Duplo(); Z() }\n",
        "p/b.go": "package p\n\nfunc Beta() { Alfa() }\n\nfunc Duplo() {}\n",
        "p/duplo2.go": "package p\n\nfunc Duplo() {}\n\nfunc Fora2() { Duplo() }\n",  # declara Duplo: não liga a b.go
        "p/z.go": "package p\n\nfunc Z() {}\n",                                         # um caractere nunca conta
        "p/ignorado.go": "//go:build ignore\n\npackage main\n\nfunc Fora() { Alfa() }\n",   # outro package na mesma pasta
        "q/q.go": "package p\n\nfunc Fora() {}\n",                                       # outra pasta, mesmo package
        "p/x_test.go": "package p\n\nfunc DeTeste() { Alfa() }\n",
    })
    assert _arestas(r) == {("p/a.go", "p/b.go"): 1, ("p/a.go", "p/duplo2.go"): 1, ("p/b.go", "p/a.go"): 1}


def test_go_mesmo_pacote_a_clausula_package_nao_e_uso(tmp_path):
    r = _escrever(tmp_path, {
        "go.mod": "module m\n",
        "app/main.go": "package main\n\nfunc main() {}\n",
        "app/outro.go": "package main\n\nfunc outro() {}\n",  # `main` em `package main` não é a chamada da função main
    })
    assert _arestas(r) == {}


def test_go_sem_go_mod_nao_inventa_aresta_de_import_mas_mantem_a_do_mesmo_pacote(tmp_path):
    r = _escrever(tmp_path, {
        "a/a.go": 'package a\n\nimport "m/b"\n\nfunc A() { b.B(); Ajuda() }\n',
        "a/ajuda.go": "package a\n\nfunc Ajuda() {}\n",
        "b/b.go": "package b\n\nfunc B() {}\n",
    })
    assert _arestas(r) == {("a/a.go", "a/ajuda.go"): 1}


def test_go_sem_go_mod_nao_inventa_aresta(tmp_path):
    r = _escrever(tmp_path, {"a/a.go": 'package a\n\nimport "m/b"\n', "b/b.go": "package b\n"})
    assert _arestas(r) == {}


def test_rust_use_crate_super_self_e_mod(tmp_path):
    r = _escrever(tmp_path, {
        "Cargo.toml": '[package]\nname = "demo"\nversion = "0.1.0"\n',
        "src/main.rs": ('mod config;\nmod net;\n\nuse crate::net::client::Cliente;\nuse std::fs;\nuse serde::Serialize;\n\n'
                        'fn main() { let _ = Cliente; }\n'),
        "src/config.rs": '// use crate::net::client;\n/* mod net; */\npub struct Config;\nconst S: &str = "mod net;";\n',
        "src/net/mod.rs": "pub mod client;\n\npub type Resultado = u8;\n",
        "src/net/client.rs": "use crate::config::{self, Config};\nuse super::Resultado;\nuse std::io::{Read, Write};\n\npub struct Cliente;\n",
    })
    assert _arestas(r) == {
        ("src/main.rs", "src/config.rs"): 1,
        ("src/main.rs", "src/net/mod.rs"): 1,
        ("src/main.rs", "src/net/client.rs"): 1,
        ("src/net/mod.rs", "src/net/client.rs"): 1,
        ("src/net/client.rs", "src/config.rs"): 1,
        ("src/net/client.rs", "src/net/mod.rs"): 1,
    }


def test_rust_workspace_liga_crate_irmao_e_ignora_target(tmp_path):
    r = _escrever(tmp_path, {
        "Cargo.toml": '[workspace]\nmembers = ["nucleo", "app"]\n',
        "nucleo/Cargo.toml": '[package]\nname = "exemplo-nucleo"\nversion = "0.1.0"\n',
        "nucleo/src/lib.rs": "pub mod regras;\n",
        "nucleo/src/regras.rs": "pub fn r() {}\n",
        "app/Cargo.toml": '[package]\nname = "app"\nversion = "0.1.0"\n',
        "app/src/main.rs": "use exemplo_nucleo::regras::r;\nfn main() { r() }\n",
        "app/target/debug/build/x/out.rs": "use crate::nada;\n",
    })
    assert _arestas(r) == {("nucleo/src/lib.rs", "nucleo/src/regras.rs"): 1,
                           ("app/src/main.rs", "nucleo/src/regras.rs"): 1}


def test_java_resolve_pacote_wildcard_so_pelo_que_o_codigo_usa(tmp_path):
    base = "src/main/java/com/acme"
    r = _escrever(tmp_path, {
        f"{base}/app/Main.java": ("package com.acme.app;\n\nimport com.acme.core.Servico;\nimport com.acme.util.*;\n"
                                  "import java.util.List;\n// import com.acme.core.Fantasma;\n\n"
                                  "public class Main { List<String> l; void run() { Ajuda.ok(); new Servico(); } }\n"),
        f"{base}/core/Servico.java": ("package com.acme.core;\n\nimport com.acme.util.Ajuda;\n\n"
                                      "public class Servico { void f() { Ajuda.ok(); } }\n"),
        f"{base}/core/Fantasma.java": "package com.acme.core;\n\npublic class Fantasma {}\n",
        f"{base}/util/Ajuda.java": "package com.acme.util;\n\npublic class Ajuda { public static void ok() {} }\n",
        f"{base}/util/Outro.java": "package com.acme.util;\n\npublic class Outro {}\n",
    })
    assert _arestas(r) == {
        (f"{base}/app/Main.java", f"{base}/core/Servico.java"): 1,
        (f"{base}/app/Main.java", f"{base}/util/Ajuda.java"): 1,
        (f"{base}/core/Servico.java", f"{base}/util/Ajuda.java"): 1,
    }


def test_kotlin_import_de_funcao_do_topo_comentario_aninhado_e_externo(tmp_path):
    r = _escrever(tmp_path, {
        "src/main/kotlin/app/Main.kt": ("package app\n\nimport core.Repo\nimport core.helpers\nimport kotlin.io.println\n"
                                        "/* fora /* import core.Fantasma */ import core.Fantasma */\n\n"
                                        "fun main() { println(Repo().x + helpers()) }\n"),
        "src/main/kotlin/core/Repo.kt": "package core\n\nclass Repo { val x = 1 }\n",
        "src/main/kotlin/core/Util.kt": "package core\n\nfun helpers() = 2\n",
        "src/main/kotlin/core/Fantasma.kt": "package core\n\nclass Fantasma\n",
    })
    assert _arestas(r) == {
        ("src/main/kotlin/app/Main.kt", "src/main/kotlin/core/Repo.kt"): 1,
        ("src/main/kotlin/app/Main.kt", "src/main/kotlin/core/Util.kt"): 1,
    }


def test_csharp_using_resolvido_pelos_namespaces_declarados(tmp_path):
    r = _escrever(tmp_path, {
        "Program.cs": ("using System;\nusing Acme.Servicos;\nusing Acme.Modelos;\n/*\nusing Acme.Fantasma;\nFantasma\n*/\n"
                       "namespace Acme.App\n{\n    class Program { void Run() { new Servico(); } }\n}\n"),
        "Servicos/Servico.cs": ("namespace Acme.Servicos\n{\n    using Acme.Modelos;\n\n"
                                "    public class Servico { Cliente c; }\n}\n"),
        "Modelos/Cliente.cs": "namespace Acme.Modelos;\n\npublic record Cliente(string Nome);\n",
        "Modelos/Outro.cs": "namespace Acme.Modelos;\n\nclass Outro {}\n",
        "Fantasma.cs": "namespace Acme.Fantasma;\n\nclass Fantasma {}\n",
    })
    assert _arestas(r) == {("Program.cs", "Servicos/Servico.cs"): 1,
                           ("Servicos/Servico.cs", "Modelos/Cliente.cs"): 1}


def test_c_e_cpp_include_com_aspas_resolve_pasta_ancestral_e_sufixo_unico(tmp_path):
    r = _escrever(tmp_path, {
        "src/main.c": ('#include <stdio.h>\n#include "util.h"\n#include "core/model.h"\n#include "inexistente.h"\n'
                       '/* #include "fantasma.h" */\n// #include "fantasma.h"\nint main(void) { return 0; }\n'),
        "src/util.h": "int u(void);\n",
        "src/util.c": '#include "util.h"\n#include "shared.h"\n',
        "src/core/model.h": '#pragma once\n#include "../util.h"\n',
        "src/app.cpp": '#include "util.h"\n',
        "src/fantasma.h": "int f(void);\n",
        "include/shared.h": "int s(void);\n",
    })
    assert _arestas(r) == {
        ("src/main.c", "src/util.h"): 1,
        ("src/main.c", "src/core/model.h"): 1,
        ("src/util.c", "src/util.h"): 1,
        ("src/util.c", "include/shared.h"): 1,
        ("src/core/model.h", "src/util.h"): 1,
        ("src/app.cpp", "src/util.h"): 1,
    }


def test_c_include_ambiguo_nao_vira_aresta(tmp_path):
    r = _escrever(tmp_path, {
        "src/main.c": '#include "comum.h"\n',
        "a/comum.h": "\n",
        "b/comum.h": "\n",
    })
    assert _arestas(r) == {}


def test_inventario_ast_enxerga_as_linguagens_novas(tmp_path):
    r = _escrever(tmp_path, {
        "go.mod": "module m\n",
        "a/a.go": 'package a\n\n// Pacote a faz tudo do pacote a.\nfunc Faz() {}\n',
        "src/main.rs": "pub fn principal() {}\n",
        "k/Main.kt": "package k\n\nclass Main\n",
    })
    por = {i["caminho"]: i for i in cp.inventario_ast(r)}
    assert por["a/a.go"]["linguagem"] == "go" and por["a/a.go"]["simbolos"][0]["nome"] == "Faz"
    assert por["a/a.go"]["docstringModulo"] == "Pacote a faz tudo do pacote a."
    assert por["src/main.rs"]["simbolos"][0] == {"nome": "principal", "tipo": "function", "linha": 1}
    assert por["k/Main.kt"]["linguagem"] == "kotlin" and por["k/Main.kt"]["simbolos"][0]["nome"] == "Main"


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "-C", str(repo), *args],
                   check=True, capture_output=True)


def test_esqueleto_rascunho_fonte_ast_em_repositorio_go_sugere_as_relacoes_certas(tmp_path):
    r = _escrever(tmp_path / "amostra", {
        "go.mod": "module example.com/amostra\n\ngo 1.22\n",
        "cmd/app/main.go": ('package main\n\nimport (\n\t"fmt"\n\t"example.com/amostra/internal/web"\n)\n\n'
                            "func main() { fmt.Println(web.Rota()) }\n"),
        "internal/web/web.go": '// Rotas HTTP da amostra.\npackage web\n\nimport "example.com/amostra/internal/store"\n\n'
                               "func Rota() string { return store.Ler() + Sufixo }\n",
        "internal/web/sufixo.go": 'package web\n\nconst Sufixo = "!"\n',  # mesmo pacote, sem import: aresta, mas não relação
        "internal/store/store.go": "package store\n\nconst Raiz = \"/\"\n",  # representante do pacote; ninguém usa seus símbolos
        "internal/store/leitor.go": 'package store\n\nimport "example.com/amostra/internal/util"\n\n'
                                    "func Ler() string { return util.Limpa(\"x\") }\n",
        "internal/util/util.go": "package util\n\nfunc Limpa(s string) string { return s }\n",
    })
    _git(r, "init", "-q")
    _git(r, "add", "-A")
    _git(r, "commit", "-q", "-m", "inicio")
    novo = subprocess.run([sys.executable, str(RAIZ / "scripts" / "novo_mapa.py"), "--repo", str(r), "--projeto", "Amostra",
                           "--raiz-codigo", "internal", "--modulos", "cmd/*/,internal/*/"],
                          capture_output=True, text=True, encoding="utf-8")
    assert novo.returncode == 0, novo.stdout + novo.stderr
    arq = r / "docs" / "architecture" / "structurizr"
    assert json.loads((arq / "lodemap.json").read_text(encoding="utf-8"))["modulos"] == ["cmd/*/", "internal/*/"]
    # por arquivo: o símbolo decide o destino (Ler está em leitor.go, não no representante store.go) e o mesmo pacote liga
    assert {par: n for par, n in _arestas(r).items() if par[0].endswith(".go")} == {
        ("cmd/app/main.go", "internal/web/web.go"): 1,
        ("internal/web/web.go", "internal/store/leitor.go"): 1,
        ("internal/web/web.go", "internal/web/sufixo.go"): 1,
        ("internal/store/leitor.go", "internal/util/util.go"): 1}
    d = esqueleto.rascunho(r, arq, fonte="ast")
    assert {c["modulo"] for c in d["componentes"]} == {"cmd/app/", "internal/web/", "internal/store/", "internal/util/"}
    assert {(x["de"], x["para"]) for x in d["relacoes"]} == {("cmd/app/", "internal/web/"),
                                                              ("internal/web/", "internal/store/"),
                                                              ("internal/store/", "internal/util/")}
    web = next(c for c in d["componentes"] if c["modulo"] == "internal/web/")
    assert web["linguagem"] == "go" and web["dica"] == "Rotas HTTP da amostra."
