---
name: lodemap
description: Lodemap. Use quando o dono pedir "lodemap", "mapa de arquitetura", "arquitetura C4", "Structurizr", "Structurizr DSL", "explorador da arquitetura", "documentar a arquitetura", "diagrama C4 do projeto", "modelo de componentes" ("architecture map", "C4 model", "document the architecture"), ou quiser criar, completar, atualizar ou conferir a arquitetura de um repositório (módulos fora do modelo, status dos componentes, fluxos animados, métricas ligadas aos componentes, atualização a cada commit ou merge). Gera um modelo C4 em Structurizr DSL versionado no repositório, com teste de cobertura que falha se um módulo ficar fora, explorador interativo, leitor de documentação e decisões e métricas com origem em commit (pt por padrão, ou en), regenerados por scripts sem chamar modelo, com a stack fixa de agentes lodemap-*.
---

# Lodemap

Mapa de arquitetura vivo de um repositório, com uma fonte só (o Structurizr DSL no repositório) e saídas geradas: o
explorador interativo (o único visualizador), o leitor de documentação e decisões (`leitor/`), os documentos derivados
e as métricas por componente. O Structurizr Lite e o site estático são opcionais (`--com-lite`, `--com-site`). As
saídas saem em português por padrão; `"idioma": "en"` no `lodemap.json` (ou `novo_mapa.py --idioma en`) as gera em
inglês, e o explorador e o leitor trocam PT | EN na barra de topo.

Este arquivo traz o que o orquestrador precisa em toda execução. O detalhe fica em `references/` e é lido só quando o
passo pede (tabela "Leia quando precisar", no fim).

## Regra fixa do visual

**O visual segue o design system da família Lode (tokens em `explorador/index.html` e `leitor/index.html`, bloco
`sds:tokens`, igual nas duas); mudanças visuais só com o OK do dono.** Por projeto só mudam os dados (`dados.js`,
gerado), o nome do projeto e as URLs, todos vindos do `lodemap.json`. Correção de comportamento (bug) pode; mudança de
aparência precisa do OK do dono, com captura antes e depois, e passa pelo `lodemap-revisor-visual`. O mesmo vale para
`views/estilos.dsl` (cores e formas por tag).

## Stack de agentes e roteamento

A stack é fixa e fica em `~/.claude/agents/` (não recrie; se faltar, `python -m lodemap instalar --perfil minimo --aplicar`).

| Agente | Modelo | Esforço | Passo | Quando chamar |
|---|---|---|---|---|
| `lodemap-inventario` | haiku | low | 2. Inventário | Começo de um mapa novo, ou módulos novos que o `lodemap_diff.py` não soube classificar. Grava `inventario.json`. Somente leitura. |
| `lodemap-modelador` | sonnet | high (único que decide arquitetura) | 3 a 7. Containers, componentes, relações, fluxos e status | Mapa novo; módulo em `semComponente`; mudança estrutural (container, área, fluxo novo). Só recebe as áreas afetadas. |
| `lodemap-metricas` | sonnet | low | 8. Métricas curadas | Evidência nova de medição; métrica com fonte a conferir. |
| `lodemap-gerador` | sonnet | medium | 1 e 9. Templates, `lodemap.json`, pipeline, `atualizar.py` | Instalação, geração e regeneração a cada merge. |
| `lodemap-verificador` | haiku | medium (não edita) | 10 a 12. Cobertura, `node --check`, headless, fontes das métricas | Depois de toda geração; devolve achados por escrito. |
| `lodemap-revisor-visual` | sonnet | high (só com pedido visual) | Mudança visual | Somente quando o dono pede mudança de aparência. |

Ordem do fluxo: `lodemap-inventario` → `lodemap-modelador` → **gate de qualidade** (`qualidade.py`, volta ao modelador
se reprovar) → (`lodemap-metricas` em paralelo com o `lodemap-gerador`) → `lodemap-verificador` → `lodemap-revisor-visual`, só
se houver pedido visual.

Regras de economia:

- a sessão principal só orquestra: escolhe o passo, passa caminhos e lê as respostas curtas;
- o modelo mais forte nunca é o primeiro degrau. **Escalada única:** se um Sonnet falhar (gate de qualidade reprovado de
  novo depois de uma correção, ou o mesmo achado do verificador reaparecendo), o mesmo passo é refeito uma vez por
  **Opus com esforço `medium`**, só nas áreas reprovadas e com o contexto do achado. Falhou de novo: pare e reporte ao
  dono, sem terceira tentativa. Registre a escalada em `.lodemap/escaladas.json` (passo, motivo, modelo);
- leitura e busca vão para haiku low (`lodemap-inventario`); trabalho mecânico vai para sonnet medium (`lodemap-gerador`);
- `high` só para decisão de arquitetura (`lodemap-modelador`) e para o visual (`lodemap-revisor-visual`);
- correção a partir de achados já escritos (do verificador ou de um revisor) vai para sonnet (`lodemap-gerador` ou
  `lodemap-metricas`), nunca de volta para quem decide;
- trabalho pesado (pytest, suítes) só pela fila do projeto, se ele tiver uma;
- para atualizar um mapa que já existe, pergunte antes ao `lodemap_decidir.py` (seção "Quando atualizar") e rode só o que
  a `acao` pedir; o `lodemap-modelador` entra apenas com `acao` `modelar`, numa sessão só para o lote inteiro.

### Escada de economia: script antes de modelo

Suba um degrau só quando o de baixo falhar:

0. **Degrau zero: arestas do código, sem modelo.** Antes de qualquer agente ler arquivo, rode
   `codegraph_ponte.py` (somente leitura): `--inventario` entrega o rascunho do `inventario.json` (arquivos,
   símbolos, docstrings); `--relacoes` entrega o `relacoes-codigo.json` (pares componente → componente com contagem
   de arestas e `confianca`); `--impacto <arquivo>` entrega os componentes afetados por um arquivo. Sem índice do
   CodeGraph, a ponte cai sozinha para `ast`.
1. **Zero token (padrão do checkpoint):**
   - `python scripts/lodemap_decidir.py` (seção "Quando atualizar"): diz se há o que fazer e em que degrau;
   - `acao` `nada` ou `adiar`: fim, sem regenerar e sem agente;
   - `acao` `scripts`: `python scripts/atualizar.py --incremental --checkpoint "<rótulo>"`, depois
     `python ~/.claude/skills/lodemap/scripts/verificar.py --arq docs/architecture/structurizr --sem-navegador`
     e o teste de cobertura. Tudo verde: fim, sem nenhum agente. É o caminho do gancho do git.
2. **Haiku:**
   - script falhou com erro claro (traceback, link quebrado): `lodemap-verificador` lê só a saída e aponta a linha;
   - inventário: rode antes `python ~/.claude/skills/lodemap/scripts/inventario.py --json`. O
     `lodemap-inventario` entra só para os `naoClassificados`;
   - nome, descrição e área de componente: `descrever.py` (rota enxuta, abaixo), antes de qualquer subagente.
3. **Sonnet low ou medium:**
   - correção mecânica a partir do apontamento: `lodemap-gerador`;
   - métrica nova: `lodemap-metricas`. Para atualizar uma métrica que já existe, basta reler a fonte declarada (arquivo
     e chave), sem agente.
4. **Sonnet high (`lodemap-modelador`):**
   - só para módulo novo sem componente, container novo, fluxo novo ou a primeira geração;
   - no incremental, passe apenas as áreas de `componentesAfetados`.

### Esqueleto e geração em fases

O custo de um mapa vem quase todo da **releitura do contexto** (medido: um agente só, 93 chamadas, mediana de 198 mil
tokens de contexto por chamada; ver `references/benchmark-e-custo.md`). Duas regras atacam isso sem tirar decisão do
modelo:

1. **Esqueleto por script.** `esqueleto.py rascunho` grava `.lodemap/decisoes-modelo.json`: um componente sugerido por
   módulo (id, caminho, linhas, dica da docstring, símbolos) e uma relação sugerida por par de módulos com arestas no
   código, com os campos de decisão vazios. O modelador **não escreve DSL de componente nem de relação entre
   componentes**: preenche nome, descrição, container, área e status de cada componente, e `manter` + verbo de cada
   relação que conferiu no código. `esqueleto.py renderizar` confere que nada ficou sem decisão e escreve
   `model/containers.dsl`, `model/componentes-<container>.dsl`, `model/relacoes-componentes.dsl` e as visões
   estáticas. À mão ficam só pessoas, sistemas externos, as relações com eles e os fluxos dinâmicos.
2. **Fases com agente novo.** Num mapa novo, cada fase é um `lodemap-modelador` **novo** (nova chamada do Agent, nunca
   a continuação do anterior), em sequência, todos no mesmo `decisoes-modelo.json`:
   - **Fase A, containers e áreas:** lê o `inventario.json` e o rascunho (não lê código, salvo pontos de entrada);
     preenche `containers` e `areas` e escreve `pessoas-externos.dsl`.
   - **Fase B, componentes.** Primeiro a **rota enxuta** (padrão para nome, descrição e área):
     `python ~/.claude/skills/lodemap/scripts/descrever.py --arq <pasta>`. Ela chama o `claude -p` oficial (assinatura,
     nunca API) em Haiku medium, sem ferramentas nem MCP, com saída por JSON Schema e a área presa às áreas da fase A,
     e manda uma ficha determinística por módulo. Cada frase traz evidência copiada da ficha, e o gate reprova frase sem
     evidência, genérica ou com nome de código que o módulo não tem; os reprovados são reenviados uma vez. Depois uma
     segunda chamada Haiku lê o código de cada módulo e corrige ou rejeita a frase falsa (`--sem-conferir` desliga;
     `--auditar` só lista as falsas de um mapa existente, sem mudar nada). Saída 0: tudo descrito.
     Saída 3 (ou `claude` fora do PATH): o que faltou está em `pendentes.descricoes_para_modelador`. Depois, um
     modelador por container (ou por bloco de até ~25 módulos) preenche container e status, confere **contra o
     código** cada frase que veio com `descrito_por` (com a conferência, 5 de 213 frases ainda eram falsas em chi e axios) e descreve só
     o que sobrou. Medição em `references/rota-enxuta.md`.
   - **Fase C, relações:** confere cada relação sugerida no código (`manter` true ou false, verbo, tecnologia),
     acrescenta as que o código não mostra (HTTP, subprocess, import tardio) com `manual: true`, para o próximo
     `rascunho` não marcá-las como sumidas, e escreve as relações com externos em `model/relacoes.dsl`.
   - **Fase D, só fluxos:** as visões estáticas (Contexto, Containers, componentes por container, por área quando
     o container tem 12+ componentes e mais de uma área, e as filtradas por status) saem do `renderizar` em
     `views/visoes-geradas.dsl`, sem modelo. O modelador escreve só os `dynamic` em `views/visoes.dsl`.

   Cada fase passa o estado pelo arquivo, nunca pela conversa. **Orçamento de contexto:** um agente que passar de ~100
   mil tokens de contexto termina a fase, grava as pendências no `estado.json` e devolve; a próxima chamada é de um
   agente novo.

**Atualização do modelo só no que mudou.** Num mapa com `decisoes-modelo.json`, rode `esqueleto.py rascunho` de novo.
Ele preserva toda decisão tomada e lista em `pendentes`: `componentes_novos`, `relacoes_novas` e
`componentes_revisar`, os módulos cuja impressão digital semântica (docstring, imports, assinaturas e símbolos
públicos, constantes de topo, atributos e membros de classe, chaves de objeto exportado) mudou. Mudança só de corpo, comentário ou formatação não pede revisão
(`references/digital-semantica.md`). Em `removidos` ficam os módulos que sumiram, e as relações que o código não
mostra mais ganham `sumiu_do_codigo`. Rodar o `rascunho` de novo não apaga pendência: relação sem decisão e revisão
por fazer continuam na lista até alguém decidir, e o `renderizar` limpa as listas quando aceita o modelo. Rode `descrever.py` para os novos e a revisar (`--resumo` imprime uma linha em
vez do relatório). A revisão é conservadora: o módulo que já tinha nome, descrição e área mantém nome e área, e a
frase só muda se a mudança no código a tornou falsa. O modelador recebe só `descricoes_para_modelador` e as decisões
que o script não toma (container, status, relações), nunca o JSON inteiro, e o `renderizar` fecha. Sem pendência
nenhuma, nenhum agente.

Mapa antigo, sem `decisoes-modelo.json` (DSL escrito à mão): continue editando o DSL; não rode o `renderizar`, que
reescreveria `containers.dsl`.

## CodeGraph

**A skill NUNCA roda `codegraph init` (nem `codegraph index`) sozinha.** Indexar é decisão do dono. A skill usa
`<repo>/.codegraph/codegraph.db` se ele existir (aberto em `mode=ro`) e, se não existir, sugere ao dono ("rodar
`codegraph init` melhora o recall das relações") e segue pelo modo `ast`, que lê só imports. Nenhum script da skill
cria, atualiza ou apaga o índice.

As arestas são **sugestão, não verdade**: cada par sai com `confianca` (alta, média ou baixa), o modelador confirma no
código e nada entra no DSL de forma automática. `--fonte auto` (padrão) escolhe o CodeGraph se o índice existir e
senão o `ast`. **Registre no `estado.json`** a fonte usada (`fonteRelacoes`) e compare notas de recall só da mesma
fonte. O que cada fonte vê e não vê: `references/arestas-codigo.md`.

## Engenharia de contexto

- **Caminhos, nunca conteúdo:** o orquestrador passa caminhos de arquivo e o passo a cumprir; não cola código, DSL,
  diffs nem saídas longas no prompt de um agente.
- **Passagem por arquivo:** os agentes conversam pelos artefatos: `inventario.json`, `.lodemap/decisoes-modelo.json`,
  `model/*.dsl` e `views/*.dsl`, `metricas/*.json` e `.lodemap/estado.json` (estado e pendências; formato em
  `references/estado-json.md`). Cada agente atualiza só o seu bloco em `estado.json`; o `atualizar.py` grava
  `ultimoCommit`, `geradoEm`, `checkpoint` e `historico` no fim de uma geração verde.
- **Resposta curta:** cada agente responde em no máximo 12 linhas: o que fez, os números e as pendências.
- **Modo incremental:** com `ultimoCommit` no `estado.json`, rode `python scripts/lodemap_diff.py` primeiro. Só as áreas
  dos `componentesAfetados` (e os `semComponente`) vão ao `lodemap-modelador`; sem mudança estrutural, rode só
  `lodemap-gerador` → `lodemap-verificador`.
- **CodeGraph:** se o repositório tiver `.codegraph/`, use `codegraph_explore` (ou `codegraph explore "..."`) antes de
  Grep e Read para entender um módulo.
- **Cache de prompt:** os prompts dos agentes começam com um prefixo estável (papel, regras, caminhos fixos da
  arquitetura) e só no fim trazem o que muda (passo, áreas afetadas, commit).
- **Orçamento de leituras por agente:** inventário lê só cabeçalhos e definições (até ~40 arquivos por rodada);
  modelador lê o `inventario.json`, a saída do `lodemap_diff.py` e só os `.dsl` das áreas afetadas; métricas lê só a
  estrutura e os números das evidências (nunca o texto); gerador e verificador não leem código de produto.
- **Leitura em blocos:** arquivo grande (DSL de servidor, `dados.js`, evidências) se lê com offset e limite, ou com
  um script que imprime só a estrutura; nunca inteiro.

## Ferramentas (uma vez por máquina)

`python -m lodemap doctor` confere tudo abaixo sem gastar token.

- Python 3.11+ (`LODEMAP_PYTHON` ou `--python`) e git.
- Java 21 (`java -version`) e uma pasta de ferramentas (padrão `~/.structurizr`, ou `STRUCTURIZR_FERRAMENTAS`, ou
  `--ferramentas`) com o Structurizr CLI (`cli/structurizr.bat` ou `structurizr.sh`), o Graphviz (`dot`, da pasta ou
  do PATH) e, se quiser o Lite, `structurizr-lite.war`.
- Opcional: `claude` no PATH (rota enxuta), Node (`node --check`) e Playwright com Chromium (checagem no navegador).

Instalar ou mudar coisa do sistema (PATH global, variável de ambiente permanente, tarefa agendada) só com
autorização do dono.

## Permissão antes de gerar

Nada é gerado sem o ok do dono. Antes do passo 1 (e antes de qualquer passo com modelo):

1. Rode o plano, que gasta **0 tokens**: `python -m lodemap plano --repo <raiz>` (a partir de
   `~/.claude/skills/lodemap`). Ele conta os módulos, estima custo e tempo pelo modelo de custo medido
   (`references/custo-equivalente.json`, valores-piso) e lista os arquivos que seriam escritos.
2. Mostre o plano ao dono e **peça o ok**. Com o ok, grave o consentimento:
   `python -m lodemap consentir --repo <raiz> --escopos gerar[,gancho,modelo] [--orcamento-mensal X]`
   (vai para `<pasta da arquitetura>/.lodemap/consentimento.json`; revoga com `python -m lodemap revogar --repo <raiz>`).
3. Passo com modelo (inventário, modelagem, `descrever.py`, revisão com subagentes) exige o escopo `modelo` dentro do
   teto: `python -m lodemap verificar --repo <raiz> --escopo modelo --custo <estimativa>` (saída 0 = autorizado). Sem
   isso, peça confirmação explícita ao dono antes de cada passo com modelo. O gancho por commit só com o escopo
   `gancho`.

O hook opcional `hooks/aviso_lodemap.py` (perfil `padrao` do instalador) injeta uma linha única por repositório sem
mapa sugerindo o plano; ele não gera nada. O instalador (`python -m lodemap instalar --perfil minimo|padrao`, plano por
padrão, `--aplicar` grava com manifesto, `reverter` restaura os bytes) instala só a skill, os seis agentes `lodemap-*`
e, no `padrao`, esse aviso.

## Processo

Siga na ordem. Cada passo tem um critério de pronto e um agente dono (tabela acima). O passo 1 só depois do ok
do dono.

1. **Instalar no repositório** (`lodemap-gerador`).
   `python ~/.claude/skills/lodemap/scripts/novo_mapa.py --repo <raiz> --projeto "Nome" --raiz-codigo app --modulos "app/*.py,app/*/" --github https://github.com/dono/repo --ramo main [--idioma en]`
   Não sobrescreve nada sem `--forcar`. Se o projeto já usa as portas 8790 ou 8791, passe `--porta-lite` e
   `--porta-explorador`; elas vão para o `lodemap.json`. Projeto com várias pastas de código na raiz (sem `app/` ou
   `src/`): `--raiz-codigo .` e um glob por pasta (`api/*.py,jobs/*.py,*.py`). Instale os testes só por este
   script: copiar `templates/tests/*.py` à mão deixa o marcador `{{ARQ_REL}}` no arquivo. Os globs de `modulos`
   definem o que precisa estar no modelo (`*.py` casa arquivos, `*/` casa pastas); dê glob próprio às portas de
   entrada (`app/routes/*.py`).
   - **Raiz do código.** Sem `--raiz-codigo`, o script usa a primeira de `app/`, `src/`, `lib/`, `backend/` e
     `server/` que tem código. Se nenhuma tem e há código fora delas (Go, biblioteca com os arquivos na raiz), a
     raiz é a do repositório: `"raiz_codigo": ""` e globs sem prefixo (`**/*.go`).
   - **`"ignorar"`.** Lista de globs do `lodemap.json`: o candidato que casa algum não é módulo (teste que mora
     ao lado do código, exemplo, fixture). O script escreve o padrão da linguagem: Go `**/*_test.go`, `**/_*/**`
     e `**/testdata/**` (o que o `go build` ignora); JS/TS `**/*.test.*` e `**/*.spec.*`; Python `**/test_*.py`,
     `**/*_test.py` e `**/conftest.py`. `--ignorar "a,b"` troca a lista, `--ignorar ""` deixa vazia, e com
     `--modulos` explícito nada é ignorado sem `--ignorar`. Teste de cobertura, diff, gancho, esqueleto,
     inventário, qualidade e plano leem a mesma lista. Mapa antigo sem a chave continua como estava.
2. **Inventário** (`lodemap-inventario`): `python .../scripts/codegraph_ponte.py --inventario --arq <arq> --json <arq>/inventario-codegraph.json`
   (rascunho sem ler arquivos) e `python .../scripts/inventario.py --repo <raiz> --importadores --json <arq>/inventario.json`,
   completado pelo agente com pontos de entrada, rotas, serviços externos e configuração. Pronto quando cada módulo
   tem um destino anotado.
2b. **Esqueleto** (script, 0 tokens): `python .../scripts/esqueleto.py rascunho --arq <arq>`. Os passos 3 a 5
   preenchem o `decisoes-modelo.json`, em fases com agente novo.
3. **Containers e áreas** (fase A, `lodemap-modelador`): `containers` e `areas` no JSON; externos em
   `pessoas-externos.dsl`.
4. **Componentes por área** (fase B): `descrever.py` e depois um agente por container: nome, descrição, container,
   área e status de cada componente; `tags` extras (`Dados`, `Gate`, `Privacidade`...) e `propriedades`
   (`observabilidade`, `equipe`, `spec`, `nota`, `ramo`) quando houver. Ver `references/modelagem-c4.md`.
5. **Relações** (fase C): cada relação sugerida ganha `manter` e verbo depois de conferida no código; relações com
   pessoas e externos vão à mão em `model/relacoes.dsl`. Depois: `python .../scripts/esqueleto.py renderizar --arq
   <arq>` (recusa e lista o que faltar decidir; avisa se `relacoes.dsl` ainda tem as setas de exemplo do template).
6. **Fluxos** em `views/visoes.dsl`: um `dynamic` por fluxo que precisa ser entendido em ordem. Cada passo precisa de
   uma relação que exista no modelo; numa visão de container só entram componentes desse container.
7. **Status por componente** pela realidade do código: mesclado e testado = Pronto; existe mas falta meta, revisão
   ou merge = Em andamento; espera outra pessoa = Aguardando; só design = Planejado. Código em outro ramo:
   propriedade `ramo`.
7b. **Gate de qualidade** (seção abaixo): exporte (`python scripts/atualizar.py`), rode o `qualidade.py` e só siga
    com o modelo aprovado.
8. **Métricas** (`lodemap-metricas`) em `metricas/metricas.json`: só números e origem (arquivo, ramo, commit, campo),
   ligados por identificador aos componentes que medem. Nunca respostas, textos ou dados pessoais.
9. **Gerar** (`lodemap-gerador`): `python scripts/atualizar.py` (`--checkpoint "<rótulo>"` para registrar o marco;
   `--com-site` só se o dono quiser essa saída). Decisão nova vira ADR no formato único
   (`references/leitor-e-adr.md`).
10. **Testes** (`lodemap-verificador`, pela fila do projeto se houver): cobertura (módulo fora, caminho inexistente,
    exceção podre), métricas (fonte incompleta, componente inexistente, número que não bate no commit),
    `test_lodemap_diff.py`, ADRs (`test_adrs_formato.py`) e leitor (`test_leitor_gerador.py`: âncoras, links
    internos, zero requisição externa). Exceções da cobertura ficam em `EXCECOES`, sempre com motivo.
11. **Idioma:** com `"idioma": "en"`, nomes, descrições, notas e ADRs do modelo são escritos em inglês pelos agentes;
    as chaves canônicas (tags de status, campos do cabeçalho do ADR) continuam como estão.
12. **Checagem final** (`lodemap-verificador`):
    `python .../scripts/verificar.py --arq <raiz>/docs/architecture/structurizr --capturas <pasta> --qualidade`:
    `node --check` em `dados.js` e no script do `index.html`, explorador sem erro de JS, um fluxo tocado, o foco por
    `#identificador` e o **gate do `qualidade.py`** (falha se o modelo reprovar). Olhe as capturas antes de dizer
    pronto. Checklist do verificador, nesta ordem: cobertura (pytest), métricas, `test_lodemap_diff.py`,
    `qualidade.py` (`--qualidade`), `node --check`, navegador.
13. **Registrar e commitar:** uma linha no `docs/99-registro-de-atualizacoes.md`; commits em passos lógicos. Depois,
    a cada merge: `python scripts/lodemap_decidir.py` e só o que ele pedir (seção "Quando atualizar").

## Gate de qualidade

O modelador roda em Sonnet; a qualidade não pode depender do modelo. O `scripts/qualidade.py` mede o `workspace.json`
com uma rubrica objetiva de 14 critérios (sem LLM) e compara com a linha de base
(`references/baseline-qualidade.json`, medido no mapa público de exemplo do axios).

1. Depois do `lodemap-modelador`, exporte (`python scripts/atualizar.py`) e rode
   `python ~/.claude/skills/lodemap/scripts/qualidade.py --arq <arq> --listar-reprovados`
   (`--repo` e `--db` se o código ou o índice estiverem em outro lugar).
2. Se reprovar, devolva ao `lodemap-modelador` **só a lista `reprovados`** (componentes e relações que falham, mais as
   relações faltantes com a contagem de arestas), no máximo **2 rodadas**, e só com os componentes reprovados. Passe o
   caminho da saída, não o conteúdo do modelo.
3. Se depois de 2 rodadas ainda reprovar, vale a escalada única (seção "Stack de agentes"); se ela falhar, registre a
   pendência em `qualidade.pendencias` do `estado.json` e avise o dono; não finja que passou.

**Regra do gate:** total no máximo **10 pontos abaixo** do total da linha de base e **nenhum critério abaixo de 70%**
do valor dela (comparados só os critérios disponíveis nos dois lados; "n/d" fica fora da nota e do gate;
`observabilidade` conta no total, mas não tem piso próprio: uma biblioteca sem log tira 0 com o modelo certo).
Critérios, pesos e as notas da linha de base: `references/gate-qualidade.md`. Recalibrar a linha de base só com o OK
do dono (`--gravar-baseline`).

## Limites das medições

O gate mede propriedades estruturais, não garante que descrições e relações sejam verdadeiras. A cobertura depende
dos globs e das exceções escolhidas. A campanha de custo tem três rodadas por célula, quatro registros internos
ausentes e preços equivalentes de API, não fatura; seus resultados históricos não medem modelos novos. Ela não prova
ganho de entendimento humano nem economia de tokens com o mapa. Fontes e limites: `references/benchmark-e-custo.md`
e `experimentos/campanha-custo/RESULTADOS.md`.

## Quando atualizar

Atualizar a cada commit gasta à toa. No axios, o modelador custou US$ 0,45 para 3 módulos novos, e a maior parte foi
contexto escrito e relido (58 mil tokens escritos em cache, 830 mil relidos), que cada sessão paga de novo; regenerar
os arquivos versionados a cada commit só suja a árvore. Quanto se economiza juntando mudanças ainda não foi medido.
Por isso a primeira ação de qualquer pedido de atualização, e a única decisão do gancho, é de um script:

`python scripts/lodemap_decidir.py` (na pasta da arquitetura; zero token; `--resumo` dá uma linha)

Ele mede a dívida do mapa e devolve `acao`, `motivos`, `divida`, `lote` e `proximo`. Siga a `acao`:

| `acao` | Quando | Modelo |
|---|---|---|
| `nada` | nada mudou, ou mudou pouco e a cadência de commits ainda não venceu | não |
| `scripts` | mudou fonte da arquitetura ou o conjunto de módulos, ou venceu a cadência: `atualizar.py --incremental` | não |
| `adiar` | módulo novo dentro da tolerância: `lodemap_decidir.py --adiar` grava em `pendentes.json` (versionado, com data) | não |
| `descrever` | superfícies públicas mudadas passaram do limite: `descrever.py`, uma chamada | Haiku |
| `modelar` | módulo fora do modelo além da tolerância ou do prazo, caminho citado que sumiu, relações novas além do limite | Sonnet |
| `gerar` | ainda não há modelo: o fluxo completo | os dois |

- **Um lote por sessão.** Com `acao` de modelo, resolva na mesma sessão tudo o que vier em `lote` (módulos adiados,
  revisões e relações novas); nunca uma sessão por módulo.
- **Sem `acao` de modelo, nenhum agente roda.** Não chame o modelador "para garantir".
- **Pedido explícito do dono vence a política** ("atualize agora"): rode o lote inteiro e diga o que a política faria.
- **Número que falta é `null`.** Sem a pasta da skill ao alcance (`--skill` ou `LODEMAP_SKILL`), `revisoes` e
  `relacoes_novas` saem `null` com o motivo; não estime.
- A política mora em `"politica"` no `lodemap.json`. Padrões: `tolerancia_modulos` 0, `tolerancia_dias` 14,
  `revisoes_para_atualizar` 10, `relacoes_para_atualizar` 10, `commits_para_regenerar` 10.
- `tolerancia_modulos` 0 mantém o gate estrito: todo módulo novo reprova o teste na hora. Num repositório ativo, sugira
  3 a 5 ao dono; a escolha é dele, e fica escrita no `lodemap.json`.
- O teste de cobertura lê a mesma política: passa enquanto os módulos fora do modelo estiverem em `pendentes.json`,
  dentro do limite e do prazo; fora disso falha dizendo qual dos três casos. `--adiar` nunca renova a data de um
  módulo já adiado.

## Abrir e atualizar

- **Abrir:** `python scripts/ver_arquitetura.py` serve a pasta da arquitetura em `127.0.0.1` e abre o explorador
  (`--abrir leitor` abre a documentação; `--com-lite` sobe também o Lite; `--sem-navegador` só sobe os servidores).
  Portas e detalhes: `references/abrir-e-servir.md`. Quem subiu um servidor para conferir algo encerra o processo dele
  no fim, e só ele.
- **Checkpoint:** `atualizar.py --checkpoint "<rótulo>"` grava o rótulo no `estado.json`.
- **Incremental:** `atualizar.py --incremental` pergunta ao `lodemap_diff.py --relevante` se mudou código dos globs,
  DSL, métricas, ADRs ou documentos desde `ultimoCommit`; sem mudança, sai sem regenerar. `semComponente` vira aviso.
  O `lodemap_diff.py` só olha commits (use `--trabalho` para o que ainda não foi commitado).
- **Gancho do git, opt-in e nunca automático:** `python scripts/instalar_gancho.py --python <python> --ferramentas <pasta>`
  grava `post-commit` e `post-merge` (em `.git/hooks` ou no `core.hooksPath`), com a pasta de ferramentas fixada. O
  `post-merge` roda o `atualizar.py --incremental` em segundo plano quando há o que regenerar; o `post-commit`, só
  quando o `lodemap_decidir.py` responde `scripts` (nos outros casos anota a pendência no log). Com trava, sem
  bloquear o git, sem chamar modelo; o log fica em `.lodemap/ultimo-atualizar.log`. O gancho só executa scripts cujo hash foi aprovado na instalação. `--remover` tira
  só os ganchos da skill; gancho alheio não é sobrescrito sem `--forcar`. Quem instala é o dono do repositório, com o
  escopo `gancho` consentido.
- No Windows, `atualizar.ps1`, `ver-arquitetura.ps1` e `instalar-gancho.ps1` são invólucros finos dos scripts Python
  (`-Incremental`, `-Checkpoint`, `-ComSite`, `-ComLite`, ...).

## Convenções

- **Identificadores** (`!identifiers flat`): camelCase com prefixo da área (`nucRotas`, `memEsquecer`), únicos no
  workspace e estáveis (`explorador/index.html#<identificador>` e os links do leitor dependem deles).
- **`codigo`**: caminhos a partir da raiz do repositório, separados por vírgula; nome sem barra herda a pasta do
  anterior; parênteses são comentário; "/" no fim cobre a pasta. A raiz do código sozinha não conta para a cobertura.
- **Status:** a tag e a propriedade `status` mudam juntas, no mesmo commit que muda o código.
- **Tags de forma:** `Dados`, `Gate`, `Privacidade`, `Modelo`, `WebBrowser`, `Janela`, `Barramento`, `Externo`, `Nuvem`.
- **Contexto e Containers sem seta:** com `!impliedRelationships false`, as visões de panorama só têm setas se você
  declarar relações de `sistema` e de container no fim do `relacoes.dsl`.
- **Fora do git:** `workspace.json`, `.structurizr/` (inclui `export/`), `site/` e `.lodemap/`, menos
  `.lodemap/decisoes-modelo.json`, que é versionado: é dele que o `renderizar` escreve o DSL e é com a impressão
  digital guardada nele que o `rascunho` sabe o que mudou em outra máquina ou no CI.

## Leia quando precisar

| Arquivo em `references/` | Quando ler |
|---|---|
| `modelagem-c4.md` | ao cortar componentes, nomear relações, desenhar visões e fluxos, escolher status e tags, formatar métricas |
| `exemplos-estilo.md` | antes de escrever descrições e relações (o modelador lê sempre) |
| `scripts.md` | para saber o que cada script da skill e do projeto faz e quais opções aceita |
| `arestas-codigo.md` | quando o recall ou a precisão das relações parecer estranho, ou a linguagem não for Python/JS |
| `gate-qualidade.md` | quando o gate reprovar e for preciso entender um critério ou o peso dele |
| `estado-json.md` | ao criar ou ler o `.lodemap/estado.json` |
| `leitor-e-adr.md` | ao criar ou migrar ADRs, organizar documentos ou mexer na barra de topo |
| `abrir-e-servir.md` | portas, opções do `ver_arquitetura.py` e o Structurizr Lite |
| `armadilhas.md` | quando um passo falhar de um jeito estranho (PowerShell, Lite, Graphviz, ganchos, nome antigo do projeto) |
| `rota-enxuta.md`, `digital-semantica.md`, `benchmark-e-custo.md`, `precisao-ast.md` | medições: de onde vêm os números de custo, qualidade e precisão |
