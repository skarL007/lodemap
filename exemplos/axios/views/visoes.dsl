        !include visoes-geradas.dsl

        // Visões estáticas em views/visoes-geradas.dsl (esqueleto.py). Aqui ficam só os fluxos (visões
        // dinâmicas), escritos pelo modelador. Cada passo precisa de uma relação que exista no modelo.
        // O Structurizr numera os passos automaticamente, na ordem em que são escritos.

        dynamic axiosLib "FlowRequestLifecycle" "A vida de uma requisição no Node.js, da chamada da aplicação até a resposta devolvida." {
            title "Fluxo: ciclo de vida da requisição (Node.js)"
            devApp -> libAxios "Chama axios(config) ou axios.get(url) na instância padrão"
            libAxios -> coreAxios "Repassa a chamada ao método request vinculado da instância"
            coreAxios -> coreMergeConfig "Mescla os padrões da instância com a configuração da chamada"
            coreAxios -> coreInterceptorManager "Executa os interceptors de requisição, do último registrado para o primeiro"
            coreAxios -> coreDispatchRequest "Entrega a configuração mesclada para o despacho"
            coreDispatchRequest -> coreTransformData "Executa transformRequest para serializar o corpo e definir o content-type"
            coreDispatchRequest -> adaptersAdapters "Resolve config.adapter ou a lista padrão em um único adaptador"
            coreDispatchRequest -> adaptersHttp "Invoca o adaptador escolhido, aqui o adaptador http do Node.js"
            adaptersHttp -> nodeRuntime "Envia a requisição pelo socket http, https ou http2"
            nodeRuntime -> remoteServer "Leva a requisição ao servidor e traz a resposta de volta"
            adaptersHttp -> coreSettle "Resolve a promise pelo status da resposta; status fora do intervalo rejeitam"
            coreDispatchRequest -> coreTransformData "Executa transformResponse para interpretar o corpo, por exemplo JSON"
            coreAxios -> coreInterceptorManager "Executa os interceptors de resposta na ordem de registro e depois devolve o resultado a quem chamou"
            autoLayout lr 150 50
        }

        dynamic axiosLib "FlowAdapterSelection" "Como o axios escolhe o transporte do ambiente atual: xhr nos navegadores, http no Node.js, fetch como alternativa." {
            title "Fluxo: seleção do adaptador por ambiente"
            coreDispatchRequest -> defaultsIndex "Lê a lista padrão de adaptadores, ['xhr', 'http', 'fetch']"
            coreDispatchRequest -> adaptersAdapters "Chama getAdapter com config.adapter ou a lista padrão"
            adaptersAdapters -> libUtils "Percorre os nomes e verifica se cada entrada é um nome, uma função ou um adaptador personalizado"
            adaptersAdapters -> adaptersXhr "Tenta o xhr primeiro: ele só existe onde há XMLHttpRequest (navegadores)"
            adaptersAdapters -> adaptersHttp "Tenta o http em seguida: ele só existe no Node.js, e os bundles de navegador recebem um módulo nulo"
            adaptersAdapters -> adaptersFetch "Tenta o fetch por último: ele existe onde há os globais do fetch (Deno, Bun, workers)"
            adaptersAdapters -> coreAxiosError "Lança um erro de adaptador desconhecido ou não suportado se nada estiver disponível"
            coreDispatchRequest -> adaptersHttp "Invoca o primeiro adaptador disponível; aqui Node.js, portanto http"
            autoLayout lr 150 50
        }

        dynamic axiosLib "FlowNodeHttpRequest" "O que o adaptador http do Node.js faz por uma requisição: URL e cabeçalhos, proxy, limite de taxa e progresso do upload, e a resposta descomprimida." {
            title "Fluxo: requisição pelo adaptador http do Node.js"
            coreDispatchRequest -> adaptersHttp "Invoca o adaptador http do Node.js com a configuração transformada"
            adaptersHttp -> coreBuildFullPath "Junta baseURL e url na URL da requisição"
            adaptersHttp -> helpersBuildURL "Acrescenta à URL os params serializados"
            adaptersHttp -> coreAxiosHeaders "Monta os cabeçalhos da requisição"
            adaptersHttp -> helpersShouldBypassProxy "Confere o host com as regras de NO_PROXY"
            adaptersHttp -> proxyServer "Roteia a requisição pelo proxy quando há um configurado ou definido no ambiente"
            adaptersHttp -> helpersAxiosTransformStream "Limita a taxa do stream de upload quando maxRate está definido"
            adaptersHttp -> helpersProgressEventReducer "Emite eventos de progresso do upload enquanto o corpo é escrito"
            adaptersHttp -> nodeRuntime "Envia a requisição; os redirecionamentos são seguidos pelo wrapper follow-redirects até maxRedirects"
            nodeRuntime -> remoteServer "Leva a requisição e devolve o stream da resposta"
            adaptersHttp -> helpersZlibHeaderTransformStream "Repara streams deflate crus antes de descomprimi-los com zlib"
            adaptersHttp -> helpersProgressEventReducer "Emite eventos de progresso do download enquanto a resposta é lida"
            adaptersHttp -> coreSettle "Resolve a promise com a resposta, ou rejeita diante de um status inválido ou do limite maxContentLength"
            autoLayout lr 150 50
        }

        dynamic axiosLib "FlowCancelTimeout" "Como um cancelamento ou um timeout interrompe uma requisição no adaptador fetch e vira um CanceledError ou um AxiosError." {
            title "Fluxo: cancelamento e timeout"
            coreDispatchRequest -> cancelCancelToken "Pergunta ao token se o cancelamento já foi solicitado, antes e depois de o adaptador rodar"
            coreDispatchRequest -> adaptersFetch "Invoca o adaptador fetch com o signal, o cancelToken e o timeout da configuração"
            adaptersFetch -> cancelCancelToken "Converte o token de cancelamento em um sinal de cancelamento"
            adaptersFetch -> helpersComposeSignals "Mescla o sinal do usuário, o sinal do token e o timeout em um único sinal"
            helpersComposeSignals -> cancelCanceledError "Aborta com um CanceledError quando o sinal do usuário ou o token disparam"
            helpersComposeSignals -> coreAxiosError "Aborta com um erro de timeout ECONNABORTED quando o tempo se esgota"
            adaptersFetch -> fetchApi "Envia o fetch com o sinal composto; o ambiente o rejeita com um AbortError quando o sinal dispara"
            adaptersFetch -> coreAxiosError "Relança o motivo composto, ou envolve qualquer outra falha como erro de rede"
            coreDispatchRequest -> cancelIsCancel "Distingue um cancelamento de outras rejeições antes de o erro chegar a quem chamou"
            autoLayout lr 150 50
        }

        dynamic axiosLib "FlowMultipartBody" "Como um corpo em objeto ou FormData vira uma requisição multipart no Node.js: serialização, política de cabeçalhos e a codificação em stream." {
            title "Fluxo: corpo multipart/FormData"
            coreDispatchRequest -> coreTransformData "Executa transformRequest nos dados da requisição"
            coreTransformData -> defaultsIndex "Recorre às transformações padrão, que escolhem o serializador do corpo pelo content-type"
            defaultsIndex -> helpersToFormData "Serializa um objeto simples em um FormData para multipart/form-data"
            helpersToFormData -> classesFormData3 "Cria a instância do form-data porque o Node.js aqui não tem FormData nativo"
            coreDispatchRequest -> adaptersHttp "Invoca o adaptador http do Node.js com o corpo FormData"
            adaptersHttp -> coreSetFormDataHeaders "Copia os cabeçalhos do FormData (boundary) para a requisição conforme formDataHeaderPolicy"
            adaptersHttp -> helpersFormDataToStream "Envolve um FormData compatível com a especificação em um stream de bytes multipart"
            helpersFormDataToStream -> platformIndex "Gera o boundary multipart"
            helpersFormDataToStream -> helpersReadBlob "Lê as partes Blob e File bloco a bloco"
            adaptersHttp -> helpersProgressEventReducer "Emite o progresso do upload enquanto o stream é enviado"
            adaptersHttp -> nodeRuntime "Escreve o stream multipart no socket"
            autoLayout lr 150 50
        }

        dynamic axiosLib "FlowUrlAndHeaders" "Como a URL e os cabeçalhos da requisição são resolvidos antes de o adaptador fetch enviá-la." {
            title "Fluxo: resolução de URL e cabeçalhos"
            adaptersFetch -> helpersResolveConfig "Resolve URL, cabeçalhos, autenticação e política do corpo a partir da configuração"
            helpersResolveConfig -> coreMergeConfig "Mescla a configuração bruta"
            helpersResolveConfig -> coreBuildFullPath "Resolve a URL completa"
            coreBuildFullPath -> helpersIsAbsoluteURL "Dispensa a junção quando a url já é absoluta"
            coreBuildFullPath -> helpersCombineURLs "Junta baseURL e a url relativa, removendo barras duplicadas"
            coreBuildFullPath -> coreAxiosError "Lança erro em URLs inseguras, ocultando quaisquer credenciais"
            helpersResolveConfig -> helpersBuildURL "Acrescenta os params serializados como query string"
            helpersBuildURL -> helpersAxiosURLSearchParams "Codifica os params quando o URLSearchParams nativo não serve"
            helpersResolveConfig -> coreAxiosHeaders "Monta os cabeçalhos mesclados da requisição"
            coreAxiosHeaders -> helpersSanitizeHeaderValue "Remove caracteres inseguros dos valores de cabeçalho"
            helpersResolveConfig -> helpersIsURLSameOrigin "Verifica a origem antes de o cabeçalho XSRF ser adicionado"
            helpersResolveConfig -> helpersCookies "Lê o cookie XSRF em ambientes de navegador padrão"
            autoLayout lr 150 50
        }
