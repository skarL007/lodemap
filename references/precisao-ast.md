# Precisão do modo ast da ponte

Medição de 2026-11-08 do modo `ast` de `scripts/codegraph_ponte.py`: as arestas arquivo -> arquivo que ele produz a
partir dos imports (Python, JavaScript e TypeScript, Go, Rust, Java, Kotlin, C# e C/C++). A medição é determinística e
não usa modelo: `scripts/medir_ast.py` roda o extrator e compara o resultado com uma referência.

Todo número abaixo saiu de uma execução real desse script. Onde não há medida, a célula diz "sem repo real" ou "não
analisado".

## O que é medido

O extrator gera uma aresta `(a, b)` quando o arquivo `a` importa algo que está no arquivo `b` do mesmo repositório.
Import de biblioteca externa não gera aresta. As definições:

- **TP**: aresta que o extrator produz e a referência também tem.
- **FP**: aresta que o extrator produz e a referência não tem.
- **FN**: aresta que a referência tem e o extrator não produz.
- **Precisão** = TP / (TP + FP). **Recall** = TP / (TP + FN).

### Camada A: gabarito rotulado à mão

`tests/fixtures/ast_precisao/<linguagem>/` tem um mini-repositório por linguagem e um `gabarito.json` com a lista exata
de arestas que um leitor humano reconhece lendo o código. Os repositórios cobrem os casos difíceis de cada linguagem
(import em comentário, string e raw string, import relativo, import preguiçoso, módulo local com nome de biblioteca
padrão, `mod` em linha no Rust, import explícito que oculta um homônimo do curinga em Java e Kotlin, e assim por
diante). O gabarito também lista `limites`: pares que o extrator erra de propósito e que o texto assume como limite
conhecido (seção "Limites"). Um limite conhecido fica fora da conta e é reportado à parte.

Ressalva importante: as fixtures foram escritas por quem já conhecia o código do extrator. A camada A prova que um erro
corrigido não volta e que os casos listados funcionam. Ela não é uma amostra aleatória de código real, então 1,000 aqui
não significa 1,000 num repositório desconhecido. Quem mede isso é a camada B.

### Camada B: comparação com o índice do CodeGraph

Com `--repo <caminho>`, o script abre `.codegraph/codegraph.db` do repositório em modo somente leitura
(`mode=ro`; nunca roda `codegraph init`, nunca escreve no repositório) e usa como referência as arestas de tipo
`imports` entre arquivos diferentes. Só entram na conta arquivos que as duas fontes enxergam.

A referência é outra ferramenta, não a verdade. Por isso o FP tem dois níveis:

- **FP duro**: o índice não tem nenhuma aresta entre os dois arquivos.
- **FP corroborado**: o índice não chama de `imports`, mas tem `calls`, `instantiates`, `references`, `extends`,
  `implements` ou `decorates` entre os dois. A dependência existe; só o rótulo difere.

Colunas das tabelas: **P imp** = TP / (TP + FP duro + FP corroborado), a precisão contra o que o índice chama de
import. **P ampla** = (TP + FP corroborado) / (TP + FP duro + FP corroborado), que conta a dependência corroborada por
chamada. **R** = TP / (TP + FN).

## Resultado, camada A

Piso do teste (`tests/test_medir_ast.py`): precisão >= 0,95 e recall >= 0,90 em cada linguagem. É o piso proposto, não
um piso rebaixado: o extrator corrigido atinge 1,000 / 1,000 em todas, então o piso tem folga e só falha com
regressão. "Antes" é a ponte do commit 85fc0a6; "depois" é a ponte corrigida.

| Linguagem | Arestas no gabarito | Antes: TP / FP / FN | Antes: P / R | Depois: TP / FP / FN | Depois: P / R | Limites conhecidos (fora da conta) |
|---|---|---|---|---|---|---|
| Python | 18 | 16 / 2 / 2 | 0,889 / 0,889 | 18 / 0 / 0 | 1,000 / 1,000 | 1 FP |
| JavaScript e TypeScript | 22 | 18 / 3 / 4 | 0,857 / 0,818 | 22 / 0 / 0 | 1,000 / 1,000 | 2 FN |
| Go | 12 | 12 / 0 / 0 | 1,000 / 1,000 | 12 / 0 / 0 | 1,000 / 1,000 | 0 |
| Rust | 36 | 36 / 2 / 0 | 0,947 / 1,000 | 36 / 0 / 0 | 1,000 / 1,000 | 0 |
| Java | 7 | 7 / 1 / 0 | 0,875 / 1,000 | 7 / 0 / 0 | 1,000 / 1,000 | 0 |
| Kotlin | 8 | 8 / 0 / 0 | 1,000 / 1,000 | 8 / 0 / 0 | 1,000 / 1,000 | 0 |
| C# | 9 | 9 / 0 / 0 | 1,000 / 1,000 | 9 / 0 / 0 | 1,000 / 1,000 | 0 |
| C e C++ | 14 | 14 / 0 / 0 | 1,000 / 1,000 | 14 / 0 / 0 | 1,000 / 1,000 | 1 FP |

Go, Kotlin, C# e C não tinham erro nas fixtures: nelas o resultado confirma o extrator, não corrige nada. Não
significa que essas linguagens não tenham bugs, só que as fixtures atuais não os encontraram.

## Resultado, camada B

Repositórios locais com índice do CodeGraph usados: cinco repositórios privados do autor,
chamados aqui de R1 a R5 (R1 mistura Rust e Python; R5 é um monorepo). Para Java, Kotlin, C# e C/C++ não havia repositório real
indexado: **sem repo real**. Essas quatro linguagens têm só a camada A.

**Go num repositório público, conferido por leitura (09/11/2026).** No [go-chi/chi](https://github.com/go-chi/chi)
v5.4.0 (35 arquivos de produto, 2 pacotes) não há índice para comparar; as arestas foram conferidas no código, uma
a uma, por dois agentes em leituras separadas. A primeira versão do extrator ligava o arquivo ao pacote importado e
escolhia um arquivo do pacote: 6 arestas, as 6 erradas (todas para `chain.go`). Com a resolução por símbolo
(`alias.Nome` entre pacotes, pelo nome declarado em `package`; nome de topo usado entre arquivos do mesmo pacote):
31 arestas, 31 confirmadas (precisão 1,00 nesta amostra), e 3 relações reais não achadas, de chamada de método e de
uso por interface (31 de 34, recall 0,91). Método não é resolvido porque exige o tipo do receptor.

### Python

| Repositório | Arquivos | Antes: TP / FP duro / FP corrob. / FN | Antes: P imp / P ampla / R | Depois: TP / FP duro / FP corrob. / FN | Depois: P imp / P ampla / R |
|---|---|---|---|---|---|
| R1 | 364 | 274 / 2 / 26 / 131 | 0,907 / 0,993 / 0,677 | 304 / 10 / 27 / 101 | 0,892 / 0,971 / 0,751 |
| R2 | 289 | 215 / 26 / 109 / 24 | 0,614 / 0,926 / 0,900 | 215 / 26 / 109 / 24 | 0,614 / 0,926 / 0,900 |
| R3 | 337 | 588 / 61 / 301 / 137 | 0,619 / 0,936 / 0,811 | 588 / 61 / 301 / 137 | 0,619 / 0,936 / 0,811 |
| R4 | 513 | 1357 / 90 / 69 / 391 | 0,895 / 0,941 / 0,776 | 1307 / 87 / 70 / 441 | 0,893 / 0,941 / 0,748 |
| R5 | 814 | 653 / 19 / 98 / 1349 | 0,848 / 0,975 / 0,326 | 1641 / 193 / 370 / 361 | 0,745 / 0,912 / 0,820 |

### JavaScript e TypeScript

| Repositório | Arquivos | Antes: TP / FP duro / FP corrob. / FN | Antes: P imp / R | Depois: TP / FP duro / FP corrob. / FN | Depois: P imp / R |
|---|---|---|---|---|---|
| R1 | 90 | 109 / 8 / 0 / 18 | 0,932 / 0,858 | 114 / 10 / 0 / 13 | 0,919 / 0,898 |
| R2 | 28 | 15 / 0 / 0 / 0 | 1,000 / 1,000 | 15 / 0 / 0 / 0 | 1,000 / 1,000 |
| R4 | 34 | 40 / 0 / 0 / 0 | 1,000 / 1,000 | 40 / 0 / 0 / 0 | 1,000 / 1,000 |
| R5 | 535 | 1189 / 30 / 4 / 122 | 0,972 / 0,907 | 1189 / 29 / 4 / 122 | 0,973 / 0,907 |

### Rust

| Repositório | Arquivos | Antes: TP / FP duro / FP corrob. / FN | Antes: P imp / P ampla / R | Depois: TP / FP duro / FP corrob. / FN | Depois: P imp / P ampla / R |
|---|---|---|---|---|---|
| R1 | 237 | 213 / 246 / 221 / 84 | 0,313 / 0,638 / 0,717 | 213 / 166 / 217 / 84 | 0,357 / 0,722 / 0,717 |

### Como ler a camada B sem se enganar

Os números da camada B misturam erro do extrator com erro (ou convenção diferente) do índice. Cada um dos casos abaixo
foi conferido lendo o código-fonte do repositório, não só a tabela:

1. **R5 Python: a precisão "caiu" e o recall subiu de 0,326 para 0,820.** O repositório é um monorepo com
   várias raízes de código (`packages/domain/ankirag_domain/`, `packages/infrastructure/ankirag_infra/`,
   `services/api/ankirag_api/`), instaladas de forma editável. Antes, o extrator só resolvia o import dentro da
   própria raiz, e 1310 dos 1349 FN eram pares cujos dois primeiros níveis de pasta diferem (por exemplo
   `evals/adversarial_eval.py` -> `packages/domain/ankirag_domain/checks.py`); os outros 39 tinham os mesmos dois primeiros
   níveis nos dois lados. Os 446 pares novos que a camada B conta como FP
   foram conferidos um a um por texto: todos os 446 têm um `from ankirag_...` ou `import ankirag_...` do módulo
   apontado no arquivo de origem (muitos dentro de função, como `from ankirag_domain.retrieval import ...` em
   `tests/test_concurrency_contract.py`). São arestas verdadeiras que o índice não registra como `imports`. A queda
   de "P imp" de 0,848 para 0,745 é, portanto, falha de cobertura do índice, não do extrator.
2. **R4 Python: o recall caiu de 0,776 para 0,748.** Dos 54 FN novos, 52 são um `import logging`
   da biblioteca padrão que o índice liga ao pacote local `ufo/logging/__init__.py` (o nome do pacote local é igual ao
   da stdlib). O extrator agora trata `import logging` dentro de um pacote como stdlib, que é o comportamento real do
   Python; o índice está errado nesses 52. Os 2 restantes importam também `ufo.logging.setup`, então o texto não
   separa os dois casos e não foram conferidos um a um.
3. **R1 TypeScript: 2 FP duros novos** (`sdk/typescript/src/index.ts` -> `errors.ts` e `types.ts`) vêm de
   `export * from "./errors.js"` e `export type * from "./types.js"`. São re-exportações reais; o índice não as
   registra como import. O ganho do `.js` -> `.ts` trouxe 5 TP novos que antes eram FN.
4. **R1 Rust: P imp 0,357.** Dos 383 pares sem TP (166 FP duros e 217 corroborados), uma busca textual
   encontrou `mod <nome>;` ou `#[path]` apontando para o alvo em 103, e um `use` que cita o alvo em 247; os 33
   restantes não casaram com a busca simples. Três deles foram lidos à mão e são `use` reais:
   `tui/claude.rs` -> `tui/mod.rs` (`use super::data::clean;`), `telemetry/events.rs` -> `telemetry/mod.rs`
   (`use super::TelemetrySnapshot;`) e `doctor.rs` -> `main.rs` (`use crate::{daemon_base_url, daemon_get};`). O
   índice não registra `mod x;` como import, aponta o cruzamento entre crates do workspace para `lib.rs` e deixa de
   registrar vários `use super::`. O que a tabela mostra, portanto, é sobretudo a diferença de convenção, e o recall
   de 0,717 (84 FN) **não foi analisado**.
5. **Python do R1, R2, R3 e os FN restantes do R5** (101, 24, 137 e 361): não foram
   analisados um a um. Não há afirmação sobre a causa.

Dois registros da própria camada B sobre o índice (comportamentos observados, não suposições): ele liga `import
logging` da stdlib ao `logging/__init__.py` local, e liga `from pkg.sub import x` também ao `__init__.py` do pacote pai.

## Bugs corrigidos

Cada correção tem um teste `test_bug_*` em `tests/test_medir_ast.py` que falha na ponte original e passa na corrigida
(conferido rodando o mesmo arquivo de testes contra `85fc0a6`: 14 testes falham, entre eles os 4 pisos da camada A de
Java, JavaScript, Python e Rust).

| Bug | Onde (`scripts/codegraph_ponte.py`) | Efeito medido |
|---|---|---|
| JavaScript: `import`/`require` dentro de comentário, string ou template literal virava aresta | `_limpar_js` e `arestas_ast_js` | camada A: 3 FP a menos em JS |
| TypeScript ESM: `./x.js` não achava `x.ts`/`x.tsx` (nem `.mjs` -> `.mts`, `.cjs` -> `.cts`) | `_JS_PARA_TS` e `_resolver_js` | camada A: 4 FN a menos; R1 TS: 5 FN a menos |
| Java e Kotlin: `import c.Lista;` explícito não ocultava o `Lista` de um `import b.*;` | `_JVM_IMPORT` (grupo do alias) e `_arestas_jvm` | camada A: 1 FP a menos em Java |
| Python: `import logging` dentro de um pacote com `logging.py` ou `logging/` local pegava o homônimo em vez da stdlib | `_resolver_py` | camada A: 2 FP a menos |
| Python: pacote de uma raiz importado de outra (monorepo, instalação editável) não resolvia | `_resolver_py` e `_raizes_pacote_py` | camada A: 2 FN a menos; R5: recall 0,326 -> 0,820 |
| Rust: `use super::*` dentro de `mod tests { }` apontava para o `mod.rs` do pai em vez do próprio arquivo | `_prof_modulos_em_linha` e `resolver` (parâmetro `em_linha`) | camada A: 2 FP a menos; R1: 80 FP duros e 4 corroborados a menos |
| `ast.parse` imprimia `SyntaxWarning` de arquivos analisados (`"\l"`) no stderr | `arestas_ast_python` | sem ruído no stderr da ferramenta |

O ajuste do Python para monorepo só vale para pacote de topo **único** no repositório e fora da stdlib: um nome de
topo que existe em duas pastas (`dup` em `libs/a` e `libs/b`) continua sem aresta, e `import json` nunca vai para um
`json/` de outra raiz. É melhor perder uma aresta do que inventar.

## Limites

O modo `ast` lê o texto e a sintaxe dos imports; não executa nem resolve o ambiente do projeto. O que ele não enxerga:

- **Import dinâmico**: `importlib.import_module("x")`, `__import__("x")`, `require(variavel)` e `import(variavel)`.
- **Alias de caminho de TypeScript e bundler**: `baseUrl` e `paths` do `tsconfig.json`, alias `@/`. O extrator só segue
  caminho relativo (`./x`, `../x`). São os 2 FN conhecidos da fixture de JavaScript.
- **Macros e pré-processador**: um `#include` dentro de `#if 0` vira aresta (o extrator não avalia o pré-processador),
  e include gerado por macro não aparece. É o FP conhecido da fixture de C.
- **Reflection e injeção de dependência**: a dependência declarada em configuração (Spring, Guice, `Class.forName`,
  contêiner de DI em C#) não tem import no texto, então não há aresta.
- **Pacote de namespace em Python**: numa pasta sem `__init__.py` o extrator assume que ela está em `sys.path`; um
  módulo local com nome de biblioteca padrão ali (`pkg_ns/json.py`) vence a stdlib. É o FP conhecido da fixture de Python.
- **Literal de expressão regular em JavaScript**: o limpador de comentário e string não distingue uma `/regex/` de uma
  divisão; uma regex com aspas dentro pode confundir a limpeza do trecho seguinte. Não há caso medido.
- **Pacote instalado, não do repositório**: quando o pacote só existe em `site-packages` o extrator corretamente não
  produz aresta, e o índice também não deveria.
- **Cobertura da própria medição**: Java, Kotlin, C# e C/C++ têm só a camada A, escrita pelo autor do extrator. Rust
  e Go têm um único repositório real cada; o de Go foi conferido por leitura, sem índice.
- **Go, método e interface**: `x.Metodo()` e o uso de um tipo por uma interface de outro arquivo não viram aresta.

## Reproduzir

Na raiz do repositório lodemap, só com a biblioteca padrão do Python:

```
python scripts/medir_ast.py
python scripts/medir_ast.py --repo <caminho de R1> --repo <caminho de R5> --saida medida.json
git show 85fc0a6:scripts/codegraph_ponte.py > ponte_antes.py
python scripts/medir_ast.py --ponte ponte_antes.py
python -m pytest tests/test_medir_ast.py -q
```

O primeiro comando imprime a camada A por linguagem, com a lista de erros. O segundo acrescenta a camada B de cada
`--repo` (exige `.codegraph/codegraph.db` já existente; o script não cria índice) e grava o JSON. O terceiro e o quarto
medem a ponte original para a coluna "antes". Os valores da camada B dependem do estado dos repositórios e dos índices
na data da medição (2026-11-08) e podem mudar quando o código ou o índice mudarem.
