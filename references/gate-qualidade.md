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

Notas da linha de base (`baseline-qualidade.json`: o primeiro mapa que a skill gerou, 188 componentes; total 82,2 com 14 critérios, CodeGraph como fonte): descrição 79,8; código 100;
observabilidade 14,9; relações por componente 98,2; órfãos 100; qualificadas 100; status 100; visão por container 100;
fluxos 100; passos 100; agrupamento 100; cobertura 100; recall de relações 27,1; precisão de relações 44,6.
Os valores baixos da linha de base (observabilidade, recall, precisão) viram pisos baixos de propósito: o gate cobra o que
aquele mapa de fato entregou, não um ideal. No seu projeto, leia a nota absoluta e as notas por critério; para usar
o seu próprio mapa como régua, grave outra linha de base com `--gravar-baseline <json>` e passe `--baseline <json>`.
