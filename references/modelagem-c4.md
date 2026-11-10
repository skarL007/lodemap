# Modelagem C4 no Structurizr DSL (resumo da casa)

## Níveis

| Nível | Elemento DSL | O que é | Pergunta |
|---|---|---|---|
| 1. Contexto | `person`, `softwareSystem` | Quem usa e com que sistemas externos conversa | Quem e o quê? |
| 2. Containers | `container` | Processo ou banco que roda sozinho (servidor, app desktop, SPA, banco, fila, modelo servido) | Quais processos e dados? |
| 3. Componentes | `component` | Módulo real do código com uma responsabilidade (um arquivo ou um punhado de arquivos) | Que peças compõem cada processo? |
| 4. Código | (fora do DSL) | Funções e classes | O teste de cobertura liga o nível 3 ao código |

Regra: **um componente por responsabilidade, não por arquivo**. Vários arquivos que fazem uma coisa só entram juntos
no `codigo` ("src/llm/roteador.py, papeis.py"). Um arquivo de 4.000 linhas que faz três coisas pode virar três
componentes com o mesmo caminho e um comentário entre parênteses ("src/server.py (montagem do prompt)").

## Inventário → containers → componentes → relações

1. **Inventário**: liste os módulos (`scripts/inventario.py --importadores`). Para cada um: o que faz (docstring), quem
   importa (vira relação), em que processo roda (vira container).
2. **Containers**: um por processo que sobe sozinho ou por armazenamento com dono (SQLite, Neo4j, pasta de arquivos
   do usuário). Externos (APIs de nuvem) são `softwareSystem` com tag `Externo` ou `Nuvem`.
3. **Componentes por área**: agrupe com `group "Área" { ... }` e a tag `Area<Nome>` (a tag alimenta as visões por
   área com `include "element.tag==AreaX"`). Áreas típicas: núcleo, gateway de modelos, recuperação, memória,
   biblioteca, segurança, domínio, observabilidade, páginas.
4. **Relações**: `a -> b "verbo no presente" "tecnologia" "Tag"`. Tecnologia diz o canal ("Chamada em processo
   (Python)", "HTTP", "Bolt", "SSE", "stdio", "Arquivos"). Tags: o status quando a relação ainda não existe
   (Planejado) ou depende de algo em andamento (EmAndamento); `Gate` quando é guarda que falha fechada.
   Com `!impliedRelationships false`, relação de container para componente só existe se for declarada.
5. **Visões**: Contexto, Containers, uma visão de componentes por área (com os vizinhos de outras áreas incluídos
   por identificador), uma visão "Completo" do container principal e as visões filtradas por status sobre ela.
6. **Fluxos** (`dynamic`): os caminhos que alguém precisa entender em ordem (um turno, uma ingestão, um pedido de
   apagar). Cada passo usa uma relação que **já existe** no modelo. Numa visão dinâmica de container, só entram
   componentes desse container; de outro container, use o container inteiro. O texto do passo **não leva
   número** (`"Calls Mux.ServeHTTP"`, não `"1. Calls Mux.ServeHTTP"`): o explorador numera os passos pela
   ordem, e o número escrito no texto aparece duas vezes.

## Status e tags

| Status (propriedade `status`) | Tag | Cor |
|---|---|---|
| Pronto | `Pronto` | verde #1f7a4d |
| Em andamento | `EmAndamento` | âmbar #b7791f |
| Aguardando | `Aguardando` | roxo #6b46c1 |
| Planejado | `Planejado` | cinza-azulado tracejado |
| Fora do foco | `ForaDoFoco` | cinza, opacidade 70% |

Status é **realidade do código**, não desejo: Pronto = no código, testado e integrado no ramo principal; Em andamento
= código existe mas falta meta, revisão ou merge; Planejado = só no design (sem `codigo`, ou com `ramo`).
Código que o próprio projeto marca como obsoleto e ainda distribui (`// Deprecated:`, `@deprecated`) é
`ForaDoFoco`, com a descrição dizendo o que o substitui. "Testado" quer dizer que existe teste que exercita o
módulo, direto ou por outro; a skill não confere isso, quem marca `Pronto` é o modelador.

Tags de forma: `Dados` (cilindro), `Gate` (hexágono), `Privacidade` (borda amarela), `Modelo` (robô), `WebBrowser`,
`Janela`, `Barramento` (cano), `Externo`/`Nuvem` (borda laranja tracejada).

## Propriedades de estudo

`status`, `area`, `codigo`, `observabilidade` (métricas e eventos emitidos), `metricas` (números citados, texto),
`equipe`, `spec`, `nota`, `ramo` (o código mora em outro ramo), `commit`, `porta`, `comando`, `guia`. O
`enriquecer.groovy` transforma cada uma em perspectiva do Lite e o primeiro caminho de `codigo` em link do GitHub.

## Métricas curadas (`metricas/metricas.json`)

```json
{"id": "latencia-p50", "nome": "1º token, p50", "grupo": "Latência",
 "componentes": ["identDoDSL"], "unidade": "s",
 "meta": {"texto": "≤ 3 s", "valor": 3, "sentido": "<="}, "veredito": "passa",
 "atual": {"valor": 1.92, "rotulo": "tratamento", "data": "2026-11-02",
           "fonte": {"arquivo": "caminho/do/evidencia.json", "ramo": "feat/x", "commit": "abc1234",
                     "campo": "latencia.trat.p50", "agregacao": "soma|contar>0|max (só com *)"}},
 "historico": [{"valor": 36.7, "rotulo": "base", "data": "...", "fonte": {...}}]}
```

Só números e origem. Nunca respostas, textos de documentos ou dados pessoais. O teste confere cada número com
`git show <commit>:<arquivo>`.
