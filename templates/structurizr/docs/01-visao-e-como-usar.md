# Visão e como usar

Esta é a arquitetura de {{PROJETO}} no modelo C4, escrita no Structurizr. O `workspace.dsl` e os fragmentos em
`model/` e `views/` são a fonte. Tudo o que aparece nos diagramas, no explorador, no leitor e nos documentos
derivados sai deles.

## Como abrir

Para regenerar, em qualquer sistema (Windows, Linux e macOS; Python 3.10+ e Structurizr CLI), na pasta da arquitetura:

```
python scripts/atualizar.py                       # valida e regenera docs, leitor e explorador, sem abrir nada
python scripts/atualizar.py --incremental --checkpoint "merge feat/x"
python scripts/atualizar.py --com-site            # também o site estático do Structurizr
```

O `atualizar.py` acha o Structurizr CLI em `STRUCTURIZR_CLI`, depois em `~/.structurizr/cli/` e depois no PATH
(`structurizr.bat` no Windows, `structurizr.sh` nos outros sistemas). No Windows, o `atualizar.ps1` continua existindo
como invólucro que chama o `atualizar.py` com os mesmos parâmetros (`-Incremental`, `-Checkpoint`, `-ComSite`).

Para abrir, no PowerShell (Windows):

```
.\scripts\ver-arquitetura.ps1                 # explorador (diagramas e fluxos) em localhost
.\scripts\ver-arquitetura.ps1 -Abrir Leitor   # leitor de documentação e decisões
.\scripts\ver-arquitetura.ps1 -ComLite        # também o Structurizr Lite
```

Fora do Windows, sirva a pasta com `python -m http.server --bind 127.0.0.1` e abra `explorador/index.html` ou `leitor/index.html`.

O explorador fica em `http://127.0.0.1:{{PORTA_EXPLORADOR}}/explorador/` e o leitor em `http://127.0.0.1:{{PORTA_EXPLORADOR}}/leitor/`, os dois servidos por `python -m http.server --bind 127.0.0.1`; também abrem direto do disco. O Structurizr Lite (`http://localhost:{{PORTA_LITE}}`) só sobe com `-ComLite`. As URLs ficam no `lodemap.json` (`lite` e `explorador`). Se a porta já tem a arquitetura no ar, o script só abre o navegador.

O site estático do Structurizr saiu do padrão: `atualizar.py --com-site`. Scripts seus, fora do repositório, entram como extensões locais: liste-os em `"extensoes"` no `lodemap.json` (ou em `LODEMAP_EXTENSOES`, separados por `;` e, fora do Windows, também por `:`); cada um recebe o `workspace.json`, `--arq` e `--repo`.

## Atualização por checkpoint

`--checkpoint` (`-Checkpoint` no `.ps1`) grava o rótulo em `.lodemap/estado.json` (e o passa às extensões locais); `--incremental` só regenera se algo
mudou desde a última geração (`scripts/lodemap_diff.py`). O gancho do git é opt-in:
`.\scripts\instalar-gancho.ps1 -Python <python> -Ferramentas <pasta>` (e `-Remover`). Ele roda o `atualizar.ps1` (que chama o `atualizar.py`)
em segundo plano a cada commit que toca o código ou o DSL e a cada merge, com log em `.lodemap/ultimo-atualizar.log`.

## Explorador interativo

`explorador/index.html` lê `explorador/dados.js` (gerado; não edite à mão). Clique num nó para acender as ligações
dele; `Shift`+clique mostra o caminho entre dois nós; duplo clique abre a vizinhança no modelo inteiro; as visões
dinâmicas tocam passo a passo. O painel mostra status, código (VS Code e GitHub), observabilidade, métricas (atual ×
meta, data e fonte), o impacto de mudar e os links para o leitor. O endereço `index.html#<identificador do DSL>`
abre a menor visão que contém o elemento, já em foco.

## Leitor de documentação e decisões

`leitor/index.html` lê `leitor/dados.js`, gerado de `docs/*.md` e `adrs/*.md` por `scripts/gerar_leitor.py` (não edite à mão). Os documentos ficam em Explicação, Guias e Referência (os gerados 02, 90 e 91) e os ADRs numa linha do tempo com status. Tem sumário lateral, busca no texto (tecla `/`), tema claro e escuro (`?tema=claro` ou `?tema=escuro`) e âncoras estáveis: `leitor/index.html#doc-<arquivo sem .md>` e `#adr-<id de 4 dígitos>`. Todo elemento citado leva ao mapa (`explorador/index.html#<identificador>`).

## Decisões (ADRs)

Um formato só, em `adrs/NNNN-<titulo>.md`: cabeçalho YAML com `id`, `titulo`, `status` (`proposta`, `aceita`, `substituida` ou `rejeitada`), `data`, `date` (cópia de `data`, lida pelo Structurizr), `decisores`, `elementos` (identificadores do modelo), `substitui`, `substituida_por` e `evidencia`; depois as seções Contexto, Decisão, Alternativas e Consequências. O índice `92-indice-de-decisoes.md` é gerado, e o teste `test_adrs_formato.py` falha se um ADR citar elemento inexistente, se a substituição não for recíproca ou se o status for inválido.

## Cores e formas

| Cor | Status | Significado |
|---|---|---|
| Verde | Pronto | No código, testado e integrado. |
| Âmbar | Em andamento | Alguém está mexendo agora. |
| Roxo | Aguardando | Espera revisão, decisão ou outra equipe. |
| Cinza-azulado tracejado | Planejado | Existe no design, não no código. |
| Cinza escurecido | Fora do foco | Existe, mas não é prioridade. |

| Forma | Tag | Significado |
|---|---|---|
| Cilindro | Dados | Guarda dados. |
| Hexágono | Gate | Guarda de privacidade, custo ou contrato. |
| Robô | Modelo | Processo que serve um modelo. |
| Navegador | WebBrowser | Página. |
| Janela | Janela | Janela de desktop. |
| Cano | Barramento | Fluxo de eventos. |
| Borda tracejada laranja | Externo, Nuvem | Fora da máquina. |
| Borda amarela grossa | Privacidade | Toca dado privado. |

## Como alterar

1. Edite o fragmento certo em `model/` ou `views/`.
2. Rode `python scripts/atualizar.py` (ou `scripts\atualizar.ps1` no Windows).
3. Registre o motivo no `99-registro-de-atualizacoes.md`.
4. Rode os testes `test_arquitetura_cobertura.py`, `test_arquitetura_metricas.py`, `test_adrs_formato.py` e `test_leitor_gerador.py`.
