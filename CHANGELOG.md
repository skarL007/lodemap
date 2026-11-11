# Changelog

Todas as mudanças relevantes do Lodemap. As datas são de quando a mudança entrou na `main`.

## Unreleased

- **Explorador: polimento 4 (celular, foco e linha do tempo):**
  - Fluxo longo (3 ou mais passos) no celular vira uma coluna única, no zoom legível, com o passo 1 à vista e livre do
    título e da Legenda; o resto se alcança arrastando.
  - Ligação cuja reta passaria por trás de um nó que não é ponta dela ganha uma curva que o contorna (mapa principal e
    linha do tempo). Na demo do axios, no celular: Containers 4 para 2 interseções aresta x nó, fluxo de 14 passos 0,
    foco 10 para 8; no desktop, foco 1 para 0. Ligações longas com os dois lados bloqueados ainda podem cruzar um nó.
  - Com um nó em foco, o celular enquadra o nó e o máximo de vizinhos inteiros na faixa acima da folha; no desktop o
    rótulo das ligações em foco fica em 12 px (nunca abaixo de 10 px na tela).
  - Linha do tempo: grafo com dagre, nós retangulares do tamanho do rótulo, direção LR ou TB conforme o encaixe, zoom
    mínimo legível (0,85) com o mesmo aviso do mapa e reenquadre quando o painel muda de tamanho.
  - Toque e janela estreita: "Ctrl K" some em toque ou até 720 px; a Legenda e os itens da navegação do leitor têm
    44 px de altura no toque.
  - Testes de interface cobrem cada um desses comportamentos (zoom, fonte, caixas, interseções); `?lang=en` com o
    painel da linha do tempo aberto não mostra mais texto em português.
- **Observabilidade da arquitetura para pessoas:** apresentação centrada em fluxos, evolução do mapa no Git e
  evidências locais por componente; o gate aparece como verificação estrutural, sem promessa de verdade semântica.
- **Linha do tempo:** snapshots históricos no explorador, comparação com a versão-base, entradas, saídas e
  alterações de componentes e relações, visões históricas, reprodução da evolução e histórico do componente.
  O coletor lê o Git sem trocar de ramo e grava `linha-do-tempo.js` e `.json`; o replay ampliado do axios segue em
  revisão, sem anúncio de cinco releases concluídas.
- **Evidências locais e Saúde:** referências estáticas de testes, cobertura por arquivo, atividade no Git e JUnit
  opcional. Fontes carregam data e commit da base, com árvore de trabalho não verificada. JUnit exige atributo
  `file`; referência estática não comprova execução nem prontidão. Evidências atuais não são aplicadas ao histórico.
- **Migração de interface:** `atualizar.py --atualizar-interface` atualiza HTML e JS fixos a partir do template,
  preservando backups exclusivos `.lodemap-bak` e sufixos numerados. Pipeline tenta gerar linha do tempo e evidências;
  falhas dessas etapas apenas avisam. Relatórios opcionais são fornecidos diretamente ao coletor de evidências.
- **Uso no Codex documentado:** agentes nativos podem preencher decisões JSON e executar os scripts. Instalador,
  agentes empacotados e helper opcional `descrever.py` continuam ligados ao Claude Code; não há port completo.
  Custos históricos não medem essa rota; ganho de entendimento humano continua não medido.
- **Linha de base pública:** gate calibrado no exemplo do axios; método e resultados em `references/gate-qualidade.md`.
- **Campanha de custo:** 18 rodadas em três repositórios públicos, com limites e fontes em `experimentos/campanha-custo/RESULTADOS.md`.
- **Lançamento em português:** landing, explorador, leitor, mapa de exemplo e README em português; o inglês fica
  desligado por padrão.
- **Conferência de veracidade das descrições:** o `descrever.py` agora confere cada frase antes de escrevê-la.
  - O modelo cita evidência literal do cartão do módulo.
  - O gate rejeita uma frase cuja evidência não é encontrada, ou que cita código que o módulo não contém.
  - Uma segunda chamada ao Haiku lê o código do módulo e corrige ou rejeita as frases falsas.
  - Os prompts deixam de pedir "o porquê" a menos que o código o declare.
  - Novas opções: `--conferir <modelo>`, `--sem-conferir` e `--auditar`, que confere um mapa existente só para
    leitura e sai com 3 quando encontra uma frase falsa.
  - Medido com um juiz Sonnet no chi e no axios: as frases falsas caíram de 15 em 108 para 5 em 213, a cerca de 3,7
    vezes os tokens. Veja `experimentos/descricoes/`.
- **Experimento: o mapa deixa um agente mais barato?** Pré-registrado, 16 tarefas, 2 repositórios, 3 repetições,
  Sonnet com e sem o mapa.
  - Tokens: sem diferença (razão mediana 0,99).
  - Precisão: não piorou (recall 0,991 contra 0,977).
  - O README agora diz isso. Veja `experimentos/com-sem-mapa/`.
- **Terminal em dois idiomas:** a CLI `python -m lodemap`, os `scripts/` e os scripts copiados para um repositório
  (`templates/structurizr/scripts/`) imprimem as mensagens e o `--help` em português ou em inglês. O português é o
  padrão; o inglês só aparece com `LODEMAP_IDIOMA=en` ou com `"idioma": "en"` no mapa. Uma regra só, em
  `lodemap/idioma.py`: `LODEMAP_IDIOMA=pt|en` vence; senão vale o `"idioma"` do `lodemap.json` quando o comando aponta
  para um mapa; senão, português. O locale do sistema não decide mais. Comandos e opções ganharam nomes em inglês
  (`install`, `revert`, `plan`, `consent`, `revoke`, `check`; `--profile`, `--apply`, `--without`, `--with`,
  `--force`, `--scopes`, `--monthly-budget`, `--scope`, `--cost`, `--all`, `--manifest`, `--source`, ...) e os
  portugueses continuam funcionando como apelidos. Os dados (chaves JSON, valores de escopo `gerar`/`gancho`/`modelo`,
  arquivos) não mudam. Os testes definem `LODEMAP_IDIOMA` explicitamente; o `tests/conftest.py` o deixa em `pt` por
  padrão.
- **Mapa de exemplo no repositório:** `exemplos/axios/` guarda as fontes do mapa do axios v1.21.1 (em português, 72
  componentes), sem página gerada e sem caminho privado. O `tests/test_exemplo_axios.py` o regenera de ponta a ponta
  a partir de uma cópia limpa do axios com o Structurizr CLI de verdade, roda os testes que ele entrega e o gate de
  qualidade; é ignorado sem Java, sem o CLI e sem a cópia do axios, e falha em vez disso quando
  `LODEMAP_EXIGIR_PIPELINE=1`.
- **Pipeline em Linux e macOS no CI:** o `.circleci/preparar_pipeline.sh` baixa o Structurizr CLI fixado
  (v2025.11.09, sha256 conferido) e o axios v1.21.1 (commit conferido); os novos jobs `pipeline-linux` e
  `pipeline-macos` rodam o teste do exemplo, e o macOS também roda a suíte completa.
- **Polimento do explorador e da linha do tempo:** no celular, uma visão pequena quebra os níveis largos em fileiras e
  se enquadra na faixa livre entre o cartão de título e a Legenda, com texto de 10 px ou mais. Rótulos de ligação
  ficam horizontais, com fundo, somem abaixo de um zoom ilegível (o mouse os mostra) e não cobrem outros nós; o foco
  enquadra o grupo inteiro quando isso mantém o texto legível. A linha do tempo mostra a data da release (`data_tag`,
  o commit marcado pela tag) com a data do mapa em segundo plano; arquivos antigos sem `data_tag` seguem iguais.

## 0.1.0 (primeira versão pública)

- **Rodada de validação (repetição, Linux, Go):** a atualização do axios foi repetida três vezes (US$ 0,29 a 0,47,
  mesma estrutura em todas); a suíte, a regeneração completa, os testes entregues, o gate de qualidade e o git hook
  real rodaram no Linux; um repositório Go (go-chi/chi) foi mapeado do zero e atualizado ao longo de uma release.
  Números em `references/benchmark-e-custo.md`. O que isso mudou na skill:
  - `"ignorar"` no `lodemap.json`: globs para arquivos que ficam ao lado do código e não são módulos (testes,
    exemplos, fixtures), com padrões por linguagem; todo script e o teste de cobertura leem a mesma lista.
  - O `novo_mapa.py` detecta a raiz do código: a primeira pasta convencional que tem código, ou então a raiz do
    repositório (`"raiz_codigo": ""`, globs como `**/*.go`).
  - Arestas de Go por símbolo em vez de por pacote: no chi, 6 arestas erradas viraram 31, todas confirmadas no
    código.
  - Impressão digital versão 2 (prefixo `2:`): atributos de classe e de instância, parâmetros de `__init__` e
    variáveis públicas em Python; chaves de objetos exportados, listas de exportação, membros de classe e parâmetros
    em várias linhas em JS/TS; a primeira linha de doc dos símbolos exportados em Go. Ela pega 9 das 12 mudanças de
    superfície que a versão 1 perdeu no rich e no axios, sem revisão extra, e os mapas antigos migram sem revisão em
    massa.
  - O trabalho pendente sobrevive a um segundo `rascunho`: relações não decididas e revisões pendentes continuam
    listadas até alguém decidir; o `renderizar` as limpa.
  - A rubrica de qualidade lê o código: um componente sem relação só conta como órfão quando o código o liga a algo,
    e a meta de relações por componente segue o que o código mostra. Uma biblioteca de módulos independentes deixa
    de falhar com o mapa certo.
  - Explorador: nós sem ligação vão para uma grade abaixo do grafo em vez de uma coluna alta; as visões de área
    mostram o próprio nome na barra lateral em vez do mesmo prefixo cortado.
  - O `atualizar.py` também acha o template pelo `LODEMAP_SKILL`, então o hook atualiza a prova de código sem a skill
    instalada em `~/.claude`.
- **Política de atualização (quando atualizar, por zero tokens):** o `scripts/lodemap_decidir.py` mede a dívida do
  mapa (módulos fora do modelo, caminhos que sumiram, superfícies públicas alteradas, relações de import novas,
  commits desde a última execução) e responde `nada`, `scripts`, `adiar`, `descrever`, `modelar` ou `gerar`, com os
  motivos e o próximo comando exato. Bloco `"politica"` opcional no `lodemap.json`; com `tolerancia_modulos` acima de
  0, módulos novos podem esperar num `pendentes.json` versionado e datado, e o teste de cobertura passa até o limite
  ou o prazo ser ultrapassado. O padrão continua estrito. O hook `post-commit` agora só regenera quando a resposta é
  `scripts` (antes rodava em todo commit que tocava código); o `esqueleto.py pendencias` é o ensaio por trás das
  contagens de revisões e relações.
- **Explorador:** os fluxos escolhem a direção que cabe no canvas (um fluxo de 13 passos passou de cerca de metade do
  tamanho, cortado nas bordas, para totalmente visível); a legenda começa fechada, lembra a escolha, e nenhum nó fica
  enquadrado sob uma caixa flutuante; os rótulos de relação não se escondem mais sob nós em layouts de colunas; os
  nomes dos marcadores seguem o idioma da interface e o inspetor deixa de repetir status e área como marcadores.
- **Rota enxuta de descrição (padrão para nome, descrição e área):** o `scripts/descrever.py` preenche nome, descrição
  de uma frase e área dos componentes pendentes com uma chamada `claude -p` (Haiku medium, sem ferramentas nem MCP,
  saída em JSON Schema com a área como enum, cartão determinístico por módulo, uma nova tentativa direcionada por um
  gate). No rich: nota 95–97, mesma faixa do subagente, cerca de metade dos tokens; no axios (JavaScript): 0,90 de
  concordância de área com uma referência Sonnet, 70 mil contra 99 mil tokens. Volta para o modelador em qualquer
  falha.
- **Escopo:** o Lodemap é só o mapa de arquitetura e a documentação do projeto. Os agentes padrão, os hooks de
  segurança, a telemetria e a visão Agentes não fazem parte dele (2026-11-06). A ponte opcional para um motor de
  memória externo e o escopo de consentimento dela foram removidos antes da primeira versão pública; os escopos são
  `gerar`, `gancho` e `modelo`.
- **Instalador:** dois perfis (`minimo`: skill + seis agentes `lodemap-*`; `padrao`: + aviso único), dry run por
  padrão, `reverter` exato em bytes, recusa-se a tocar arquivos de outra pessoa sem `--forcar`.
- **Permissão:** `plano` (0 tokens), `consentir` por escopo com teto mensal finito, `revogar`; o `plano` agora avisa
  quando os globs padrão não acham nenhum módulo em vez de imprimir uma estimativa de custo zero.
- **Leitor de docs:** desenha diagramas Mermaid offline (build mínimo embutido, carregado só quando a página tem um),
  com tema, tamanho real, ver fonte e tela cheia.
- **Segurança:** o lançador do git hook só roda scripts cujo hash foi aprovado; nomes de agente restritos a
  `[A-Za-z0-9-]`; caminhos pessoais absolutos removidos dos arquivos versionados, e os repositórios privados usados
  na medição de precisão de import são chamados de R1 a R5. O `SECURITY.md` diz como relatar uma vulnerabilidade.
- **Portabilidade:** o hook de commit recorre ao `pwsh` fora do Windows; o `verificar.py` falha de forma clara quando
  o `explorador/index.html` não existe.
- **Idioma:** português por padrão, inglês sob pedido (`"idioma"` do `lodemap.json` ou `LODEMAP_IDIOMA`): docs,
  explorador, leitor, rótulos do DSL e visões geradas; seletor PT | EN nas páginas. A maior parte das mensagens do
  terminal ainda está em português.
- **Visões determinísticas:** as visões de contexto, contêineres, por contêiner, por área (12+ componentes) e por
  status são escritas pelo `esqueleto.py` em `views/visoes-geradas.dsl`; o modelo agora escreve só os fluxos
  dinâmicos. O gate de qualidade aceita rótulos de status em inglês.
- **Pipeline multiplataforma:** `atualizar.py` (Windows, Linux, macOS; o `atualizar.ps1` é um invólucro fino). Só o
  Windows foi rodado de ponta a ponta.
- **Prova de relações por AST:** imports em Python, JS/TS, Go, Rust, Java, Kotlin, C# e C/C++; a precisão nas
  linguagens novas ainda não foi medida.
- **Leitor de docs:** `mindmap`, `architecture` e fórmulas KaTeX carregam o build completo do Mermaid (5,3 MB) só nas
  páginas que precisam.
- **Impressão digital semântica:** o `esqueleto.py rascunho` guarda uma `digital` por componente (só a superfície
  pública) e lista em `pendentes.componentes_revisar` apenas os módulos cuja superfície mudou; edições só no corpo
  mantêm a descrição. Medido em cinco pares de releases do rich: 78 arquivos alterados, 29 revisões (63% a menos).
  Veja `references/digital-semantica.md`.
- **Removido:** a exportação para cofre de notas pessoal; uma tag de estilo sem documentação e sem uso (as tags de
  forma documentadas não mudam).
- **Notas de medição:** os três repositórios privados medidos antes das demos públicas aparecem como projeto A, B e C
  em `references/benchmark-e-custo.md` e `references/custo-equivalente.json` (ids de rodada renomeados para
  combinar). Nenhum número mudou.
- **Repositórios fora do Python, de fábrica:** sem `--modulos`, o `novo_mapa.py` e o `plano` escolhem os globs pela
  linguagem que domina a raiz do código (`lib/**/*.js` num pacote JavaScript; Python mantém `raiz/*.py` +
  `raiz/*/`). Antes, o `plano` contava 7 módulos no axios em vez de 69.
- **Corrigido: `**` nos globs de módulo.** O `lib/**/*.js` não casava com arquivos diretamente sob `lib/` ao
  transformar arestas de import em relações, então toda aresta de ou para um arquivo na raiz era descartada (44 de 165
  no axios). O casamento agora segue o `Path.glob`, a mesma regra que o teste de cobertura usa.
- **Relações manuais:** uma relação que os imports não mostram (HTTP, adaptador escolhido por configuração, import
  tardio) é adicionada com `manual: true` e deixa de ser marcada como `sumiu_do_codigo` no `rascunho` seguinte.
- **Revisão conservadora:** numa atualização, o `descrever.py` mantém o nome e a área de um módulo que já os tinha e
  reescreve a frase só quando a mudança a tornou falsa. No axios v1.20.0 → v1.21.1: 1 de 16 frases mudou, contra 16
  de 16 (mais 8 nomes e 3 áreas) antes. O `--resumo` imprime um relatório de uma linha.
- **Gate de qualidade:** a `observabilidade` ainda conta no total, mas não tem piso próprio; uma biblioteca sem
  logs nem métricas tirava 0 ali com um modelo correto e reprovava no gate.
- **Decisões versionadas:** o `.gitignore` instalado mantém o `.lodemap/decisoes-modelo.json` no git, para que outra
  máquina ou o CI vejam as mesmas decisões e impressões digitais em vez de tratar todo módulo como novo.
- **Saída em português onde outras pessoas leem:** as mensagens de falha do teste de cobertura, as linhas de resumo
  de `rascunho`, `renderizar` e `descrever.py --resumo`, e os passos do `atualizar.py` seguem o idioma do mapa.
- **Corrigido: os dados do explorador levavam o caminho absoluto do repositório.** O `explorador/dados.js` é
  versionado e guardava o caminho local (com o nome de usuário) para o link "VS Code". O caminho saiu do arquivo:
  aberto como arquivo, o explorador o deriva do próprio endereço; servido em 127.0.0.1, lê o `.lodemap/local.json`
  (fora do git); e uma cópia hospedada não tem esse link.
- **Corrigido: painel de mudanças e hook de commit com globs `**`.** O `lodemap_diff.py` e o git hook casavam os
  globs de módulo com `fnmatch` mais uma contagem de barras, então com `lib/**/*.js` só arquivos exatamente uma pasta
  abaixo contavam como módulos alterados.
- **Corrigido: aviso desatualizado no `atualizar.py --incremental`.** "Módulos sem componente" era calculado antes da
  exportação, a partir do modelo anterior, e disparava mesmo quando o DSL já tinha os componentes novos.
- **Passagem de bastão na atualização:** depois de descrever um módulo novo, o `descrever.py` o lista em
  `pendentes.componentes_sem_container_ou_status`, para o modelador saber o que ainda falta decidir.
- **Demo pública:** um mapa do axios feito na v1.20.0 e atualizado para a v1.21.1, com o custo medido dos dois
  (README).
- **CLI:** `python -m lodemap --version` e `python -m lodemap doctor` (apelido `diagnostico`; `--json`, `--repo`): uma
  checagem só para leitura de Python, git, `claude`, Structurizr CLI, Graphviz, Java, Node, da skill e dos agentes
  instalados e, com `--repo`, do mapa e do consentimento desse repositório. Sai com 1 só quando falta algo
  obrigatório.
- **Baseline do gate de qualidade:** `references/baseline-qualidade.json`, com a chave de relatório `totalBaselineComparavel`. Grave o seu com
  `qualidade.py --gravar-baseline`.
- **Docs:** o `SKILL.md` caiu de 49 KB para 26 KB; o detalhe foi para `references/` (scripts, gate de qualidade,
  arestas de código, arquivo de estado, leitor e ADRs, servir, armadilhas) e só é lido quando um passo precisa. README
  reescrito.
- **CI:** CircleCI (Linux em Python 3.11 e 3.12, Windows), rodando `tests/` e os dois testes de template que rodam
  isolados. A configuração compila; o pipeline ainda não rodou (o repositório não está publicado).
- **Testes:** 284 em `tests/`, mais 14 nos dois arquivos de template isolados (`python -m pytest`).
