# Estudo com pessoas: o mapa do Lodemap ajuda a entender o axios mais rápido?

Status: pré-registro. O protocolo foi congelado em 11/11/2026, no commit que adiciona este arquivo; para achá-lo:
`git log --diff-filter=A -- experimentos/estudo-pessoas/PROTOCOLO.md`. A coleta ainda não começou. Qualquer mudança depois do congelamento entra como
emenda datada no fim deste arquivo, sem reescrever o texto acima. Nenhum resultado pode ser citado antes da coleta e da
análise descritas aqui.

## Pergunta e hipótese

- Pergunta: com o explorador do Lodemap aberto, uma pessoa desenvolvedora encontra no código do axios a resposta de uma
  pergunta de arquitetura mais rápido e com mais acerto do que só com o repositório?
- H1 (tempo): a mediana do tempo por tarefa é menor com o mapa.
- H2 (acerto): a taxa de acerto com o mapa não é menor que sem ele (o mapa não pode comprar velocidade com erro).
- O que NÃO se testa: produtividade geral, ganho em projeto próprio, retenção de longo prazo.

## Desenho

- Dentro de cada participante, com contrabalanço: dois conjuntos de 3 tarefas (A e B) de dificuldade parecida.
  Metade faz A com o mapa e B sem; a outra metade faz o inverso. A ordem (com mapa primeiro ou sem mapa primeiro)
  também alterna. São 4 grupos, com os participantes distribuídos em rodízio na ordem de chegada.
- Material: checkout do axios na tag v1.21.1 (o mesmo do mapa), aberto no editor da pessoa, com busca liberada.
  "Com mapa" acrescenta https://skarl007.github.io/lodemap/demo/explorador/. Sem IA/assistente de código nas duas condições.
- Tempo: cerca de 20 minutos por pessoa (2 min de apresentação, 6 tarefas de até 3 min, 2 min de questionário).
- Piloto: 2 pessoas antes da coleta, só para medir se as tarefas cabem em 3 minutos. Os dados do piloto não entram na análise.
- Amostra: alvo de 12 pessoas (3 por grupo). É um estudo pequeno: mede a direção e o tamanho do efeito, não prova
  significância. O relatório diz isso na primeira linha.

## Tarefas e gabarito (conferido no checkout v1.21.1 em 11/11/2026)

Resposta certa = arquivo correto e, quando a tarefa pede, a função. Linha aproximada não é exigida.

| # | Conjunto | Tarefa | Gabarito |
|---|---|---|---|
| 1 | A | Qual arquivo decide qual adaptador (xhr, http ou fetch) atende a requisição? | `lib/adapters/adapters.js`, função `getAdapter` (linha 65) |
| 2 | A | Em que ordem rodam os interceptores de requisição, por padrão? | do último registrado para o primeiro: `lib/core/Axios.js`, `unshiftRequestInterceptors` (linha 222) |
| 3 | A | Onde a configuração padrão da instância é mesclada com a da chamada? | `lib/core/Axios.js` linha 135, `mergeConfig(this.defaults, config)`, implementada em `lib/core/mergeConfig.js` |
| 4 | B | Qual função decide se a promise resolve ou rejeita a partir do status HTTP? | `lib/core/settle.js`, `settle`, via `config.validateStatus` (linhas 15 e 16) |
| 5 | B | Em que etapa o `transformRequest` é aplicado ao corpo? | `lib/core/dispatchRequest.js` linha 77, `transformData.call(config, config.transformRequest)` |
| 6 | B | No adaptador fetch, onde o timeout vira um sinal de cancelamento? | `lib/adapters/fetch.js` linha 241, `composeSignals`, de `lib/helpers/composeSignals.js` |

Pares de dificuldade: 1↔4 (localizar arquivo), 2↔5 (comportamento de etapa), 3↔6 (cruzar dois arquivos).

## Medidas

- Tempo por tarefa, do enunciado lido à resposta dada (cronômetro do aplicador). Limite de 3 min; estourou = erro com 180 s.
- Acerto (0/1) pelo gabarito, decidido por quem aplica antes de ver a condição na planilha (a coluna da condição fica
  oculta na correção).
- Confiança da pessoa em cada resposta (1 a 5).
- Ao fim: experiência (anos com JavaScript, já usou o axios por dentro: sim/não) e uma pergunta aberta sobre o mapa.

## Análise (decidida antes da coleta)

- Por pessoa: mediana do tempo com mapa menos sem mapa; depois, a mediana dessas diferenças com intervalo de 95% por
  bootstrap (10.000 reamostragens, semente fixa).
- Acerto: taxa com e sem mapa, diferença com intervalo de 95% por bootstrap.
- H1 é apoiada se o intervalo do tempo ficar todo abaixo de zero; H2, se o limite inferior da diferença de acerto for
  maior que −10 pontos percentuais. Qualquer outro resultado é relatado como está, inclusive se o mapa atrapalhar.
- Nenhuma pessoa é excluída depois de ver os dados. As exclusões permitidas são só estas, decididas antes: a pessoa não
  terminou, ou houve falha técnica registrada na hora.

## Privacidade e ética

- Participação voluntária, sem pagamento e sem coleta de nome na planilha (código P01, P02…).
- Não gravar tela nem voz. A planilha fica fora do repositório público. O que se publica é só o agregado.
- A pessoa pode desistir a qualquer momento, e os dados dela são apagados.

## Divulgação

- Antes da coleta: só "estou montando um estudo". Sem prometer resultado.
- Depois: um post com o resultado, qualquer que seja, com n, intervalo e a limitação do tamanho da amostra.

## Emendas

Nenhuma até agora.
