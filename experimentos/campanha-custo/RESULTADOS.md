# Campanha de custo do Lodemap: resultados

Medição de quanto custa construir o mapa de arquitetura completo, do zero, com a skill do Lodemap, em três
repositórios públicos e dois modelos. Todos os números abaixo saem de `resultados/*.json` e
`resultados/*.internas.jsonl`, pelo script `resumir.py` (saída colada na seção "Tabelas").

## Método

- **Repositórios** (cópia nova por rodada, `git archive` do commit fixo + `git init`): axios (`335e2f8`, 72 componentes),
  chi (`3a33ba5`, 36 componentes), click (`1d038f2`, 17 componentes).
- **Skill:** Lodemap no commit `e0e4d2b` (o mesmo nas 18 rodadas).
- **Modelos:** pilha `sonnet` (orquestrador Sonnet 5.5, agentes da skill com o modelo definido por eles) e pilha `haiku`
  (orquestrador Haiku e todos os agentes da skill forçados a `model: haiku`). Esforço `medium`.
- **Rodadas:** 3 por repositório × modelo = 18. Ordem embaralhada com semente fixa, 3 em paralelo.
- **Sessão:** `claude -p --output-format json --strict-mcp-config --setting-sources project --permission-mode
  bypassPermissions`, sem CLAUDE.md, ganchos nem MCP do usuário; a skill e os agentes ficam só em `.claude/` da cópia.
  O prompt autoriza `gerar,modelo` (sem gancho git) e manda seguir todos os passos até o mapa estar verificado.
- **Custo:** vem do próprio CLI: `total_cost_usd` da sessão (inclui os subagentes, que aparecem em `modelUsage`) mais,
  quando existe, a soma de `total_cost_usd` das chamadas internas do `descrever.py`. Essas chamadas rodam fora da
  sessão; um shim (`claude_shim.py`, via `LODEMAP_CLAUDE`) repassa cada chamada ao `claude` real e grava uma linha de
  custo em `<rodada>.internas.jsonl`.
- **O custo é preço equivalente de API, não fatura.** Todos os `modelUsage` trazem `costBasis: list` (preço de lista).
  A campanha rodou na assinatura, que não cobra por chamada; os valores em US$ servem para comparar rodadas entre si.
- **Qualidade:** `qualidade.py --sem-gate` (nota total e nº de componentes) e o teste de cobertura entregue no projeto
  (`test_arquitetura_cobertura.py`). Nas 18 rodadas o total ficou entre 94,0 e 96,2 (medição histórica, anterior à linha de base pública atual).
- **Remedição de cobertura:** o processo da campanha carregou um `medir()` sem `--noconftest`, e o `conftest.py` do
  click quebrava o teste (`No module named 'click'`). `remedir.py` refez a medição das 18 rodadas com `--noconftest`
  e guardou o valor antigo em `cobertura_original`. Mudaram de falha para ok as 6 rodadas do click; as outras já
  estavam ok.
- **Tempo:** relógio de parede da sessão em segundos, com 3 rodadas concorrentes (varia com a carga da máquina).
- `chi-sonnet-1` falhou na primeira passada (`PermissionError` ao apagar a pasta da rodada, no Windows); o runner foi
  corrigido (`onerror` com `chmod`) e a rodada refeita sozinha (`--so chi-sonnet-1`), depois das outras. O arquivo
  `resultados/piloto-chi-sonnet-1.json` é de uma execução-piloto anterior, não entra nas contas.

## Tabelas

Saída de `python resumir.py`:

```
Rodadas lidas: 18

| Rodada | Sessao (US$) | Interno (US$) | Chamadas internas | Total (US$) | Gate | Componentes | Cobertura | Tempo (s) |
|---|---|---|---|---|---|---|---|---|
| axios-haiku-1 | 0.6280 | 0.0607 | 5 | 0.6887 | 94.5 | 72 | ok | 1077 |
| axios-haiku-2 | 0.1512 | 0.0601 | 5 | 0.2113 | 95.0 | 72 | ok | 891 |
| axios-haiku-3 | 0.6926 | 0.0661 | 5 | 0.7588 | 94.9 | 72 | ok | 1994 |
| axios-sonnet-1 | 1.2508 | 0.0603 | 5 | 1.3110 | 94.9 | 72 | ok | 945 |
| axios-sonnet-2 | 1.7885 | 0.0556 | 5 | 1.8441 | 95.0 | 72 | ok | 943 |
| axios-sonnet-3 | 1.0312 | 0.0600 | 5 | 1.0912 | 94.9 | 72 | ok | 613 |
| chi-haiku-1 | 0.1392 | 0.0291 | 3 | 0.1682 | 94.0 | 36 | ok | 719 |
| chi-haiku-2 | 0.2063 | 0.0311 | 3 | 0.2374 | 94.6 | 36 | ok | 851 |
| chi-haiku-3 | 0.1513 | 0.0311 | 4 | 0.1824 | 94.7 | 36 | ok | 780 |
| chi-sonnet-1 | 0.9126 | 0.0334 | 4 | 0.9460 | 94.5 | 36 | ok | 484 |
| chi-sonnet-2 | 0.7515 | ausente* | ausente* | 0.7515* | 94.7 | 36 | ok | 368 |
| chi-sonnet-3 | 0.9785 | ausente* | ausente* | 0.9785* | 95.8 | 36 | ok | 1257 |
| click-haiku-1 | 0.1659 | 0.0255 | 6 | 0.1914 | 95.0 | 17 | ok | 659 |
| click-haiku-2 | 0.0562 | 0.0316 | 10 | 0.0878 | 94.2 | 17 | ok | 350 |
| click-haiku-3 | 0.1687 | 0.0262 | 6 | 0.1949 | 94.2 | 17 | ok | 648 |
| click-sonnet-1 | 0.9256 | 0.0265 | 6 | 0.9521 | 95.0 | 17 | ok | 459 |
| click-sonnet-2 | 0.6346 | ausente* | ausente* | 0.6346* | 95.8 | 15 | ok | 263 |
| click-sonnet-3 | 0.8311 | ausente* | ausente* | 0.8311* | 96.2 | 17 | ok | 377 |

`*` = sem registro das chamadas internas (descrever.py); o total e so a sessao, piso e nao valor medido.

| Repo x modelo | n | Total medio | Min | Max | So sessao medio | Min | Max | Rodadas c/ interno | Gate medio | Tempo medio (s) | Cobertura ok |
|---|---|---|---|---|---|---|---|---|---|---|---|
| axios x haiku | 3 | 0.5529 | 0.2113 | 0.7588 | 0.4906 | 0.1512 | 0.6926 | 3/3 | 94.8 | 1321 | 3/3 |
| axios x sonnet | 3 | 1.4154 | 1.0912 | 1.8441 | 1.3568 | 1.0312 | 1.7885 | 3/3 | 94.9 | 834 | 3/3 |
| chi x haiku | 3 | 0.1960 | 0.1682 | 0.2374 | 0.1656 | 0.1392 | 0.2063 | 3/3 | 94.4 | 784 | 3/3 |
| chi x sonnet | 3 | 0.8920 | 0.7515 | 0.9785 | 0.8809 | 0.7515 | 0.9785 | 1/3 | 95.0 | 703 | 3/3 |
| click x haiku | 3 | 0.1580 | 0.0878 | 0.1949 | 0.1303 | 0.0562 | 0.1687 | 3/3 | 94.5 | 552 | 3/3 |
| click x sonnet | 3 | 0.8059 | 0.6346 | 0.9521 | 0.7971 | 0.6346 | 0.9256 | 1/3 | 95.7 | 367 | 3/3 |

Total medio mistura rodadas com e sem registro interno; a coluna 'So sessao' e comparavel entre todas.

Por modelo (todas as rodadas, so sessao):
- haiku: n=9 media 0.2622 min 0.0562 max 0.6926
- sonnet: n=9 media 1.0116 min 0.6346 max 1.7885

Cobertura original (antes do remedir --noconftest) vs atual:
- click-haiku-1: original=False atual=True
- click-haiku-2: original=False atual=True
- click-haiku-3: original=False atual=True
- click-sonnet-1: original=False atual=True
- click-sonnet-2: original=False atual=True
- click-sonnet-3: original=False atual=True

Sem registro interno (4): chi-sonnet-2, chi-sonnet-3, click-sonnet-2, click-sonnet-3
Chamadas internas sem custo legivel: nenhuma
```

## Leitura

- Nas 18 rodadas o mapa foi gerado, o teste de cobertura passou (após a remedição) e a nota do gate ficou entre 94,0 e
  96,2. A qualidade medida pelo gate não distingue os modelos: Haiku e Sonnet ficam na mesma faixa.
- O custo distingue: só sessão, Sonnet média US$ 1,0116 contra US$ 0,2622 do Haiku (n=9 cada), mas a dispersão dentro
  de um mesmo par é grande (axios × haiku vai de 0,1512 a 0,6926).
- O custo cresce com o tamanho do repositório (17, 36 e 72 componentes) nos dois modelos.
- As chamadas internas do `descrever.py` somam entre US$ 0,0255 e US$ 0,0661 por rodada onde há registro: pouco perto
  da sessão.

## Rodadas sem registro interno (item aberto)

`chi-sonnet-2`, `chi-sonnet-3`, `click-sonnet-2` e `click-sonnet-3` não têm `.internas.jsonl`. Nenhuma tem
`descrito_por` em `decisoes-modelo.json` (as rodadas com registro têm, 17 em click-sonnet-1 e click-haiku-1), e nos
transcritos de `click-sonnet-2`, `click-sonnet-3` e `chi-sonnet-2` não há comando Bash/PowerShell que execute
`descrever.py`: o orquestrador/agente de modelagem descreveu os componentes à mão e não chamou o script. Em
`chi-sonnet-3` o transcrito mostra a execução do `descrever.py` (`--resumo`), e o relatório final diz que ele "travou
na chamada `claude -p` aninhada" e foi morto após cerca de 10 minutos; o shim só grava a linha quando a chamada
termina, então a chamada interrompida não deixou registro e seu custo é desconhecido. Por isso essas quatro rodadas
ficam marcadas como **ausente** e o total delas é piso (só sessão). Não se estimou custo interno para elas.
O fato de o `descrever` só ter sido usado em parte das rodadas Sonnet é decisão do próprio modelo, não do runner: o
prompt manda seguir a skill, e a skill diz para rodar o `descrever.py` antes dos subagentes.

## Limitações

- **n=3** por célula; com dispersão como a de axios × haiku (4,6 vezes entre mínimo e máximo), as médias são
  indicativas, não estimativas estáveis. Sem teste de significância.
- **Quatro rodadas sem registro interno**, todas na pilha Sonnet (chi e click): o "total" delas é piso, e as médias de
  `chi x sonnet` e `click x sonnet` misturam rodadas com e sem registro. Compare pela coluna "So sessao".
- **Preço de lista**, não fatura; os preços de lista mudam e não refletem a assinatura.
- **Tempo** medido com 3 rodadas em paralelo na mesma máquina e dependente de carga e limites da assinatura; não é
  latência isolada.
- **Cobertura:** o resultado vem da remedição com `--noconftest`; o valor da campanha original (falha nas 6 rodadas do
  click) fica em `cobertura_original` nos JSON. O teste passando mede o teste que a própria rodada gerou, não a
  fidelidade do mapa.
- **Gate** mede forma (descrições, caminhos existentes, relações, órfãos, observabilidade), não se o mapa está certo.
  Observabilidade foi citada como ponto fraco nas rodadas de click e chi (relatórios finais das sessões).
- `click-sonnet-2` tem 15 componentes, não 17; o gate não penaliza isso.
- Três repositórios (JavaScript, Go, Python) e um único commit da skill: não generaliza para outros projetos.

## Arquivos

- `rodar_campanha.py`: runner (caminhos por `LODEMAP_CAMP_BASE` e `LODEMAP_SKILL`; no original eram absolutos).
- `claude_shim.py`: registra o custo das chamadas internas. `remedir.py`: remede cobertura. `transcritos.py`: resume
  os transcritos de sessão. `resumir.py`: gera as tabelas acima.
- `q-axios.json`, `q-chi.json`, `q-e2e.json`: saídas do `qualidade.py` (nota total e critérios) guardadas na pasta da campanha; não alimentam as tabelas.
  usado por nenhum script.
- `resultados/`: um JSON por rodada, o `.internas.jsonl` (quando existe) e o piloto. Caminhos absolutos foram
  trocados por `<BASE>` e `<SKILL>`.
