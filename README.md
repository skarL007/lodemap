# Lodemap

**Veja como seu sistema funciona e como sua arquitetura vem mudando. Fluxos, linha do tempo do Git e evidências
locais, em um mapa que vive no seu repositório.**

O Lodemap oferece observabilidade da arquitetura para pessoas: quem conversa com quem, por onde passa cada fluxo,
o que mudou entre versões do mapa e quais evidências locais estão ligadas a cada componente. O modelo C4 em
[Structurizr DSL](https://docs.structurizr.com/dsl) fica ao lado do código; scripts geram o explorador interativo,
o leitor de documentação e decisões (ADRs), as métricas e as comparações históricas.

O teste de cobertura é a garantia estrutural por trás do acompanhamento: detecta módulos fora do modelo e caminhos
que sumiram, conforme os globs e as exceções do projeto. Ele não garante a verdade de descrições, relações ou status.
O Lodemap não coleta telemetria de execução.

[![O explorador do Lodemap no mapa do axios, rodando o fluxo do ciclo de vida de uma requisição](assets/explorer-axios.webp)](https://skarl007.github.io/lodemap/demo/)

**Demonstração ao vivo:** o [explorador](https://skarl007.github.io/lodemap/demo/explorador/) e o
[leitor de docs](https://skarl007.github.io/lodemap/demo/leitor/) de um mapa do [axios](https://github.com/axios/axios)
(72 componentes, 7 fluxos animados) que acompanhou cinco releases reais, da v1.17.0 à v1.21.1: cada release virou uma
versão do mapa, comparável na linha do tempo. Páginas estáticas, sem servidor, sem requisição externa.

**O mapa original, neste repositório:** [`exemplos/axios/`](exemplos/axios/) guarda as fontes do primeiro mapa do
axios, feito na v1.20.0 e atualizado para a v1.21.1, com 6 fluxos (DSL, docs, ADRs, métricas, `lodemap.json`), cerca de
300 KB, sem página gerada e sem caminho privado. O
`tests/test_exemplo_axios.py` o regenera de ponta a ponta a partir de uma cópia limpa do axios v1.21.1 com o
Structurizr CLI de verdade, e depois roda os testes que o mapa entrega e o gate de qualidade. O CI roda esse teste
em Linux e macOS. Para regenerar você mesmo:

```bash
bash .circleci/preparar_pipeline.sh   # Structurizr CLI (sha256 checked) and axios v1.21.1 into ~/axios
LODEMAP_EXEMPLO_AXIOS=~/axios python -m pytest -q tests/test_exemplo_axios.py
```

## Acompanhar a arquitetura

- **Fluxos:** percorra os passos modelados e veja os componentes e relações envolvidos. São fluxos descritos no
  modelo, não rastros de requisições em produção.
- **Linha do tempo:** abra a visão no explorador, escolha uma versão e compare as entradas, saídas e alterações com
  a versão-base registrada. O grafo histórico, as visões e o histórico de cada componente vêm dos snapshots do Git.
  “Tocar evolução” percorre as versões disponíveis; o histórico só existe onde o mapa foi versionado.
- **Saúde:** a cor mostra se testes encontrados referenciam o código, se nenhuma referência foi encontrada ou se
  faltam dados. O inspetor apresenta cobertura por arquivo, atividade no Git e falhas de JUnit quando fornecidas.
  “Pronto” sem referência estática de teste gera um alerta para revisão, não um diagnóstico de defeito.
- **Proveniência:** confira a data e o commit da evidência. A árvore de trabalho não é verificada; um commit igual
  ao do mapa não prova que testes ou relatórios vieram daquela revisão. A linha do tempo não aplica evidências atuais
  aos snapshots históricos.

Os dois coletores rodam localmente sem chamar modelo. A partir da raiz do checkout do Lodemap, use os caminhos do
seu projeto:

```bash
python scripts/linha_do_tempo.py --mapa /caminho/projeto/docs/architecture/structurizr --resumo
python scripts/evidencias.py --repositorio /caminho/projeto --mapa /caminho/projeto/docs/architecture/structurizr --json
```

O primeiro grava `explorador/linha-do-tempo.js` e `.json`; o segundo grava `explorador/evidencias.js` e, com
`--json`, `.json`. Relatórios opcionais entram com `--cobertura coverage.xml` (ou `lcov.info`) e
`--junit junit.xml`, relativos à raiz do projeto. Uma referência de teste é estática, não prova execução; o JUnit só
associa casos com atributo `file`. Os comandos, a atualização da interface e os backups estão em
[references/scripts.md](references/scripts.md).

A demo pública acima é o replay das cinco releases, refeito a partir da v1.17.0; o mapa original de `exemplos/axios/`
segue como teste de ponta a ponta no CI. O ganho de entendimento humano ainda não foi medido: o estudo está
pré-registrado em [`experimentos/estudo-pessoas/PROTOCOLO.md`](experimentos/estudo-pessoas/PROTOCOLO.md) e a coleta não
começou.

### O gate, numa release real

O mapa foi feito no axios v1.20.0. Depois o upstream lançou a v1.21.1 (99 commits, 27 arquivos alterados em `lib/`,
três deles novos). Depois de mesclar a tag, o teste de cobertura falhou e apontou os três arquivos. A gravação abaixo
mostra a saída real de cada comando (caminhos longos cortados).

![Terminal: o teste de cobertura falha depois do merge, a atualização roda, o teste passa](assets/gate-demo.gif)

| Passo | O que rodou | Resultado |
|---|---|---|
| `pytest tests/test_arquitetura_cobertura.py` | script | falha: 3 módulos fora do modelo |
| `esqueleto.py rascunho` | script, 0 tokens | 3 módulos novos, 16 dos 24 arquivos alterados com superfície pública diferente, 12 relações novas |
| `descrever.py` | uma chamada ao Haiku, 26.029 tokens, 34 s (a repetição na gravação: 26.660 tokens, 37 s) | descreve os 3 módulos novos e revisa os 16; 15 frases mantidas palavra por palavra, 1 alterada (o helper de cookies ganhou um caminho pela Cookie Store API); a repetição manteve 14 |
| `lodemap-modelador` | Sonnet, 19 chamadas, 129 s | contêiner e status dos 3 componentes novos, verbos das 12 relações |
| `atualizar.py --incremental` | scripts, 17 s | exportação do DSL, explorador, leitor, docs derivados |
| `pytest tests/test_arquitetura_cobertura.py` | script | passa |

A sessão orquestradora não entra na conta. A atualização foi repetida depois, duas vezes, a partir do mesmo commit:
a etapa de scripts deu o mesmo lote, a etapa do modelo fez 13 e 9 chamadas, e o mapa saiu
com os mesmos 72 componentes e 188 relações. Um dos três módulos novos caiu numa área diferente na primeira
execução, e a redação de verbos e frases varia entre execuções.

### Quando o mapa atualiza

Atualizar a cada commit gasta dinheiro e atenção: cada sessão do modelo paga o contexto de novo, e regenerar
arquivos versionados depois de cada commit suja a árvore sem mudar o mapa. Um script decide, por zero tokens:

```bash
python docs/architecture/structurizr/scripts/lodemap_decidir.py --resumo
```

| Ele responde | Quando | Modelo |
|---|---|---|
| `nada` | nada relevante mudou, ou mudou pouco desde a última execução | não |
| `scripts` | as fontes do modelo ou o conjunto de módulos mudaram, ou passaram 10 commits | não |
| `adiar` | um módulo novo pode esperar: ele vai para `pendentes.json`, com a data, no seu commit | não |
| `descrever` | 10 ou mais módulos mudaram a superfície pública | uma chamada ao Haiku |
| `modelar` | módulos esperaram além do limite ou do prazo, um caminho citado pelo modelo sumiu, ou 10 ou mais relações de import novas | uma sessão do Sonnet para tudo o que está pendente |

O gate é estrito por padrão: qualquer módulo novo faz o teste de cobertura falhar. Para deixar a estrutura esperar,
dê uma tolerância no `lodemap.json`:

```json
"politica": {"tolerancia_modulos": 3, "tolerancia_dias": 14}
```

Assim, até 3 módulos podem esperar até 14 dias, cada um listado por nome e data num arquivo versionado que um
revisor pode ler. O quarto módulo, ou o dia 15, faz o teste falhar de novo, e rodar o comando duas vezes não
estende um prazo. Quando o modelo finalmente roda, trata o lote inteiro numa só sessão. O git hook opcional segue a
mesma resposta e nunca chama um modelo.

Reproduzido no merge do axios acima, por zero tokens: com a política padrão o script responde `modelar` e nomeia os 3
arquivos; com tolerância de 3 ele responde `adiar`, o teste passa quando os 3 estão listados, e com a skill ao
alcance ainda responde `modelar`, porque o merge também trouxe 12 relações de import novas (limite 10). O lote que
ele relata, 3 módulos, 16 revisões e 12 relações, é exatamente o que a atualização real tratou. Quanto o agrupamento
economiza ainda não foi medido.

## O que muda

- **Cobertura estrutural verificável.** O `tests/test_arquitetura_cobertura.py` é instalado no seu projeto e falha quando um
  módulo que casa com seus globs não tem componente, quando um componente aponta para um caminho que não existe mais,
  ou quando uma exceção não tem motivo. Coloque-o no CI e o mapa não fica para trás em silêncio.
- **Atualizar não custa chamada de modelo.** O `atualizar.py --incremental` regenera todas as saídas com scripts. Um
  modelo só é consultado de novo para os módulos cuja *superfície pública* mudou (docstring, imports, assinaturas,
  símbolos públicos). Em cinco pares de releases do [rich](https://github.com/Textualize/rich), 78 arquivos alterados
  precisaram de 29 revisões (63% a menos).
- **Custo medido, publicado com as ressalvas.** Todo número abaixo nomeia o repositório, o modelo e o que ficou de
  fora. Nada aqui é projeção, a menos que diga que é.

O que o Lodemap **não** afirma: que o mapa deixa um agente de código mais barato. Isso foi medido e não deixa. Num
experimento pré-registrado (96 execuções, Sonnet, 16 perguntas de navegação no chi e no axios), o agente com o mapa
gastou os mesmos tokens que o agente sem ele (razão mediana 0,99). As respostas não foram piores (recall 0,991 contra
0,977) e foram um pouco melhores em 3 perguntas do tipo "quem depende de X"; esse ganho não é significativo. Veja
[experimentos/com-sem-mapa](experimentos/com-sem-mapa/RESULTADOS.md).

## Instalação

O instalador abaixo empacota a integração com [Claude Code](https://code.claude.com): skill, agentes e aviso opcional
em `~/.claude/`. Os scripts também podem ser executados de um checkout no Codex; isso não instala uma integração
nativa completa nem altera os hooks do Codex. Para decisões com modelos nativos, veja a seção de uso abaixo.

Exige Python 3.11+ e git. No Debian/Ubuntu o interpretador é `python3`.

```bash
git clone https://github.com/skarL007/lodemap && cd lodemap
python -m lodemap install --profile padrao            # dry run: prints every change, writes nothing
python -m lodemap install --profile padrao --apply    # applies, with backups and a manifest
python -m lodemap doctor                              # checks Python, git, Java, Structurizr CLI, Graphviz, claude
```

Desfaça com `python -m lodemap revert`: ele restaura os bytes exatos de cada arquivo que a instalação tocou, da
instalação mais recente para a mais antiga. É tudo ou nada: se um arquivo tocado mudou depois da instalação, ele se
recusa e nomeia o arquivo.

| Perfil | O que instala |
|---|---|
| `minimo` | A skill (um link de `~/.claude/skills/lodemap` para esta pasta) e seis agentes `lodemap-*` em `~/.claude/agents/`. |
| `padrao` | O acima, mais um aviso único (hook `SessionStart`) em repositórios que não têm mapa. |

O instalador nunca sobrescreve um arquivo, chave ou link que pertença a outra pessoa, a menos que você passe
`--force`, e nunca mexe nos hooks de outras ferramentas. O `python -m lodemap status` mostra o que está instalado.

Gerar um mapa também exige Java 21, o [Structurizr CLI](https://docs.structurizr.com/cli) e o Graphviz. O `doctor`
diz qual deles está faltando e onde procurou.

## Uso

**No Codex, com modelos nativos:** execute inventário e esqueleto por script, preencha as decisões em
`.lodemap/decisoes-modelo.json` no agente da sessão e rode `esqueleto.py renderizar` e o pipeline. Confira cada
descrição e relação no código. A seleção de modelo e esforço pertence à sessão; a tabela de Claude Code no
[SKILL.md](SKILL.md) descreve a integração empacotada. O helper opcional `descrever.py` ainda chama `claude -p`;
não é uma rota nativa do Codex. Uma execução restrita a modelos nativos deve preencher as descrições no JSON e
pular esse helper, sem chamar CLI de modelo externa.

No Claude Code, dentro do seu repositório, peça o mapa ("lodemap", "mapa de arquitetura", "modelo C4 deste
projeto"). A skill sempre começa com um plano que não gasta tokens e espera o seu OK:

```bash
python -m lodemap plan --repo .        # modules found, estimated cost and time, files that would be written
python -m lodemap consent --repo . --scopes gerar,modelo --monthly-budget 5
python -m lodemap revoke --repo .
```

Os nomes de comando e opções em português continuam funcionando (`instalar`, `reverter`, `plano`, `consentir`,
`revogar`, `verificar`, `diagnostico`; `--perfil`, `--aplicar`, `--sem`, `--com`, `--forcar`, `--manifesto`,
`--escopos`, `--orcamento-mensal`, `--escopo`, `--custo`, `--todos`), então scripts existentes seguem rodando. Os
valores de escopo (`gerar`, `gancho`, `modelo`) são os mesmos nos dois idiomas.

Depois da primeira geração:

```bash
python scripts/atualizar.py --incremental   # regenerate only if something relevant changed; no model call
python scripts/ver_arquitetura.py           # serve on 127.0.0.1 and open the explorer
python scripts/instalar_gancho.py           # optional: update on every commit and merge
```

A partir de um mapa existente, os comandos acima rodam na pasta da arquitetura. Para migrar a interface, primeiro
atualize a instalação da skill ou o checkout do Lodemap. Preserve `<arq>/scripts/atualizar.py` em backup exclusivo
(`atualizar.py.lodemap-bak`, depois `.1`, `.2`, etc., sem sobrescrever backups) e compare-o com
`templates/structurizr/scripts/atualizar.py` dessa fonte confiável atual. Se o script local não tiver personalizações,
copie o atual para `<arq>/scripts/atualizar.py`; se tiver, incorpore a atualização manualmente preservando-as.
`--template` não atualiza o próprio script, e `novo_mapa.py` preserva scripts existentes por padrão. Confirme que o
script do mapa já mostra `--atualizar-interface` em `python scripts/atualizar.py --help`. Só então, na pasta da arquitetura:

```bash
python scripts/atualizar.py --atualizar-interface --template /caminho/lodemap/templates/structurizr
```

Execute o script copiado no mapa: ele determina a raiz pela própria localização. O procedimento completo está em
[Migrar a interface de mapas existentes](references/scripts.md#migrar-a-interface-de-mapas-existentes).
A opção migra o HTML e os JS fixos para o template indicado, com backups exclusivos `.lodemap-bak`,
`.lodemap-bak.1`, etc. Revise também as personalizações desses arquivos. Sem a opção, arquivos fixos existentes são
preservados. O pipeline também regenera linha do tempo e evidências quando encontra os coletores no checkout da
skill; falhas nessas etapas geram
avisos, portanto confira as saídas. A coleta automática não recebe relatórios opcionais de cobertura ou JUnit;
rode `evidencias.py` diretamente para incluí-los.

## Como funciona

O fluxo abaixo descreve a integração empacotada com Claude Code. No Codex, a edição das decisões em JSON substitui
as chamadas de modelo externas; os scripts de inventário, renderização e validação continuam os mesmos.

1. **Inventário e esqueleto, por script.** `inventario.py` e `codegraph_ponte.py` listam os módulos e as arestas de
   import entre eles. `esqueleto.py rascunho` escreve um JSON com um componente sugerido por módulo e uma relação
   sugerida por par com arestas, deixando as decisões em branco.
2. **Descrições, por uma chamada enxuta.** `descrever.py` preenche nome, descrição de uma frase e área com uma única
   chamada `claude -p` (Haiku, sem ferramentas, saída em JSON Schema, a área restrita às áreas já decididas). Um
   gate determinístico rejeita uma frase que:
   - é genérica;
   - não tem evidência literal;
   - cita código que o módulo não contém.

   Ele repete só essas, uma vez. Uma segunda chamada ao Haiku então lê o código de cada módulo e corrige ou rejeita
   as frases falsas (`--sem-conferir` pula essa etapa; `--auditar` confere um mapa existente sem alterá-lo).
3. **Decisões, pelo modelador.** O agente `lodemap-modelador` decide contêineres, áreas, status e quais relações
   sugeridas são reais, em fases separadas, cada uma com um agente novo, para o contexto ficar pequeno.
4. **Todo o resto, por script.** `esqueleto.py renderizar` escreve o DSL e as visões estáticas; o `atualizar.py`
   exporta o workspace e monta o explorador, o leitor e os documentos derivados.
5. **Dois portões.** O teste de cobertura (estrutura) e o `qualidade.py`, uma rubrica de 14 critérios sem modelo no
   processo (qualidade das descrições, relações respaldadas por arestas de código, componentes órfãos e assim por
   diante).

Seis agentes, uma tarefa cada: `lodemap-inventario`, `lodemap-modelador` (o único que decide arquitetura),
`lodemap-metricas`, `lodemap-gerador`, `lodemap-verificador` e `lodemap-revisor-visual`. As regras de roteamento,
ordem e gravação estão no [SKILL.md](SKILL.md).

## Medições

As medições desta seção são históricas, com os modelos e as condições declarados em cada fonte. Não medem o custo
da execução atual com modelos nativos do Codex. Reduzir revisões de arquivos não demonstra economia de tokens;
o experimento com e sem mapa abaixo não encontrou essa economia.

### Chamadas e tempo de um mapa completo

Chamadas e tokens lidos das transcrições dos subagentes (uso deduplicado por id de mensagem). As execuções usaram uma
assinatura do Claude Code.

| Execução | Modelo | Chamadas | Tempo |
|---|---|---:|---:|
| Mapa completo, repositório de 63 módulos, um agente | Sonnet | 93 | 25 min |
| Mesmo repositório e commit, esqueleto por script + agente novo por fase | Sonnet (+ verificador Haiku) | 98 | 14 min |
| Atualização num commit sem mudança estrutural | só scripts | 0 | 11–17 s |
| Mapa completo do axios v1.20.0 (69 módulos), esqueleto + fases + descrições enxutas | Sonnet (+ uma chamada ao Haiku) | 51 | 10 min |
| Atualização desse mapa para o axios v1.21.1 (3 módulos novos, 16 revisões, 12 relações novas), três execuções | Sonnet (+ uma chamada ao Haiku) | 20, 14, 10 | 1 a 3 min |
| Mapa completo do go-chi/chi v5.4.0 (Go, 35 módulos), com cada descrição conferida contra o código | Sonnet (+ uma chamada ao Haiku) | 67 | 9 min |
| Atualização desse mapa para o chi v5.5.0 (1 módulo novo, 1 revisão) | Sonnet (+ uma chamada ao Haiku) | 8 | 1 min |

As linhas do axios e do chi são de repositórios públicos e podem ser refeitas.
O tempo é tempo de modelo; os scripts somam menos de um minuto. A menor atualização ainda paga o contexto de uma
sessão do Sonnet: cerca de 37.000 tokens de escrita de cache para decidir um módulo no chi.

Não incluído: a sessão orquestradora que despachou os agentes. As duas linhas de mapa completo são o mesmo
repositório, mas não um teste controlado (a primeira execução também corrigiu seis defeitos da skill). O `plano`
escala a execução do Sonnet linearmente pelo número de módulos, o que é uma suposição. Método e números brutos:
[references/benchmark-e-custo.md](references/benchmark-e-custo.md).

### Rota enxuta de descrição

Mesma faixa de qualidade de um subagente, com menos tokens, em dois repositórios públicos:

| Repositório | Módulos | Rota enxuta (Haiku medium) | Subagente |
|---|---:|---|---|
| [rich](https://github.com/Textualize/rich) (Python) | 76 | nota 96,9 (intervalo de 95% 92,7–98,7), 64.670 tokens | nota 96,9, 129.385 tokens |
| [axios](https://github.com/axios/axios) (JavaScript) | 72 | área concorda com a referência em 0,90, 70.178 tokens, 105 s | 98.869 tokens, 240 s |

A referência é uma execução do Sonnet, não um gabarito humano. Uma repetição no rich deu 95,3. Detalhes e as variantes
que perderam: [references/rota-enxuta.md](references/rota-enxuta.md).

### Arestas de import sem índice

Sem um índice do CodeGraph, as relações são sugeridas a partir dos imports lidos por um parser embutido (Python,
JS/TS, Go, Rust, Java, Kotlin, C#, C/C++). Em Go, onde os arquivos de um pacote se enxergam sem import, a aresta vem
do símbolo usado: no go-chi/chi ele achou 31 arestas, as 31 confirmadas no código, e perdeu 3 reais (uso de método
e de interface). Precisão por linguagem: [references/precisao-ast.md](references/precisao-ast.md).
Arestas sugeridas nunca são escritas no modelo automaticamente; o modelador confirma cada uma no código.

## Idioma

O lançamento é em português. Páginas geradas, docs, rótulos do DSL, visões e o terminal (mensagens e `--help`) saem
em português. O inglês existe, mas fica desligado por padrão: só aparece com `LODEMAP_IDIOMA=en` ou com
`"idioma": "en"` no `lodemap.json` (ou `novo_mapa.py --idioma en`). Os prompts da skill estão em português do Brasil.

A saída do terminal vale para a CLI inteira, os `scripts/` e os scripts copiados para o seu repositório:
`LODEMAP_IDIOMA=pt|en` vence; senão vale o `"idioma"` do `lodemap.json` do mapa (quando o comando aponta para um com
`--repo` / `--arq`); senão, português. Nomes de comando e opções existem nos dois idiomas, e o ativo vem primeiro. O
teste de cobertura e o pipeline de atualização (`draft`/`rascunho`, `render`/`renderizar`, `descrever.py --resumo`,
`atualizar.py`) imprimem no idioma do mapa.

## Limites

- **Observabilidade da arquitetura, sem telemetria de execução.** Fluxos e status são decisões do modelo. Testes
  referenciados, cobertura, Git e JUnit ajudam a revisão, mas não certificam prontidão ou comportamento em produção.
  Falta de relatório aparece como ausência ou dado desconhecido. A árvore de trabalho da coleta não é verificada.
- **Entendimento humano ainda não medido.** Não há resultado de estudo com pessoas que sustente ganho de compreensão
  ou de velocidade. O replay ampliado do axios continua em revisão.
- **O mapa não deixa um agente mais barato.**
  - **O que foi medido:** Sonnet com Read, Grep e Glob, respondendo 16 perguntas de navegação de código em dois
    repositórios de 35 e 69 módulos. Com o mapa e um ponteiro para ele, o agente gastou os mesmos tokens que sem o
    mapa, e a precisão não piorou ([experimentos/com-sem-mapa](experimentos/com-sem-mapa/RESULTADOS.md)).
  - **O que não foi medido:** tarefas de edição, outros modelos e repositórios grandes.
  - **Um estudo relacionado:** uma pesquisa sobre arquivos de contexto de repositório
    ([arXiv 2602.11988](https://arxiv.org/abs/2602.11988)) concluiu que eles não aumentam, em geral, o sucesso nas
    tarefas. Ela não testou mapas C4.
  - **O que o Lodemap oferece:** documentação que se mantém atual e um gate que falha quando o modelo se afasta
    do código.
- **Rodado de ponta a ponta no Windows e no Linux; no macOS, não.** No Linux (WSL Ubuntu 24.04, Python 3.12, Java 21,
  o Structurizr CLI de verdade) a suíte de testes passou naquela rodada histórica, a regeneração completa levou 9 s no
  mapa do axios e 5 s no do chi, os docs e inventários gerados do axios saíram byte a byte iguais aos do Windows
  (só os carimbos de data diferem), o gate de qualidade deu as mesmas notas, e o git hook real regenerou num commit
  de arquitetura e ficou quieto num commit só de código. As fases do modelo (agentes) rodaram só no Windows. O macOS
  tem ramos cobertos por testes que simulam a plataforma e nada além disso.
- **Custo:** a campanha mediu 18 gerações em três repositórios públicos, com três rodadas por modelo e repositório.
  Valores em dinheiro são equivalentes de API, não fatura, e não medem modelos novos. Monorepos e repositórios
  muito grandes não foram medidos. Veja [a campanha](experimentos/campanha-custo/RESULTADOS.md).
- **Descrições escritas pela rota enxuta ainda podem estar erradas.**
  - **Antes da conferência de veracidade:** um juiz Sonnet lendo o código achou 15 frases falsas em 108 (13,9%) no
    chi e no axios.
  - **Com a conferência:** 5 de 213 em quatro execuções (2,3%).
  - **Custo:** a conferência custa cerca de 3,7 vezes os tokens da passada de descrição, cerca de 325.000 tokens para
    os dois repositórios.
  - O modelador ainda confirma as frases na fase B.
  - Os detalhes estão em [`experimentos/descricoes/RESULTADOS.md`](experimentos/descricoes/RESULTADOS.md).
- **A impressão digital não pega comportamento que muda sem mudar a superfície**: 3 de 178 arquivos alterados nos
  dois repositórios auditados. Veja [references/digital-semantica.md](references/digital-semantica.md).
- O gate de qualidade compara com o `references/baseline-qualidade.json`, o mapa público de exemplo do axios. No
  seu projeto, leia a nota absoluta e as notas por critério, ou grave seu próprio baseline com `--gravar-baseline`.
- O consentimento é um registro que a skill e seus agentes leem e seguem. Nenhum hook o impõe, e o teto mensal é
  conferido por execução, não somado entre execuções.
- Com os globs padrão, um `__init__.py` vazio conta como módulo e precisa de um componente ou de uma entrada em
  `EXCECOES`.
- Arquivos que ficam ao lado do código e não são módulos (testes, exemplos, fixtures) ficam de fora pela lista
  `"ignorar"` do `lodemap.json`. Um mapa novo recebe os padrões da sua linguagem (Go: `**/*_test.go`,
  `**/_*/**`, `**/testdata/**`; JS/TS: `**/*.test.*`, `**/*.spec.*`; Python: `**/test_*.py`, `**/*_test.py`,
  `**/conftest.py`); um mapa feito antes de a lista existir não tem nenhuma até você acrescentar.
- O `--incremental` compara commits: um módulo novo ainda não commitado aparece depois do commit (ou rode
  `lodemap_diff.py --trabalho`).
- O leitor desenha o Mermaid offline com um build embutido; `mindmap`, `architecture` e matemática carregam um build
  maior só nas páginas que precisam.

## Privacidade e segurança

- Os coletores de linha do tempo e evidências e os geradores rodam localmente, sem chamada de modelo. Na integração
  Claude Code, o helper `descrever.py` envia contexto pelo seu próprio Claude Code à Anthropic. No Codex, os arquivos
  lidos pelo agente seguem a sessão e o provedor configurados. O visualizador (`ver_arquitetura.py`) serve as páginas
  só em `127.0.0.1`.
- As páginas geradas não carregam nada de uma CDN; as bibliotecas embutidas estão listadas em
  [THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md).
- O git hook opcional só roda os scripts do repositório enquanto o hash deles bate com o aprovado na instalação.
  Depois de um pull que os altere, ele registra um aviso e não roda nada até você aprovar de novo.
- O instalador faz backup de cada arquivo antes de escrever. Os backups ficam em `~/.claude/.lodemap-instalador/`.
- Para relatar uma vulnerabilidade: [SECURITY.md](SECURITY.md).

## Estrutura do repositório

```
SKILL.md       instruções operacionais e limites das integrações
references/    read on demand: modeling guide, gate criteria, pitfalls, measurements
agents/        the six lodemap-* agents
lodemap/       CLI: python -m lodemap (install, revert, status, doctor, plan, consent, revoke, check)
scripts/       inventory, skeleton, lean descriptions, quality gate, bridges
templates/     what a new map copies into your repository (DSL, explorer, reader, scripts, tests)
hooks/         the one-time hint hook
tests/         run with: python -m pytest
```

## Licença

[MIT](LICENSE). Contribuições: [CONTRIBUTING.md](CONTRIBUTING.md). Mudanças: [CHANGELOG.md](CHANGELOG.md).
