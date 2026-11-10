// Gerado por scripts/esqueleto.py a partir de .lodemap/decisoes-modelo.json. Fluxos: views/visoes.dsl.

systemContext sistema "Contexto" "Quem usa o sistema e com o que ele conversa." {
    include *
    autoLayout lr 150 50
    title "Contexto"
}

container sistema "Containers" "Os processos e os dados." {
    include *
    autoLayout lr 150 50
    title "Containers"
}

component axiosLib "Componentes-axiosLib" "Todos os componentes de Pacote axios." {
    include *
    autoLayout lr 150 50
    title "Pacote axios: componentes"
}

component axiosLib "Area-axiosLib-Client" "Componentes da área Cliente e configuração em Pacote axios." {
    include "element.tag==AreaClient"
    autoLayout lr 150 50
    title "Pacote axios: Cliente e configuração"
}

component axiosLib "Area-axiosLib-Pipeline" "Componentes da área Pipeline da requisição em Pacote axios." {
    include "element.tag==AreaPipeline"
    autoLayout lr 150 50
    title "Pacote axios: Pipeline da requisição"
}

component axiosLib "Area-axiosLib-Adapters" "Componentes da área Adaptadores de transporte em Pacote axios." {
    include "element.tag==AreaAdapters"
    autoLayout lr 150 50
    title "Pacote axios: Adaptadores de transporte"
}

component axiosLib "Area-axiosLib-UrlHeaders" "Componentes da área URLs e cabeçalhos em Pacote axios." {
    include "element.tag==AreaUrlHeaders"
    autoLayout lr 150 50
    title "Pacote axios: URLs e cabeçalhos"
}

component axiosLib "Area-axiosLib-Payload" "Componentes da área Codificação do corpo em Pacote axios." {
    include "element.tag==AreaPayload"
    autoLayout lr 150 50
    title "Pacote axios: Codificação do corpo"
}

component axiosLib "Area-axiosLib-Streaming" "Componentes da área Streams e progresso em Pacote axios." {
    include "element.tag==AreaStreaming"
    autoLayout lr 150 50
    title "Pacote axios: Streams e progresso"
}

component axiosLib "Area-axiosLib-Errors" "Componentes da área Erros e cancelamento em Pacote axios." {
    include "element.tag==AreaErrors"
    autoLayout lr 150 50
    title "Pacote axios: Erros e cancelamento"
}

component axiosLib "Area-axiosLib-Platform" "Componentes da área Plataforma e utilitários em Pacote axios." {
    include "element.tag==AreaPlatform"
    autoLayout lr 150 50
    title "Pacote axios: Plataforma e utilitários"
}
