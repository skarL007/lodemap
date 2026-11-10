# Fontes de arestas: CodeGraph e `ast`

Detalhe do que cada fonte de arestas vê e não vê. A regra de uso está no `SKILL.md` ("CodeGraph"); a precisão medida do modo `ast` está em `precisao-ast.md`.

As arestas são **sugestão, não verdade**: num repositório de 188 componentes o índice tinha 84 mil `unresolved_refs` contra 75 mil arestas
resolvidas. Cada par sai com `confianca` (alta = `calls` com 3 arestas ou mais; média = imports ou 2 arestas; baixa =
1 aresta). O modelador confirma no código; nada entra no DSL de forma automática. O recall de relações do
`qualidade.py` só conta pares de confiança alta ou média. No modo `ast`, todo `import` entre componentes conta como
média (um import é um fato do código; antes só valiam 2 arestas e o recall virava "1 de 1" sem dizer nada). O `ast` não
vê `sys.path.insert` + import tardio, globais de JavaScript (`window.Fmt`) nem HTTP: essas relações reais saem como
"sem aresta" na precisão, e isso é esperado (numa medição: 5 de 72, todas reais).

| | CodeGraph (`--fonte codegraph`) | `ast` (`--fonte ast`, reserva) |
|---|---|---|
| Requer | índice feito pelo dono (`.codegraph/codegraph.db`) | nada; só a biblioteca padrão |
| Linguagens | 30+ (Python, JS/TS, Go, Rust, Java...) | Python (`ast`), JS/TS (regex de caminho relativo), Go, Rust, Java, Kotlin, C# e C/C++ (regex, depois de tirar comentários e strings) |
| Vê | chamadas, instanciações, imports e despacho resolvido | só imports (`import`, `use`, `mod`, `using`, `#include "x.h"`, `require`) |
| Tipo da aresta | `calls` e `imports` | `imports` (confiança no máximo média) |
| Limites | referência não resolvida some; índice pode estar velho | não vê chamada dinâmica, HTTP nem registro por decorador; alias de pacote e imports não relativos de JS ficam de fora |
| Inventário | arquivos, símbolos, docstrings e linhas | módulo, classes e funções do topo, docstring |

O modo `ast` lê imports de Python, JS/TS, Go, Rust, Java, Kotlin, C# e C/C++, só com a biblioteca padrão. Go resolve por símbolo: o import de um pacote interno (reconhecido pelo module path do `go.mod`) vira aresta para o arquivo que declara cada `pacote.Nome` usado, e arquivos do mesmo pacote, que se usam sem import, ganham aresta pelo nome de topo (func, type, var, const) que um usa e o outro declara; nome não exportado com ligação local de mesmo nome no arquivo é ignorado, e método não conta porque exigiria tipos (medido no go-chi/chi v5.4.0: 31 arestas em 35 arquivos, 31 conferidas à mão como verdadeiras por quem escreveu a regra; antes eram 6, todas no arquivo errado); Rust usa `mod`, `use crate::`/`self::`/`super::` e os crates do workspace pelo `Cargo.toml`; Java e Kotlin usam o `package` declarado ou a árvore `src/main/java`; C# usa os `namespace` declarados; C/C++ usa `#include "x.h"`. O import que não resolve para um arquivo do repositório é ignorado, nunca inventado. Limites: macros do Rust, `use a::*` sem nome exato, `replace` do Go, reflection e injeção de dependência (JVM, C#), `#include <...>` e `-I` do build não são seguidos. Nesses casos, use `--fonte codegraph` ou modele à mão.

`--fonte auto` (padrão) escolhe o CodeGraph se o índice existir e senão o `ast`. **Registre no `estado.json`** qual
fonte foi usada (`fonteRelacoes`: `codegraph` ou `ast`) e, no caso de `ast`, a sugestão de indexar. A nota do recall
muda de fonte para fonte (o `ast` vê menos pares); compare notas só da mesma fonte.
