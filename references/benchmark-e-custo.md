# Benchmark e custo medido da skill lodemap

Medição de 02/11/2026, na primeira geração completa, feita num projeto privado, chamado aqui de projeto A (Python,
Electron e web). Os números vêm do registro do agente (`usage` de cada turno) e dos testes e verificadores da
própria skill.

Três projetos privados aparecem neste arquivo como projeto A, projeto B e projeto C. O código deles não é público,
então quem lê não consegue refazer as medições feitas neles. As que qualquer pessoa pode refazer estão nas seções
"Demo pública" e "Validação (fase 3)", em repositórios abertos.

## Por que é promissor

1. **A documentação deixa de envelhecer.** O teste de cobertura falha quando um módulo fica fora do mapa. No projeto A, o
   mapa feito à mão já cobria só 54 de 98 módulos (55%) antes da skill, e depois dela passou a 98 de 98. Em vez de
   "documentação que alguém lembra de atualizar", vira uma checagem que trava o merge.
2. **Os números têm origem.** Cada métrica aponta para o arquivo e o commit de onde saiu, e um teste confere o valor
   com `git show`. Nenhum número do painel é digitado à mão. No projeto A foram 10 métricas, entre elas a latência
   (1º token de 36,7 s para 1,92 s), a VRAM e o recall.
3. **Fica barato manter.** Depois da primeira geração, cada checkpoint roda em modo incremental. O `lodemap_diff.py`
   apontou só o componente afetado pela mudança, o gancho do git voltou em 0,5 s e, sem mudança estrutural, o
   trabalho é de scripts, sem raciocínio de modelo. A stack não usa Opus: Haiku lê e confere, e Sonnet decide e
   gera.
4. **Um modelo, várias saídas.** O mesmo DSL alimenta o Structurizr Lite (C4 oficial), o explorador interativo
   (impacto de mudança, fluxos animados, métricas por componente), o site estático, o leitor e os documentos
   derivados. Muda-se num lugar e o resto se regenera.
5. **Serve para qualquer projeto.** Fora do projeto A, a skill foi provada num projeto de exemplo (12 testes e o
   verificador verdes) e num segundo projeto real, o projeto B (Python, JavaScript, PowerShell e Bash em
   várias pastas, sem `app/` nem `src/`): 63 módulos em 63 cobertos, nota de qualidade 95,2 e 25 testes verdes em
   cerca de 28 minutos de um agente só (seção "Prova no 2º projeto real (projeto B)"). O pacote instala em um comando, com
   backup do que já existir.

**Limites honestos:**
- o custo da stack de seis agentes continua estimado: a prova no projeto B foi feita por um agente Sonnet só, que fez os
  papéis de modelador, métricas, gerador e verificador, sem subagentes; o custo do roteamento Haiku e Sonnet entre
  agentes não foi medido;
- a nota de qualidade mede estrutura (descrição, caminho, relações, visões, cobertura), não se a arquitetura está
  certa: 95,2 no projeto B não quer dizer "melhor que o projeto A", só que o modelo passa no gate. A observabilidade ficou em
  12%, porque o projeto B quase não tem nome de log ou métrica nos módulos;
- sem índice do CodeGraph, as relações vêm do `ast`, que só vê `import`: JavaScript sem `import`, `sys.path` com
  import tardio, HTTP e subprocesso ficam de fora e o modelador precisa conhecê-los (no projeto B, 5 de 72 relações
  componente a componente);
- só dois projetos (A e B) tinham passado pela skill nesta data; um projeto sem Python (só JavaScript ou Go) ainda
  não foi provado;
- o Structurizr Lite ainda não mostra as métricas (elas aparecem no explorador, no leitor e no documento 91) e não
  foi aberto na prova do projeto B (a conferência foi no explorador e no site estático).

## Custo da primeira geração (medido)

Nessa rodada, um único agente Opus 5.5 fez tudo. Ela inclui a criação da própria skill (templates, geradores e
testes), que não se repete em projetos novos.

| Medida | Valor |
|---|---|
| Modelo | Opus 5.5 (stack antiga, antes do roteamento) |
| Turnos do modelo | 200 |
| Tokens de saída | 246 mil |
| Leitura de cache | 67,6 milhões de tokens |
| Escrita de cache | 0,49 milhão de tokens |
| Chamadas de ferramenta | 228 |
| Duração | cerca de 50 min |

### Estimativa com a stack atual (sem Opus)

Estimativa, ainda não medida:

- **Projeto novo, geração completa:** cerca de metade dos tokens de saída acima. Quase tudo roda em Haiku ou
  Sonnet, e só o `lodemap-modelador` usa Sonnet high. A skill e os templates já existem.
- **Atualização por checkpoint (incremental):** só `lodemap-gerador` (Sonnet medium) e `lodemap-verificador` (Haiku medium).
  São dezenas de milhares de tokens. Sem mudança estrutural, o trabalho é quase todo de scripts.

- **Escada de economia (no `SKILL.md`):** script antes de modelo. O checkpoint comum, sem módulo novo, removido ou sem
  componente, roda só scripts (`lodemap_diff`, `atualizar.ps1 -Incremental`, `verificar.py` e teste de cobertura), com
  **zero token de modelo**. A ordem de subida é Haiku para diagnóstico, Sonnet low ou medium para correção ou
  métrica nova e Sonnet high só para estrutura nova. Na geração completa, o inventário também sai primeiro por
  script (`inventario.py`).

A primeira medição com a stack nova (um agente Sonnet fazendo todos os papéis) está na seção "Prova no 2º projeto
real (projeto B)", mais abaixo.

## Resultado no projeto A (o que foi gerado)

| Medida | Antes | Depois |
|---|---|---|
| Módulos de primeiro nível de `app/` no modelo | 54 de 98 | **98 de 98**, mais 24 subpastas e 18 rotas |
| Componentes | 153 | **188** |
| Elementos e relações | — | 215 e 338 |
| Visões | 25 | **26**, sendo 7 fluxos animados e 4 por status |
| Métricas curadas com origem conferida em commit | 0 | **10** |

## Testes e verificação

| Verificação | Resultado |
|---|---|
| Cobertura, métricas e `lodemap_diff` (pytest) | 13 de 13 passaram |
| Com os testes do `.env` e do chat, depois do merge | 26 de 26 passaram |
| `node --check` em `dados.js` e no script do `index.html` | ok |
| Explorador em `http://127.0.0.1:8791/explorador/` | 200, sem erro de JS; foco por `#id` e fluxo tocado |
| Structurizr Lite em `http://localhost:8790` | no ar (302 para o workspace) |
| `fit` das visões sem foco (layout "Círculos") | corrigido e conferido em capturas Playwright |

## Validação no projeto de exemplo (a skill fora do projeto A)

| Cenário | Resultado |
|---|---|
| Instalação, pipeline completo e site | gerados; 12 testes verdes; `verificar.py` passou |
| `lodemap_diff.py` sem `ultimoCommit` | `{"modo": "completo"}` |
| Mudança em `src/servico.py` depois da geração | só `appServico` em `componentesAfetados`; nada em `semComponente` |
| `-Incremental` sem mudança | saiu sem regenerar |
| Gancho `post-commit` com commit só de documentação | não disparou |
| Gancho `post-commit` com commit no código | voltou em cerca de 0,5 s e o atualizar rodou em segundo plano (código 0), registrado no `estado.json` |
| Instalação sem GitHub | gera e verifica; a cobertura fica vermelha até haver componentes, como esperado |

## Instalador do pacote

| Cenário | Resultado |
|---|---|
| Instalação limpa num destino temporário | skill e 6 agentes copiados |
| Reinstalação | backup automático (`lodemap.bak-<data>` e `_bak-lodemap-<data>`) |
| Acentos no PowerShell 5.1 | ok (arquivo com BOM) |

## Prova no 2º projeto real (projeto B)

Medição de 02/11/2026 no projeto B (orquestração multiagente): cerca de 316 arquivos Python
versionados (a maioria é teste, prova e snapshot; 63 são módulos de produção, entre Python, JavaScript, Bash e
PowerShell), em 8 pastas de código na raiz e sem `app/` nem `src/`. A prova rodou numa
cópia (`git clone --local`), sem `.codegraph` (relações pelo `ast`) e sem
subagentes: um único agente Sonnet 5.5 fez os papéis de inventário, modelador, métricas, gerador e verificador, na ordem
da escada de economia (script antes de modelo).

| Medida | Valor |
|---|---|
| Tempo total, do clone ao último teste | cerca de 28 min, incluindo a correção dos defeitos da skill e o pacote |
| Tempo só da geração (do clone ao primeiro mapa verde) | cerca de 12 min (19:09 a 19:21) |
| Chamadas de ferramenta | cerca de 100 (estimativa; sem contador) |
| Tokens de saída do agente | cerca de 70 mil (estimativa: ~28 mil de DSL e relações, o resto de código de correção e raciocínio) |
| Modelo | Sonnet 5.5, esforço padrão, sem Opus |
| `inventario.py` + `codegraph_ponte.py --inventario` (ast) | 2,5 s, 0 token |
| `atualizar.ps1` completo (com site estático) | 11 a 17 s, 0 token |
| `verificar.py --qualidade` (com navegador) | 14 s |
| Testes (cobertura, métricas, `lodemap_diff`, ponte, qualidade) pela fila | 25 de 25 em 3,6 a 4,6 s |
| Explorador numa porta do projeto (8801) | 200, 0 erro de JS no console, 11 visões, 4 fluxos, foco por `#id` |

O que foi gerado:

| Item | Valor |
|---|---|
| Módulos cobertos | **63 de 63** (0 fora do modelo) |
| Containers, componentes, relações, visões | 8, 50, 135 e 14 (4 fluxos animados, 3 visões por status) |
| Métricas curadas com origem em commit | 4 (nós, arestas e arquivos de um grafo, e um custo de API), conferidas no teste |
| Modo incremental | commit com um módulo novo: `semComponente = [<pasta>/novo_modulo.py]` e aviso no `atualizar.ps1`; o componente afetado por um arquivo alterado saiu certo |

Nota de qualidade (`qualidade.py`, fonte `ast`), contra o baseline do projeto A (82,2; mínimo para passar 72,2):

| Critério | Projeto B | Projeto A |
|---|---|---|
| Descrição (40+ caracteres, sem repetir o nome) | 100 | 79,8 |
| Código (caminho existe) | 100 | 100 |
| Cobertura | 100 | 100 |
| Recall de relações (todo `import` do código) | 100 (67 de 67 pares) | 27,1 |
| Relações com verbo e tecnologia | 100 | 100 |
| Relações por componente | 100 (3,68) | 98,2 |
| Órfãos, status, visão por container, fluxos, passos, agrupamento | 100 | 100 |
| Precisão das relações (aresta real no código) | 93,1 (67 de 72) | 44,6 |
| Observabilidade | 12,0 (6 de 50) | 14,9 |
| **Total** | **95,2** | **82,2** |

Leitura honesta: o total passa o gate com folga, mas o recall e a precisão do projeto A vêm do CodeGraph e os do projeto B do
`ast`; as duas colunas não são comparáveis nesses dois critérios. As 5 relações que o `ast` não confirma são reais
(`window.Fmt` no JavaScript, `sys.path.insert` com import tardio, fetch entre a página e o servidor).

### Problemas que a skill teve na prova (e o que foi corrigido)

| Problema | Efeito | Correção |
|---|---|---|
| Portas 8790 e 8791 fixas nos templates; a 8790 já era de um serviço do projeto B | o Lite brigaria com um serviço do projeto | `novo_mapa.py --porta-lite --porta-explorador` e `ver-arquitetura.ps1` lendo as portas do `lodemap.json` |
| `lodemap.json` com BOM (o `Set-Content -Encoding UTF8` do PowerShell 5.1 grava BOM) | `atualizar.ps1` caía com traceback no `json.loads`; o aviso só dizia "Traceback" | todo script e teste lê o JSON com `utf-8-sig` |
| No modo `ast`, quase todo par saía com confiança "baixa" e o recall só contava 2+ arestas | recall "1 de 1", nota 100 sem significado | no `ast`, todo `import` entre componentes conta como confiança média; o `qualidade.py` usa mínimo de 1 aresta nesse modo |
| Visões Contexto e Containers sem seta (`!impliedRelationships false`) | o explorador mostrava uma coluna de nós soltos | passo novo no `SKILL.md`: declarar relações de sistema e de container no fim do `relacoes.dsl` |
| Copiar `templates/tests/*.py` à mão deixa `{{ARQ_REL}}` no arquivo | `pytest` não coleta (FileNotFoundError) | `SKILL.md` manda instalar os testes só pelo `novo_mapa.py` |
| Raiz de código única presumida (`app/`, `src/`) | projeto com várias pastas parecia sem lugar no passo 1 | documentado: `--raiz-codigo .` com um glob por pasta; funcionou sem mudar código |

Pendências que ficaram (não corrigidas): o `inventario.py --importadores` varre o repositório todo (inclui snapshots e
testes) e junta módulos de mesmo nome (o mesmo nome de arquivo em duas pastas); o explorador não reage a mudança só de
`#hash` na mesma página (só ao abrir a URL; mudança de comportamento, não visual, deixada para o dono pedir); o
`lodemap_diff.py` só enxerga commits, não alterações soltas na árvore.

## Esqueleto e fases: o mesmo mapa do projeto B, refeito (08/11/2026)

O que mudou na skill (commits 4e077f6, e6cc66e e o desta seção): o `esqueleto.py` escreve o boilerplate do DSL e o
modelador só preenche um JSON de decisões; cada fase do modelo é um `lodemap-modelador` novo, em sequência, com
orçamento de ~100 mil tokens de contexto.

**Desenho.** Mesmo repositório e mesmo commit da rodada de 02/11 (projeto B, `cfeb634`, clone descartável), os mesmos 17 globs
(63 módulos), relações pelo `ast`, Sonnet 5.5, sem Opus. O orquestrador ficou de fora nas duas rodadas. Não é um teste controlado: a rodada de 02/11 incluiu 6 correções da
própria skill e o pacote, e foi um agente só.

| Agente | Modelo | Chamadas | Escrita de cache (1 h) | Leitura de cache | Saída | Maior contexto | US$ |
|---|---|---|---|---|---|---|---|
| A containers, áreas e externos | Sonnet high | 11 | 53.230 | 389.367 | 9.967 | 53.232 | 0,35 |
| B1 componentes (1ª pasta, 19 módulos) | Sonnet high | 11 | 50.209 | 377.600 | 11.913 | 54.692 | 0,36 |
| B2 componentes (2ª pasta, 23) | Sonnet high | 12 | 49.922 | 425.482 | 13.688 | 56.836 | 0,38 |
| B3 componentes (resto, 21) | Sonnet high | 12 | 66.550 | 520.090 | 17.133 | 73.464 | 0,49 |
| C relações e `renderizar` | Sonnet high | 22 | 73.256 | 1.103.962 | 22.211 | 80.170 | 0,63 |
| D visões, exportação e gate | Sonnet high | 17 | 55.450 | 762.461 | 15.663 | 62.364 | 0,45 |
| Métricas | Sonnet low | 7 | 27.398 | 160.780 | 4.645 | 31.881 | 0,17 |
| Verificador | Haiku medium | 6 | 28.630 | 125.222 | 3.827 | 28.632 | 0,01 |
| **Geração (total)** | | **98** | **404.645** | **3.864.964** | **99.047** | **80.170** | **2,84** |

(Entrada sem cache: 196 tokens no total.) Tempo: 04:18:45 a 04:32:43 UTC, 14 min.
Scripts (`novo_mapa`, `inventario`, `esqueleto rascunho`): 12,8 s, 0 token.

| | Um agente (02/11) | Fases (08/11) | Diferença |
|---|---|---|---|
| Custo equivalente | US$ 3,61 | US$ 2,84 | −21% |
| Leitura de cache | 17,6 mi | 3,9 mi | −78% |
| Escrita de cache | 240 mil | 405 mil | +69% (cada agente novo escreve o próprio prefixo) |
| Saída | 88,5 mil | 99 mil | +12% |
| Chamadas acima de 100 mil tokens | 87 de 93 | 0 de 98 | |
| Tempo | 25 min | 14 min | |
| Gate (`qualidade.py`, `ast`) | 95,2 | 96,5 (primeira rodada, sem correção) | |

Onde ficou o custo agora: escrita de cache 53%, saída 34%, leitura 13%. O próximo degrau é a escrita: com o TTL
de 5 minutos ela custaria 1,25× a entrada em vez de 2× (US$ 0,56 a menos), mas o TTL é do Claude Code, não da skill.

**Qualidade.** Gate 96,5 contra o mínimo de 72,2: descrição, código, cobertura, recall, status, visões, fluxos (5) e
agrupamento em 100; observabilidade **77,8** (era 12,0); precisão das relações 89,0 (8 de 73 sem aresta no `ast`, todas
subprocess, `window.X` ou `sys.path`); **órfãos 72,2** (15 de 54 componentes sem relação, era 100): o ponto fraco desta
rodada. 54 componentes (9 módulos fundidos), 80 relações entre componentes e 29 com externos, 20 visões, 7 métricas
com origem em commit. Cobertura 4/4 e testes de arquitetura 43/43; 2 testes de produto do projeto B falham por
dependerem de uma pasta de outro projeto, ausente na máquina (não é o mapa). Navegador: explorador sem erro de console.

**Auditoria independente** (Sonnet medium, agente novo, sem ver o raciocínio do modelador; amostra de 20 componentes e
20 relações sorteada com semente fixa; US$ 0,56, fora do custo da geração): descrições 18 corretas, 2 parciais, 0
erradas; status 20 de 20 plausíveis; observabilidade 14 com nomes que existem, 2 em parte, 0 inventados; relações 20
de 20 confirmadas no código, verbos 20 de 20 adequados. Intervalo de Wilson 95% para "relação confirmada": 84% a 100%.

**Defeitos achados e corrigidos durante a medição:**
- `codegraph_ponte._modulo_de` usava `fnmatch` puro: `app/*.py` casava `app/dados/repo.py`, e a pasta só casava um
  nível abaixo do certo;
- o rascunho via só `.py` e `.js`; módulos `.sh`, `.ps1` e `.html` dos globs ficavam sem componente sugerido;
- a propriedade `status` saía como tag (`EmAndamento`) e o explorador contava 0 "Em andamento": o renderizador grava o
  rótulo e o `arq_comum.status_de` aceita as duas formas (o mapa do projeto C, escrito à mão, tinha 16 componentes nesse
  caso).

**Haiku.** Com todas as chamadas abaixo de 100 mil tokens, os mesmos tokens no preço do Haiku dariam US$ 0,17 (antes a
projeção era US$ 1,26, porque quase toda chamada caía na faixa cara). É projeção: a qualidade do Haiku como modelador
não foi medida.

## Revalidação de 08/11/2026

**Custo.** Recontagem nos transcripts dos subagentes (`~/.claude/projects/<projeto>/<sessão>/subagents/`),
usage deduplicado por `message.id`, preço oficial conferido em 08/11/2026 na página de preços da Anthropic. As três
rodadas tinham escrita de cache que a primeira conta não incluiu, toda ela de 1 hora (`ephemeral_1h_input_tokens`,
cobrada a 2x a entrada):

| Rodada | Arquivo | Entrada | Escrita de cache 1h | Leitura de cache | Saída | Antes | Agora |
|---|---|---|---|---|---|---|---|
| 1ª geração, projeto A (Opus) | agent-a6e9afe483512f699 | 408 | 492.388 | 67.589.674 | 245.733 | 20,88 | 22,37 |
| Gate e ponte (Sonnet) | agent-ae3d1a5790d49745d | 86 | 175.103 | 6.215.934 | 72.624 | 1,35 | 2,05 |
| Mapa do projeto B (Sonnet) | agent-aff1767f44410100b | 186 | 239.572 | 17.627.657 | 88.498 | 2,65 | 3,61 |

Redução Opus → Sonnet: 84% (antes 87%). Projeção Haiku, preço por chamada conforme o tamanho do prompt: US$ 1,26;
87 de 93 chamadas passaram de 100 mil tokens, então a faixa barata (US$ 0,22) não se aplica a esta execução. Fica de
fora o orquestrador: a sessão-mãe fez 39 chamadas Opus na janela do projeto B (US$ 2,33), mas rodava outros agentes ao
mesmo tempo e o custo não é atribuível só ao mapa.

**Para onde foi o custo (projeto B).** Leitura de cache 49%, escrita de cache 27%, saída 25%. O contexto por chamada
começou em 67 mil tokens (antes de qualquer trabalho), teve mediana de 198 mil e terminou em 263 mil. Nenhum intervalo
entre chamadas passou de 127 s, então a escrita de 1 hora não trouxe vantagem sobre a de 5 minutos.

**Atualização sem modelo**, refeita no projeto C num worktree descartável: completa 12,0 s; incremental sem mudança 1,4 s;
incremental depois de um commit de código 13,7 s (regenera tudo). Zero chamadas de modelo.

**Precisão no projeto C.** Gate, modo ast: 92,9 (recall 95,5; precisão 75,0, porque 7 relações do modelo não aparecem nos
imports). Auditoria independente, agente Sonnet lendo o código, amostra com semente 7:
- as 7 relações que o ast não achou existem (subprocesso, leitura de JSON gerado ou chamada indireta): 7/7, Wilson 65–100%;
- 10 relações sorteadas entre as 43: 8 existem, 1 é só planejada, 1 não verificável; rótulo correto em 7 (Wilson para 8/10: 49–94%);
- 10 descrições sorteadas: 7 corretas, 3 parciais (omitem parte do que o arquivo faz), 0 erradas.

Conclusão: a precisão do modo ast subestima as relações de componente para componente, que fecharam 28/28 conferidas.
O erro real está nas relações com sistemas externos e planejadas e na completude dos rótulos e descrições.

## Medições independentes (02/11/2026, 19:40)

**1. Tokens exatos**, lidos do registro dos agentes e deduplicados por mensagem:

| Rodada | Modelo | Chamadas | Saída | Leitura de cache | Duração |
|---|---|---|---|---|---|
| 1ª geração, projeto A (inclui criar a skill) | Opus | 200 | 245,7 mil | 67,6 mi | 50 min |
| Gate de qualidade e ponte com o CodeGraph | Sonnet | 41 | 72,6 mil | 6,2 mi | 11 min |
| Prova no projeto B (inclui 6 correções e o pacote) | Sonnet | 93 | 88,5 mil | 17,6 mi | 25 min |

A prova no projeto B gastou 64% menos tokens de saída e 74% menos leitura de cache que a 1ª geração, sem usar Opus. A estimativa anterior, de cerca de 70 mil tokens, ficou abaixo do medido.

**2. Avaliação independente**, numa amostra com semente 42:
- **Descrições:** 14 de 15 corretas e 1 parcial (93%; Wilson de 95%: 70% a 99%).
- **Relações:** 20 de 20 existem no código (Wilson: 84% a 100%). Duas têm o texto com defeito: a tecnologia errada (Playwright em vez de Edge headless) e uma descrição exagerada. A precisão estrita é 90%.
- **Ajuste da régua do modo ast:** não mudou a nota (95,2 nas duas versões).
- **Ressalvas:**
  - no ast, o recall é circular, porque o modelo nasce dos mesmos imports;
  - a cobertura é medida pelos próprios globs da skill;
  - por isso, o valor honesto do projeto B fica entre 90 e 95.

**3a. CodeGraph contra ast no projeto B**, com o índice de 358 arquivos e nenhum defasado:

| Fonte | Total | Recall | Precisão |
|---|---|---|---|
| CodeGraph | 94,0 | 88,4 | 93,1 |
| ast | 95,2 | — | 93,1 |

A nota do CodeGraph é a mais independente.

**3b. Linguagens:** a skill NÃO é agnóstica de linguagem.
- O modo ast lê Python, JS/TS, Go, Rust, Java, Kotlin, C# e C/C++ (limites em `arestas-codigo.md`). Na medição original, que só lia
  Python e JS/TS, ele viu 0 de 57 arquivos num crate Rust; com os extratores novos, achou 1619 arestas em 519 `.rs` de um
  repositório Rust (precisão dessas arestas não medida).
- Fora dessas linguagens, use `--fonte codegraph` (o CodeGraph indexa mais de 30) ou faça a modelagem manual.

## Demo pública: axios v1.20.0 e a atualização para a v1.21.1 (09/11/2026)

Primeiro mapa feito num repositório público, para qualquer pessoa poder refazer: [axios](https://github.com/axios/axios),
JavaScript, globs `lib/**/*.js`. Mapa em inglês (`"idioma": "en"`). Tokens lidos dos transcripts dos subagentes, uso
deduplicado por `message.id`; toda escrita de cache foi de 1 hora. Preços de `custo-equivalente.json`.

**Mapa completo na v1.20.0 (69 módulos, 8 áreas, 6 fluxos, 176 relações entre componentes).**

| Fase | Modelo | Chamadas | Escrita de cache | Leitura de cache | Saída | Pico de contexto | Tempo | US$ |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| A containers e áreas | Sonnet high | 9 | 47.961 | 290.130 | 7.459 | 47.963 | 75 s | |
| Rota enxuta (`descrever.py`, 69 módulos) | Haiku medium | 1 | | | | | 66 s | < 0,03 |
| B container e status | Sonnet high | 9 | 41.956 | 273.501 | 7.793 | 48.870 | 86 s | |
| C relações | Sonnet high | 25 | 92.641 | 1.482.281 | 30.948 | 97.124 | 284 s | |
| D fluxos | Sonnet high | 7 | 41.112 | 222.603 | 12.552 | 48.302 | 89 s | |
| **Modelador (total)** | | **50** | **223.670** | **2.268.515** | **58.752** | **97.124** | **534 s** | **1,71** |

(Entrada sem cache: 100 tokens.) A chamada de Haiku somou 54.116 tokens; a divisão por tipo não foi guardada, então o
custo dela aparece como teto: todos os tokens cobrados como saída dariam US$ 0,027. Total do mapa: no máximo US$ 1,74.
Gate de qualidade: 94,5 (linha de base 82,2). Ficam de fora o orquestrador e a conferência final (scripts e navegador
sem cabeça, sem modelo).

**Atualização para a v1.21.1** (99 commits no upstream; 27 arquivos alterados em `lib/`, 3 novos). Depois do merge, o
teste de cobertura falhou citando os 3 arquivos.

| Passo | Quem | Chamadas | Tokens | Tempo | US$ |
|---|---|---:|---|---:|---:|
| `esqueleto.py rascunho`: 3 novos, 16 a revisar, 12 relações novas | script | 0 | 0 | | 0 |
| `descrever.py`: 3 descrições novas e 16 revisões (15 mantidas) | Haiku medium | 1 | 26.029 | 34 s | < 0,02 |
| Modelador: container e status dos 3, verbo das 12 relações, conferência dos 6 fluxos | Sonnet high | 19 | escrita 58.488, leitura 830.471, saída 13.600 | 129 s | 0,45 |
| `renderizar` e `atualizar.py --incremental` | scripts | 0 | 0 | 17 s | 0 |

Total da atualização: no máximo US$ 0,47. Depois: 72 componentes, 188 relações (177 com import que as confirma, 11
acrescentadas à mão), gate 94,5, 86 testes de arquitetura passando.

**O que a demo achou na skill** (tudo corrigido com teste antes de fechar): globs padrão só de Python; `**` que não
casava arquivo na raiz do código (44 de 165 arestas perdidas); piso de observabilidade reprovando biblioteca; revisão
que reescrevia nome, frase e área de módulo estável (16 de 16 frases, 8 nomes, 3 áreas); aviso de módulo sem
componente calculado sobre o modelo antigo; painel de mudanças cego para arquivos fora de um nível de pasta; caminho
absoluto da máquina dentro do `dados.js` versionado; `decisoes-modelo.json` fora do git.

**Limites.** Uma rodada de cada. O custo é equivalente pela API, não fatura. A qualidade das descrições e das
relações não passou por auditoria independente com amostra sorteada neste repositório.

## Política de atualização, repetida sobre o merge da v1.21.1 do axios (09/11/2026)

O `lodemap_decidir.py` foi rodado numa cópia do repositório da demo no commit do merge (antes da atualização do mapa),
com a última geração marcada no commit do mapa da v1.20.0. Nenhuma chamada de modelo; os números de revisão e de
relação vêm do `esqueleto.py pendencias`, que não grava nada.

| Situação | Resposta do script | Teste de cobertura |
|---|---|---|
| política padrão (`tolerancia_modulos` 0) | `modelar`: 3 módulos fora do modelo, citados pelo nome | falha, citando os 3 |
| `tolerancia_modulos` 3, sem a pasta da skill (o que o gancho enxerga) | `adiar`: os 3 cabem na tolerância e ainda não têm prazo | falha, pedindo o `--adiar` |
| depois do `--adiar` (`pendentes.json` com os 3, de 09/11, valendo até 23/11) | sem a skill: os 3 podem esperar | passa |
| a mesma situação, com a skill ao alcance | `modelar`: 12 relações novas (limite 10); o lote traz os 3 módulos, 16 revisões e 12 relações | passa |
| a mesma situação, 15 dias depois (`LODEMAP_HOJE=2026-11-24`) | `modelar`: prazo vencido em 23/11 para os 3 | falha, com a data |

Os três números do lote (3 módulos, 16 revisões, 12 relações) são os mesmos que a atualização real tratou naquele
merge. Ou seja: num lançamento com 99 commits, a política chama o modelo uma vez, para tudo, mesmo com tolerância.

**Limite.** Isto mostra que a decisão é a certa neste caso e não gasta token. Não mede quanto se economiza adiando e
juntando: para isso falta comparar, no mesmo repositório, uma atualização por módulo com uma atualização do lote.

## Validação (fase 3): repetição, Linux, Go e a digital (09/11/2026)

Quatro perguntas que a demo do axios deixou abertas: o custo da atualização se repete? A skill roda fora do Windows?
Funciona numa terceira linguagem? A impressão digital deixa passar mudança que importa? Tudo em repositório público.
Mesmo método de contagem: tokens dos transcripts dos subagentes, uso deduplicado por `message.id`, preços de
`custo-equivalente.json`; a chamada de Haiku entra como teto (todos os tokens cobrados como saída).

### A atualização do axios, três vezes (v1.20.0 para v1.21.1)

Mesmas entradas e mesmo pedido, em três clones do commit do mapa. O script deu o mesmo rascunho nas três (3 novos, 16 a
revisar, 12 relações novas, 0 tokens).

| Rodada | Haiku (tokens) | Frases mantidas | Modelador: chamadas | Escrita de cache | Leitura de cache | Saída | Tempo | US$ modelador | US$ total (teto) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 26.029 | 15 de 16 | 19 | 58.488 | 830.471 | 13.600 | 129 s | 0,45 | 0,47 |
| 2 | 23.721 | 16 de 16 | 13 | 53.195 | 459.201 | 9.291 | 80 s | 0,35 | 0,36 |
| 3 | 25.479 | 14 de 16 | 9 | 43.866 | 297.652 | 7.635 | 64 s | 0,28 | 0,29 |

Média US$ 0,37; a faixa é de 0,29 a 0,47, e a primeira rodada (a que estava publicada) foi a mais cara. Nas três os
portões passaram (gate 94,5, testes de arquitetura, `atualizar.py` em 11 s).

**O que se repete:** 72 componentes, 188 relações, as 12 relações novas mantidas nas três, os 6 fluxos sem mudança.
**O que varia:** a área de um dos 3 módulos novos (`lib/core/assertParamsAcyclic.js`: `AreaUrlHeaders` na rodada 1,
`AreaClient` nas rodadas 2 e 3; quem o chama, `mergeConfig.js`, está em `AreaPipeline`) e o texto: os verbos das 12
relações novas diferem em 11 ou 12 entre duas rodadas, e de 4 a 6 frases de descrição mudam de redação. A estrutura
é estável; a redação e uma decisão de área em três não são.

### Linux de ponta a ponta

WSL Ubuntu 24.04, Python 3.12.3, Java 21 (Temurin), Structurizr CLI de verdade.

| O que | Windows | Linux |
|---|---|---|
| Suíte da skill (árvore final) | 415 passam em 8 min 33 s | 414 passam, 1 pulado, em 59 s |
| `atualizar.py` completo no mapa do axios | 11 a 17 s | 8 a 9 s |
| `atualizar.py` completo no mapa do chi | 11 s | 5 s |
| Documentos derivados e inventários do axios | referência | idênticos byte a byte; só os carimbos de data mudam |
| Testes entregues ao projeto (axios e chi) | 91 passam, 1 pulado | 91 passam, 1 pulado |
| Gate de qualidade | 94,6 (axios) e 94,3 (chi) | 94,6 e 94,3 |
| Gancho de git real | | commit no modelo regenera em ~5 s; commit só de código registra que não regenerou; `--remover` limpa |

A primeira rodada no Linux achou dois defeitos, corrigidos com teste: um teste que dependia de o `.sh` falso ter
permissão de execução, e o gancho, que sem a skill instalada em `~/.claude` não achava o template e deixava a prova de
relações velha (`atualizar.py` agora também aceita `LODEMAP_SKILL`). As fases com modelo rodaram só no Windows.
macOS continua sem rodada real.

### Go: go-chi/chi v5.4.0, do zero, e a atualização para a v5.5.0

Terceira linguagem e primeiro repositório com o código na raiz, sem `src/`. Mapa em inglês: 2 containers, 8 áreas,
35 componentes, 34 relações (31 do código, 3 à mão), 5 fluxos.

| Fase | Modelo | Chamadas | Escrita de cache | Leitura de cache | Saída | Tempo | US$ |
|---|---|---:|---:|---:|---:|---:|---:|
| A containers e áreas | Sonnet high | 9 | 38.292 | 286.108 | 5.756 | 54 s | |
| Rota enxuta (`descrever.py`, 35 módulos) | Haiku medium | 1 | | | 31.213 no total | 34 s | < 0,02 |
| B container, status e conferência das frases | Sonnet high | 21 | 74.025 | 1.221.083 | 11.699 | 145 s | |
| C relações e conferência das frases | Sonnet high | 26 | 95.958 | 1.621.455 | 23.048 | 209 s | |
| D fluxos | Sonnet high | 10 | 48.284 | 352.096 | 12.182 | 118 s | |
| **Modelador (total)** | | **66** | **256.559** | **3.480.742** | **52.685** | **526 s** | **1,90** |

Total do mapa: no máximo US$ 1,92. Custou mais que o do axios (US$ 1,74) com metade dos módulos porque as fases B e C
receberam um pedido a mais: abrir os arquivos e conferir as frases da rota enxuta contra o código.

**Atualização para a v5.5.0** (6 arquivos de produto alterados, 1 novo). O teste de cobertura falhou citando
`middleware/deprecation.go`; o `lodemap_decidir.py` respondeu `modelar`.

| Passo | Quem | Chamadas | Tokens | Tempo | US$ |
|---|---|---:|---|---:|---:|
| `esqueleto.py rascunho`: 1 novo, 1 a revisar, 0 relações | script | 0 | 0 | | 0 |
| `descrever.py`: 1 descrição nova, 1 revisão | Haiku medium | 1 | 5.767 | 14 s | < 0,01 |
| Modelador: container e status do novo, nome do revisado, conferência das outras 4 frases e dos 5 fluxos | Sonnet high | 7 | escrita 37.401, leitura 225.082, saída 3.640 | 41 s | 0,21 |
| `renderizar` e `atualizar.py --incremental` | scripts | 0 | 0 | 15 s | 0 |

Total: no máximo US$ 0,22. Depois: 36 componentes, 34 relações, gate 94,3, 91 testes passando. O piso de uma
atualização com modelador é o contexto da sessão: 37 mil tokens de escrita de cache para decidir um módulo.

**O que o mapa em Go mostrou**

- **Arestas.** Em Go todo arquivo do pacote enxerga os outros sem import. A ponte ligava cada arquivo do pacote
  `middleware` ao primeiro arquivo do pacote `chi` (6 arestas, todas erradas). Agora ela resolve o símbolo usado
  (`alias.Nome` entre pacotes, nome de topo entre arquivos do mesmo pacote): 31 arestas, as 31 confirmadas no código
  por dois agentes em leituras separadas. Faltaram 3 relações reais, de método e de interface, que entraram à mão:
  31 de 34.
- **Frases da rota enxuta.** Das 35 frases do Haiku, 6 afirmavam algo falso sobre o módulo e 2 eram vagas (4 achadas
  entre 21 arquivos abertos na fase B, 2 entre 26 na fase C). O modelador corrigiu todas. No axios essa conferência
  nunca foi feita, então a taxa lá é desconhecida. A nota de qualidade não pega frase falsa: mede forma, não verdade.
- **Digital.** Na v5.5.0 o `Sunset` deixou de escrever o cabeçalho `Deprecation`, com a mesma assinatura. A digital
  não marcava o arquivo e a frase guardada ficaria falsa. Entrou a regra do comentário de doc em Go; com ela o
  arquivo foi marcado, o Haiku corrigiu a frase e o modelador trocou o nome do componente. Das outras 4 frases de
  arquivos alterados e não marcados, o modelador abriu os diffs e as 4 continuavam verdadeiras.

### A digital deixa passar mudança que importa?

Estudo sem modelo, lendo um a um os diffs que a digital não marcava em 10 pares de versões do rich e do axios: 12 de
92 arquivos não marcados escondiam mudança de superfície (3 no rich, 9 no axios). A versão 2 pega 9 dos 12 sem marcar
nenhum arquivo a mais sem motivo, e migra os mapas antigos sem revisão em massa. Tabelas e o que continua de fora:
`digital-semantica.md`.

### Defeitos da skill achados nesta fase (todos corrigidos com teste)

Teste ao lado do código virava módulo (lista `"ignorar"`); raiz do código presumida como `src/` (detecção); arestas de
Go por pacote (resolução por símbolo); segundo `rascunho` apagava a lista de relações por decidir e perderia revisões
pendentes (pendências que só somem quando alguém decide); gate de qualidade reprovando o mapa certo de uma biblioteca
de módulos independentes, 89,6 com dois critérios abaixo do piso (rubrica que olha o código); explorador empilhando 26
nós sem ligação numa coluna ilegível (grade) e repetindo sete nomes cortados iguais na barra lateral; passos de fluxo
numerados duas vezes; lacunas da digital em Python, JS e Go; tokenizador de JS que se perdia em regex com aspas.

**Limites desta fase.** Três rodadas de uma atualização num repositório, uma rodada de cada coisa no chi. A
conferência das frases foi feita pelo próprio modelador, não por leitor independente. Não foi medido: se o mapa ajuda
um agente de código; quanto se economiza juntando atualizações; macOS; monorepo; repositório grande. As mensagens do
`novo_mapa.py` e o campo `descricao` do `lodemap.json` saem em português mesmo com `--idioma en`.
