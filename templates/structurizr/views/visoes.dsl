        // 1. Panorama e contexto
        systemContext sistema "Contexto" "Quem usa o sistema e com o que ele conversa." {
            include *
            autoLayout lr 150 50
            title "Contexto"
        }

        // 2. Containers
        container sistema "Containers" "Os processos e os dados." {
            include *
            autoLayout lr 150 50
            title "Containers"
        }

        // 3. Componentes por área (uma visão por container grande, ou por área com include "element.tag==Area...")
        component app "App-Completo" "Todos os componentes da aplicação. Base das visões por status." {
            include *
            autoLayout lr 150 50
            title "Aplicação: todos os componentes"
        }

        // 4. Fluxos (visões dinâmicas): cada passo precisa de uma relação que exista no modelo.
        //    Numa visão de container, só entram componentes DESSE container; de outros, use o container inteiro.
        dynamic app "Fluxo-principal" "O caminho principal, passo a passo." {
            usuario -> appEntrada "1. Chama o ponto de entrada"
            autoLayout lr 150 50
            title "Fluxo principal"
        }

        // 5. Visões por status (derivadas da visão completa)
        filtered "App-Completo" include "Pronto" "Status-Pronto" "Componentes prontos."
        filtered "App-Completo" include "EmAndamento" "Status-EmAndamento" "Componentes em andamento."
        filtered "App-Completo" include "Planejado" "Status-Planejado" "Só no design."
