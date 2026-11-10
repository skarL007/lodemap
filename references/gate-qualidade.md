# Gate de qualidade: critérios, pesos e linha de base

O ciclo do gate está no `SKILL.md`. Aqui ficam a rubrica e a origem da linha de base.

**Critérios e pesos (soma 100; os pesos são uma escolha do autor, aberta a contestação):**

| Critério | Peso | Por quê |
|---|---|---|
| `descricao` (40+ caracteres, sem repetir o nome) | 14 | é o que o dono lê no painel; modelo preguiçoso falha primeiro aqui |
| `codigo` (caminho existe) | 12 | liga o componente ao código; sem isso, impacto e abrir no VS Code mentem |
| `cobertura` (módulos cobertos) | 11 | o teste de cobertura trava o merge; mesma regra |
| `recall_relacoes` (pares do código no modelo) | 10 | relação faltante esconde impacto de mudança; a ponte entrega a lista pronta |
| `relacoes_qualificadas` (verbo e tecnologia) | 8 | seta sem verbo não informa |
| `relacoes_media` (média / alvo, teto 100) | 6 | densidade mínima para o grafo ter navegação |
| `orfaos` | 6 | componente sem relação que o código liga é erro de modelagem |
| `precisao_relacoes` (relação com aresta real) | 6 | evita relação inventada; peso baixo porque HTTP, fila e config não deixam aresta no código |
| `observabilidade` | 5 | nem todo componente emite log ou métrica; pesa pouco, só vale com nome real do código e não tem piso próprio (uma biblioteca sem log tira 0 com o modelo certo) |
| `status` (tag válida igual à propriedade) | 5 | o filtro por status do explorador depende disso |
| `visoes_container` | 5 | um container sem visão de componentes fica invisível |
| `fluxos` (visões dinâmicas, alvo 3) | 5 | fluxo animado é o diferencial do explorador |
| `agrupamento` (grupo ou área) | 4 | organiza o grafo; fácil de cumprir |
| `passos_fluxo` (média / 6, teto 100) | 3 | evita fluxo de 2 passos só para contar |

**Os dois critérios de densidade olham o código quando a ponte achou alguma aresta.** Numa biblioteca de módulos
independentes (26 dos 30 middlewares do go-chi/chi não importam nem usam nenhum outro módulo), o mapa certo tem
componente sem relação e poucas relações por componente; a rubrica antiga reprovava esse mapa (89,6, com `orfaos`
54,3 e `relacoes_media` 67,6 abaixo dos pisos) e empurrava o modelador a inventar seta. Agora `orfaos` conta só o
componente sem relação no modelo **que o código liga a outro**, e o alvo de `relacoes_media` é
`min(3, max(1, 2 × pares do código / componentes))` em vez de 3 fixo. Sem leitura do código (ponte sem aresta, ou
linguagem que ela não lê), valem as regras antigas. Com a mudança o mapa do chi tira 94,3 e o do axios passa de
94,5 para 94,6; a nota de um mapa antigo pode subir sem o mapa ter mudado, e por isso a comparação entre datas
pede a mesma versão da rubrica.

A linha de base é o exemplo público do axios v1.21.1 em `exemplos/axios`, com 72 componentes. A medição usa
o mapa da demo em `34d46331bae4a0c5018448f75389cb223002f320`, cujas fontes estão no exemplo, e `--fonte ast`:
total **94,6**, precisão de relações **94,1**, observabilidade **0** e os demais critérios **100**. Os valores e
os detalhes estão em `baseline-qualidade.json`. O mínimo total comparável é 84,6; cada critério disponível, exceto
observabilidade, exige 70% da referência. O gate e seus parâmetros não foram relaxados.

Para reproduzir, obtenha o axios na tag v1.21.1, aplique o exemplo e exporte o mapa seguindo
`tests/test_exemplo_axios.py`; execute `python scripts/qualidade.py --arq <pasta-structurizr> --repo <axios>
--fonte ast --gravar-baseline <arquivo> --sem-gate`. É necessário o Structurizr CLI para gerar `workspace.json`.
O mapa e o código devem corresponder à mesma versão. A demo e os mapas da campanha são cópias locais; os JSONs
da campanha são os registros dos resultados, não uma distribuição dos mapas gerados.

Na mesma rubrica e fonte, com a linha de base acima, os resultados foram:

| Mapa | Total | Gate |
|---|---:|---|
| Demo axios v1.21.1 | 94,6 | passou |
| Demo chi v5.5.0 | 94,3 | passou |
| Campanha axios Sonnet 1–3 | 94,9; 95,0; 94,9 | 3/3 passaram |
| Campanha chi Sonnet 1–3 | 94,5; 94,7; 95,8 | 3/3 passaram |
| Campanha click Sonnet 1–3 | 95,0; 95,8; 96,2 | 3/3 passaram |
| Campanha axios Haiku 1–3 | 94,5; 95,0; 94,9 | 3/3 passaram |
| Campanha chi Haiku 1–3 | 94,0; 94,6; 94,7 | 3/3 passaram |
| Campanha click Haiku 1–3 | 95,0; 94,2; 94,2 | 3/3 passaram |

Para cada cópia, o comando foi `python scripts/qualidade.py --arq <repo>/docs/architecture/structurizr
--repo <repo> --fonte ast --baseline references/baseline-qualidade.json`. As 18 cópias são saídas da campanha
descrita em `../experimentos/campanha-custo/RESULTADOS.md`, que fixa os commits dos repositórios públicos; a
regeração com modelo pode produzir mapas e notas diferentes. O commit da demo citado acima é local, não é uma
fonte publicada; o exemplo versionado neste repositório permite reconstruir a medição sem depender dele. A execução integral de
`tests/test_exemplo_axios.py` gerou uma baseline idêntica, incluindo notas e detalhes.

A comparação com o próprio projeto pode
revelar pisos inadequados à sua arquitetura. Leia as notas por critério ou grave uma régua própria com
`--gravar-baseline <json>` e passe `--baseline <json>`. O gate mede estrutura, não veracidade semântica.
