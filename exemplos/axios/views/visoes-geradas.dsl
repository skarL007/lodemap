// Gerado por scripts/esqueleto.py a partir de .lodemap/decisoes-modelo.json. Fluxos: views/visoes.dsl.

systemContext sistema "Contexto" "Who uses the system and what it talks to." {
    include *
    autoLayout lr 150 50
    title "Context"
}

container sistema "Containers" "The processes and the data." {
    include *
    autoLayout lr 150 50
    title "Containers"
}

component axiosLib "Componentes-axiosLib" "Every component of axios package." {
    include *
    autoLayout lr 150 50
    title "axios package: components"
}

component axiosLib "Area-axiosLib-Client" "Components of the Client and configuration area in axios package." {
    include "element.tag==AreaClient"
    autoLayout lr 150 50
    title "axios package: Client and configuration"
}

component axiosLib "Area-axiosLib-Pipeline" "Components of the Request pipeline area in axios package." {
    include "element.tag==AreaPipeline"
    autoLayout lr 150 50
    title "axios package: Request pipeline"
}

component axiosLib "Area-axiosLib-Adapters" "Components of the Transport adapters area in axios package." {
    include "element.tag==AreaAdapters"
    autoLayout lr 150 50
    title "axios package: Transport adapters"
}

component axiosLib "Area-axiosLib-UrlHeaders" "Components of the URLs and headers area in axios package." {
    include "element.tag==AreaUrlHeaders"
    autoLayout lr 150 50
    title "axios package: URLs and headers"
}

component axiosLib "Area-axiosLib-Payload" "Components of the Payload encoding area in axios package." {
    include "element.tag==AreaPayload"
    autoLayout lr 150 50
    title "axios package: Payload encoding"
}

component axiosLib "Area-axiosLib-Streaming" "Components of the Streams and progress area in axios package." {
    include "element.tag==AreaStreaming"
    autoLayout lr 150 50
    title "axios package: Streams and progress"
}

component axiosLib "Area-axiosLib-Errors" "Components of the Errors and cancellation area in axios package." {
    include "element.tag==AreaErrors"
    autoLayout lr 150 50
    title "axios package: Errors and cancellation"
}

component axiosLib "Area-axiosLib-Platform" "Components of the Platform and utilities area in axios package." {
    include "element.tag==AreaPlatform"
    autoLayout lr 150 50
    title "axios package: Platform and utilities"
}
