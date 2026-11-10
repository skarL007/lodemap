workspace "{{PROJETO}}" "{{DESCRICAO}}" {

    !identifiers flat
    !impliedRelationships false

    !docs docs
    // ADRs no formato único do Lodemap (cabeçalho YAML); o importador "madr" lê status e date do cabeçalho.
    !adrs adrs madr

    // Base dos links "abrir no GitHub" que o enriquecer.groovy põe em cada elemento com "codigo".
    // Use "-" se o repositório não tiver remoto (o DSL não aceita valor vazio).
    properties {
        "repo.blob" "{{REPO_BLOB}}"
    }

    model {
        !include model/pessoas-externos.dsl

        sistema = softwareSystem "{{PROJETO}}" "{{DESCRICAO}}" "Pronto" {
            !include model/containers.dsl
        }

        !include model/relacoes.dsl
    }

    views {
        !include views/visoes.dsl

        // Perspectivas, links para o código e passos de animação derivados do modelo.
        !script scripts/enriquecer.groovy

        styles {
            !include views/estilos.dsl
        }
    }
}
