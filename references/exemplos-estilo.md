# Exemplos de estilo (few-shot) para o lodemap-modelador

Projeto **fictício** "Mercúrio" (loja online com pedidos, estoque e pagamento). Os nomes, caminhos e métricas são
inventados; copie o **formato e o nível de detalhe**, nunca o texto. O `qualidade.py` mede exatamente isto.

## Como escrever um componente

Regras que a rubrica confere:

- **Descrição:** uma frase, com 40 caracteres ou mais, que diz **o que faz e por que existe** (o porquê). Nunca repita
  o nome ("Serviço de pedidos" como descrição de "Serviço de pedidos" reprova).
- **Tags:** `<Status>,Area<Nome>` e, se couber, uma tag de forma (`Gate`, `Dados`, `Privacidade`, `Modelo`, `Janela`,
  `WebBrowser`, `Barramento`). Status válido: `Pronto`, `EmAndamento`, `Aguardando…`, `Planejado`, `ForaDoFoco`.
- **Propriedades:** `status` (texto, igual à tag), `area`, `codigo` (caminho que existe no repositório) e
  `observabilidade` (nomes de log ou métrica que **existem no código**; sem inventar). Sem observabilidade real, omita
  a propriedade em vez de preencher com algo genérico.
- **Grupo:** todo componente fica dentro de um `group "Área" { }`.
- **Identificador:** camelCase com prefixo da área (`pedRegras`, `estBaixa`), único e estável.
- **Planejado:** só existe no design; a propriedade `codigo` pode ficar de fora e o `ramo` marca código em outro ramo.

## Componentes

```
group "Pedidos" {
    pedEntrada = component "Rota de pedidos" "Recebe o pedido do carrinho e o valida, para que as regras de preço e estoque só vejam dados já limpos." "Python (FastAPI)" "Pronto,AreaPedidos" {
        properties {
            "status" "Pronto"
            "area" "AreaPedidos"
            "codigo" "loja/api/pedidos.py"
            "observabilidade" "pedidos.requisicoes, pedidos.invalidos, pedidos.latencia_ms"
        }
    }

    pedRegras = component "Regras de preço" "Calcula frete, cupom e imposto num lugar só, porque o checkout e o painel precisam do mesmo total." "Python" "Pronto,AreaPedidos" {
        properties {
            "status" "Pronto"
            "area" "AreaPedidos"
            "codigo" "loja/pedidos/precos.py, cupons.py"
            "observabilidade" "precos.cupom_recusado"
        }
    }

    pedFila = component "Fila de pedidos" "Guarda o pedido aceito até o pagamento confirmar, para o cliente não perder o carrinho numa queda do gateway." "Python (Celery)" "EmAndamento,AreaPedidos,Barramento" {
        properties {
            "status" "Em andamento"
            "area" "AreaPedidos"
            "codigo" "loja/pedidos/fila.py"
            "ramo" "feat/fila-pedidos"
        }
    }
}

group "Estoque" {
    estBaixa = component "Baixa de estoque" "Reserva e baixa as unidades de forma atômica, porque duas compras do último item não podem passar juntas." "Python" "Pronto,AreaEstoque,Gate" {
        properties {
            "status" "Pronto"
            "area" "AreaEstoque"
            "codigo" "loja/estoque/baixa.py"
            "observabilidade" "estoque.reserva_ok, estoque.reserva_falhou, estoque.conflito"
        }
    }

    estRepo = component "Repositório de estoque" "Isola o SQL do estoque atrás de uma interface, para trocar o banco sem mexer nas regras." "Python (SQLAlchemy)" "Pronto,AreaEstoque,Dados" {
        properties {
            "status" "Pronto"
            "area" "AreaEstoque"
            "codigo" "loja/estoque/repo.py, modelos.py"
        }
    }
}

group "Pagamento" {
    pagGateway = component "Cliente do gateway" "Fala com o provedor de cartão com tempo limite e nova tentativa, porque o provedor oscila nos picos de venda." "Python (httpx)" "Pronto,AreaPagamento,Nuvem" {
        properties {
            "status" "Pronto"
            "area" "AreaPagamento"
            "codigo" "loja/pagamento/gateway.py"
            "observabilidade" "pagamento.timeout, pagamento.retry, pagamento.aprovado"
        }
    }

    pagAntifraude = component "Antifraude local" "Pontua o pedido antes da cobrança para segurar os suspeitos; ainda não há modelo treinado." "Python" "Planejado,AreaPagamento,Modelo" {
        properties {
            "status" "Planejado"
            "area" "AreaPagamento"
        }
    }
}
```

## Relações

Formato: `origem -> destino "verbo no presente" "tecnologia" ["TagOpcional"]`. O verbo diz o que passa de um lado para
o outro; a tecnologia diz **como** (protocolo, biblioteca ou formato). Sem verbo ou sem tecnologia, a relação reprova.

```
pedEntrada -> pedRegras "Pede o total do pedido" "Chamada de função"
pedEntrada -> pedFila "Enfileira o pedido aceito" "Celery, Redis"
pedRegras -> estBaixa "Reserva os itens antes de fechar o preço" "Chamada de função"
estBaixa -> estRepo "Lê e atualiza o saldo em transação" "SQLAlchemy"
pedFila -> pagGateway "Cobra o cartão do pedido" "HTTPS, JSON"
pagGateway -> provedorCartao "Autoriza a cobrança" "HTTPS, JSON" "Gate"
pagAntifraude -> pagGateway "Segura a cobrança suspeita" "Chamada de função" "Planejado"
```

Dica de recall: antes de escrever as relações, leia `relacoes-codigo.json` (gerado por
`codegraph_ponte.py --relacoes`). Cada par é uma **sugestão** com `confianca`; confirme no código e dê o verbo.
Relações com pessoas e sistemas externos (`dono -> app`) não aparecem ali: vêm do inventário e do domínio.

## Visão dinâmica (fluxo)

Cada passo precisa de uma relação que já exista no modelo. Numere e descreva o passo em uma frase curta. Um fluxo
bom tem de 6 a 12 passos, do gatilho até o efeito final, e inclui um ramo de falha em outro fluxo.

```
dynamic api "Pedido-feliz" "Do carrinho ao pedido pago, sem falhas." {
    pedEntrada -> pedRegras "1. Pede o total do pedido"
    pedRegras -> estBaixa "2. Reserva os itens"
    estBaixa -> estRepo "3. Baixa o saldo em transação"
    pedEntrada -> pedFila "4. Enfileira o pedido aceito"
    pedFila -> pagGateway "5. Cobra o cartão"
    pagGateway -> provedorCartao "6. Autoriza a cobrança"
    autoLayout lr 150 50
    title "Pedido feliz"
}
```

E uma visão estática por container com componentes (o `qualidade.py` exige pelo menos uma):

```
component api "Api-Completa" "Todos os componentes da API. Base das visões por status." {
    include *
    autoLayout lr 150 50
    title "API: todos os componentes"
}
```
