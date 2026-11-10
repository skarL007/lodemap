        // Relações com pessoas e sistemas externos, mais as setas de nível de sistema e de container de que as visões
        // Contexto e Containers precisam (!impliedRelationships é false, então elas não são derivadas).
        // As setas entre componentes são geradas por `esqueleto.py renderizar` em relacoes-componentes.dsl.
        // Formato: origem -> destino "verbo no presente" "tecnologia" "TagOpcional"

        // Contexto (nível de sistema)
        devApp -> sistema "Instala e chama para enviar requisições HTTP" "pacote npm, API JavaScript"
        sistema -> nodeRuntime "Abre conexões HTTP, HTTP/2 e TLS por meio de" "Node.js http, https, http2"
        sistema -> browserXhr "Envia as requisições do navegador por meio de" "XMLHttpRequest"
        sistema -> fetchApi "Envia requisições e transmite corpos em stream por meio de" "fetch"
        sistema -> proxyServer "Roteia requisições por meio de, quando configurado" "proxy HTTP"
        nodeRuntime -> remoteServer "Leva a requisição e a resposta de e para" "HTTP/1.1, HTTP/2, TLS"
        browserXhr -> remoteServer "Leva a requisição e a resposta de e para" "HTTP, CORS"
        fetchApi -> remoteServer "Leva a requisição e a resposta de e para" "HTTP, CORS"
        proxyServer -> remoteServer "Encaminha a requisição para" "proxy HTTP"

        // Containers
        devApp -> axiosLib "Importa e chama no próprio processo" "módulo ES, CommonJS ou UMD"
        axiosLib -> nodeRuntime "Controla os módulos http, https, http2, zlib e stream de" "Node.js APIs"
        axiosLib -> browserXhr "Envia e aborta requisições com" "XMLHttpRequest"
        axiosLib -> fetchApi "Envia requisições e transmite corpos em stream com" "fetch"
        axiosLib -> proxyServer "Roteia requisições por meio de, quando configurado" "proxy HTTP"

        // Componentes com pessoas e sistemas externos
        devApp -> libAxios "Chama axios(), axios.get() e os métodos da instância de" "API JavaScript"
        adaptersHttp -> nodeRuntime "Envia requisições pelos sockets http, https e http2 de" "Node.js http, https, http2"
        adaptersHttp -> proxyServer "Roteia requisições por meio de, quando configurado ou definido no ambiente" "proxy-from-env, https-proxy-agent"
        helpersHttp2Sessions -> nodeRuntime "Abre e mantém sessões HTTP/2 com" "Node.js http2"
        adaptersXhr -> browserXhr "Envia a requisição e escuta os eventos de progresso e de cancelamento de" "XMLHttpRequest"
        adaptersFetch -> fetchApi "Envia a requisição e lê a resposta em stream de" "fetch, Request, Response"

        !include relacoes-componentes.dsl
