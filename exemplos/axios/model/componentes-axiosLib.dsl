// Gerado por scripts/esqueleto.py a partir de .lodemap/decisoes-modelo.json. Edite o JSON, não este arquivo.

group "Cliente e configuração" {
    libAxios = component "Fábrica da instância padrão" "Cria a instância padrão do axios e a fábrica de instâncias personalizadas, reexportando as APIs de cancelamento, erro e utilitários por um único ponto de entrada, para que quem consome importe um só módulo." "JavaScript" "Pronto,AreaClient" {
        properties {
            "status" "Pronto"
            "area" "AreaClient"
            "codigo" "lib/axios.js"
        }
    }
    coreMethodList = component "Lista de métodos HTTP suportados" "Lista o conjunto congelado de nomes de métodos HTTP que ganham funções de atalho, incluindo PURGE, LINK e QUERY, para que acrescentar um método exija uma única edição num único lugar." "JavaScript" "Pronto,AreaClient,Dados" {
        properties {
            "status" "Pronto"
            "area" "AreaClient"
            "codigo" "lib/core/methodList.js"
        }
    }
    defaultsIndex = component "Objeto de configuração padrão" "Define a configuração embutida, incluindo a leitura de JSON, as funções de transformação, os adaptadores e o validateStatus, e escolhe os codificadores de formulário adequados, para que toda instância parta de uma mesma base." "JavaScript" "Pronto,AreaClient" {
        properties {
            "status" "Pronto"
            "area" "AreaClient"
            "codigo" "lib/defaults/index.js"
        }
    }
    defaultsTransitional = component "Flags de comportamento transitório" "Guarda chaves booleanas para comportamentos legados, como a leitura silenciosa de JSON e a ordem dos interceptors, para que os mantenedores mudem os padrões num só lugar durante uma migração." "JavaScript" "Pronto,AreaClient,Dados" {
        properties {
            "status" "Pronto"
            "area" "AreaClient"
            "codigo" "lib/defaults/transitional.js"
        }
    }
}

group "Pipeline da requisição" {
    coreAxios = component "Classe de orquestração de requisições" "Guarda os padrões e os interceptors de cada instância, mescla a configuração de cada chamada e gera os métodos de atalho, para que toda requisição passe por um único pipeline ordenado." "JavaScript" "Pronto,AreaPipeline" {
        properties {
            "status" "Pronto"
            "area" "AreaPipeline"
            "codigo" "lib/core/Axios.js"
        }
    }
    coreInterceptorManager = component "Gerenciador da pilha de interceptors" "Mantém os interceptors de requisição e de resposta numa pilha ordenada, com as opções synchronous e runWhen, e ignora entradas removidas durante a execução, para que remoções no meio de uma requisição não quebrem a cadeia." "JavaScript" "Pronto,AreaPipeline" {
        properties {
            "status" "Pronto"
            "area" "AreaPipeline"
            "codigo" "lib/core/InterceptorManager.js"
        }
    }
    coreDispatchRequest = component "Despacho da requisição e transformações" "Executa as transformações da requisição, achata a configuração, verifica o cancelamento, chama o adaptador escolhido e depois transforma a resposta, para que todo adaptador receba a mesma entrada preparada." "JavaScript" "Pronto,AreaPipeline" {
        properties {
            "status" "Pronto"
            "area" "AreaPipeline"
            "codigo" "lib/core/dispatchRequest.js"
        }
    }
    coreMergeConfig = component "Mescla de configuração com precedência" "Mescla dois objetos de configuração num resultado sem protótipo, com regras por chave para cabeçalhos, autenticação e URLs, para que as camadas de configuração posteriores sobrescrevam as anteriores sem vazamento de protótipo." "JavaScript" "Pronto,AreaPipeline" {
        properties {
            "status" "Pronto"
            "area" "AreaPipeline"
            "codigo" "lib/core/mergeConfig.js"
        }
    }
    coreSettle = component "Resolução da promise pelo status" "Resolve ou rejeita a promise da requisição aplicando validateStatus, mapeando 4xx para ERR_BAD_REQUEST e as demais falhas para ERR_BAD_RESPONSE, para que os adaptadores compartilhem uma única regra de status." "JavaScript" "Pronto,AreaPipeline,Gate" {
        properties {
            "status" "Pronto"
            "area" "AreaPipeline"
            "codigo" "lib/core/settle.js"
        }
    }
    coreTransformData = component "Transformações de requisição e resposta" "Executa em ordem as funções transformRequest ou transformResponse configuradas, com cabeçalhos normalizados, para que cada função veja o mesmo objeto de cabeçalhos e o mesmo código de status." "JavaScript" "Pronto,AreaPipeline" {
        properties {
            "status" "Pronto"
            "area" "AreaPipeline"
            "codigo" "lib/core/transformData.js"
        }
    }
    helpersResolveConfig = component "Resolvedor da configuração da requisição" "Transforma a configuração mesclada em URL, cabeçalhos e corpo finais aplicando autenticação básica, XSRF e cabeçalhos de FormData, para que os adaptadores recebam uma descrição da requisição pronta para envio." "JavaScript" "Pronto,AreaPipeline" {
        properties {
            "status" "Pronto"
            "area" "AreaPipeline"
            "codigo" "lib/helpers/resolveConfig.js"
        }
    }
    helpersValidator = component "Validador de esquema de opções" "Verifica os tipos das opções contra um esquema e emite avisos únicos de descontinuação para opções transitórias removidas, para que instâncias mal configuradas falhem cedo com mensagens claras." "JavaScript" "Pronto,AreaPipeline,Gate" {
        properties {
            "status" "Pronto"
            "area" "AreaPipeline"
            "codigo" "lib/helpers/validator.js"
        }
    }
}

group "Adaptadores de transporte" {
    adaptersAdapters = component "Registro de seleção de adaptadores" "Escolhe o primeiro transporte utilizável de uma lista de nomes ou funções e rejeita os desconhecidos, para que o Axios falhe cedo e com um motivo claro quando nenhum adaptador serve ao ambiente de execução." "JavaScript" "Pronto,AreaAdapters" {
        properties {
            "status" "Pronto"
            "area" "AreaAdapters"
            "codigo" "lib/adapters/adapters.js"
        }
    }
    adaptersFetch = component "Adaptador de transporte Fetch" "Envia requisições pela Fetch API com corpos em stream e acompanhamento de progresso, para que ambientes sem XMLHttpRequest, como workers e hosts de borda, ainda possam usar o Axios." "JavaScript (Fetch API)" "Pronto,AreaAdapters" {
        properties {
            "status" "Pronto"
            "area" "AreaAdapters"
            "codigo" "lib/adapters/fetch.js"
        }
    }
    adaptersHttp = component "Transporte HTTP do Node" "Executa requisições com os módulos http e https do Node, acrescentando túnel de proxy, tratamento de redirecionamentos, limites de taxa e descompressão, que os adaptadores do navegador não oferecem." "JavaScript (só Node)" "Pronto,AreaAdapters" {
        properties {
            "status" "Pronto"
            "area" "AreaAdapters"
            "codigo" "lib/adapters/http.js"
        }
    }
    adaptersXhr = component "Transporte XHR do navegador" "Controla o XMLHttpRequest nos navegadores e converte timeouts, cancelamentos e respostas com status 0 em erros do Axios, porque o XHR é o único transporte com progresso de upload nativo ali." "JavaScript (só navegador)" "Pronto,AreaAdapters" {
        properties {
            "status" "Pronto"
            "area" "AreaAdapters"
            "codigo" "lib/adapters/xhr.js"
        }
    }
    helpersHttp2Sessions = component "Pool de sessões HTTP/2" "Guarda em cache sessões HTTP/2 por authority e conjunto de opções, reaproveitando conexões vivas e expirando as ociosas após um tempo, para que requisições repetidas evitem novos handshakes TLS." "JavaScript (só Node)" "Pronto,AreaAdapters" {
        properties {
            "status" "Pronto"
            "area" "AreaAdapters"
            "codigo" "lib/helpers/Http2Sessions.js"
        }
    }
    helpersCallbackify = component "Conversor de async para callback" "Converte uma função assíncrona em uma de estilo callback, com um redutor opcional de resultado, para que o adaptador HTTP possa envolver uma resolução de DNS assíncrona personalizada para os sockets do Node, que usam callbacks." "JavaScript" "Pronto,AreaAdapters" {
        properties {
            "status" "Pronto"
            "area" "AreaAdapters"
            "codigo" "lib/helpers/callbackify.js"
        }
    }
    helpersShouldBypassProxy = component "Verificador de exceção de proxy" "Decide se um host dispensa o proxy canonicalizando formas abreviadas, octais e hexadecimais de IPv4 e desfazendo o mapeamento de IPv6 para IPv4, para que as regras de exceção não sejam burladas por grafias alternativas." "JavaScript" "Pronto,AreaAdapters" {
        properties {
            "status" "Pronto"
            "area" "AreaAdapters"
            "codigo" "lib/helpers/shouldBypassProxy.js"
        }
    }
}

group "URLs e cabeçalhos" {
    coreAxiosHeaders = component "Mapa de cabeçalhos sem distinção de caixa" "Guarda os cabeçalhos com nomes normalizados e oferece set, get e merge, rejeitando nomes ou valores inválidos, porque cabeçalhos em objeto puro duplicam chaves em silêncio quando a caixa varia." "JavaScript" "Pronto,AreaUrlHeaders" {
        properties {
            "status" "Pronto"
            "area" "AreaUrlHeaders"
            "codigo" "lib/core/AxiosHeaders.js"
        }
    }
    coreAssertParamsAcyclic = component "Guarda de ciclos nos params" "Percorre os params mesclados de forma iterativa e lança ERR_BAD_OPTION_VALUE diante de ciclos reais, acompanhando o caminho ativo para que objetos compartilhados e acíclicos ainda passem, de modo que params circulares falhem cedo com um erro claro em vez de chegar ao serializador da query." "JavaScript" "Pronto,AreaUrlHeaders" {
        properties {
            "status" "Pronto"
            "area" "AreaUrlHeaders"
            "codigo" "lib/core/assertParamsAcyclic.js"
        }
    }
    coreBuildFullPath = component "Junção da URL base" "Junta baseURL com caminhos relativos e recusa URLs absolutas malformadas ou não permitidas, ocultando credenciais e segredos da query na mensagem, para que os erros sejam seguros de registrar em log." "JavaScript" "Pronto,AreaUrlHeaders,Gate" {
        properties {
            "status" "Pronto"
            "area" "AreaUrlHeaders"
            "codigo" "lib/core/buildFullPath.js"
        }
    }
    helpersBuildURL = component "Construtor da query string" "Acrescenta à URL os params serializados mantendo legíveis caracteres reservados como dois-pontos e vírgula, e respeita serializadores personalizados, para que as query strings geradas fiquem compactas e previsíveis." "JavaScript" "Pronto,AreaUrlHeaders" {
        properties {
            "status" "Pronto"
            "area" "AreaUrlHeaders"
            "codigo" "lib/helpers/buildURL.js"
        }
    }
    helpersCombineURLs = component "Junção de segmentos de URL" "Junta uma URL base e um caminho relativo com exatamente uma barra, removendo as barras finais da base, para que os valores de baseURL e url nunca gerem separadores duplicados ou ausentes." "JavaScript" "Pronto,AreaUrlHeaders" {
        properties {
            "status" "Pronto"
            "area" "AreaUrlHeaders"
            "codigo" "lib/helpers/combineURLs.js"
        }
    }
    helpersCookies = component "Leitura e escrita de cookies" "Lê e grava cookies de XSRF por document.cookie ou pela Cookie Store API, dividindo o texto em ponto e vírgula em vez de montar uma regex com o nome, para evitar ReDoS e correspondências com o cookie errado." "JavaScript" "Pronto,AreaUrlHeaders" {
        properties {
            "status" "Pronto"
            "area" "AreaUrlHeaders"
            "codigo" "lib/helpers/cookies.js"
        }
    }
    helpersIsAbsoluteURL = component "Detector de URL absoluta" "Detecta uma URL absoluta pela sintaxe de esquema da RFC 3986 ou por uma barra dupla inicial, para que URLs relativas ao protocolo dispensem a junção com baseURL." "JavaScript" "Pronto,AreaUrlHeaders" {
        properties {
            "status" "Pronto"
            "area" "AreaUrlHeaders"
            "codigo" "lib/helpers/isAbsoluteURL.js"
        }
    }
    helpersIsURLSameOrigin = component "Verificação de mesma origem" "Compara protocolo, host e porta com a origem da página, para que o cabeçalho XSRF seja enviado só a URLs da mesma origem nos navegadores padrão." "JavaScript" "Pronto,AreaUrlHeaders,Gate" {
        properties {
            "status" "Pronto"
            "area" "AreaUrlHeaders"
            "codigo" "lib/helpers/isURLSameOrigin.js"
        }
    }
    helpersNormalizeURLForProtocolCheck = component "Normalizador de protocolo da URL" "Remove caracteres de controle iniciais e tabulações ou quebras de linha embutidas como o parser WHATWG faz, para que a verificação de protocolo enxergue o mesmo esquema que o navegador usará." "JavaScript" "Pronto,AreaUrlHeaders" {
        properties {
            "status" "Pronto"
            "area" "AreaUrlHeaders"
            "codigo" "lib/helpers/normalizeURLForProtocolCheck.js"
        }
    }
    helpersParseHeaders = component "Analisador de cabeçalhos brutos" "Analisa o texto bruto de cabeçalhos em um objeto e descarta duplicatas de cabeçalhos que o próprio Node ignora, para que os valores mesclados coincidam com o que a camada HTTP do Node expõe." "JavaScript" "Pronto,AreaUrlHeaders" {
        properties {
            "status" "Pronto"
            "area" "AreaUrlHeaders"
            "codigo" "lib/helpers/parseHeaders.js"
        }
    }
    helpersParseProtocol = component "Extrator do esquema da URL" "Extrai o esquema de uma string de URL com uma única regex e devolve uma string vazia quando não encontra nenhum, para que os adaptadores possam escolher o transporte pelo protocolo." "JavaScript" "Pronto,AreaUrlHeaders" {
        properties {
            "status" "Pronto"
            "area" "AreaUrlHeaders"
            "codigo" "lib/helpers/parseProtocol.js"
        }
    }
    helpersSanitizeHeaderValue = component "Saneador de valores de cabeçalho" "Apara espaços e remove bytes de controle dos valores de cabeçalho, e os converte em strings de bytes para o fetch, para que caracteres inválidos não quebrem a requisição nem injetem cabeçalhos." "JavaScript" "Pronto,AreaUrlHeaders,Gate" {
        properties {
            "status" "Pronto"
            "area" "AreaUrlHeaders"
            "codigo" "lib/helpers/sanitizeHeaderValue.js"
        }
    }
}

group "Codificação do corpo" {
    coreCreateMultipartBody = component "Construtor de corpo multipart" "Monta um Blob multipart a partir de FormData para o adaptador fetch, gerando um boundary quando nenhum é informado e traduzindo falhas de serialização em códigos do AxiosError (ERR_NOT_SUPPORT, ERR_BAD_OPTION_VALUE, ERR_BAD_REQUEST), para que uploads possam ter tamanho limitado ou ser enviados em stream." "JavaScript" "Pronto,AreaPayload" {
        properties {
            "status" "Pronto"
            "area" "AreaPayload"
            "codigo" "lib/core/createMultipartBody.js"
        }
    }
    coreSetFormDataHeaders = component "Política de cabeçalhos do FormData" "Copia para a requisição os cabeçalhos gerados pelo FormData, todos ou só content-type e content-length conforme formDataHeaderPolicy, para que os boundaries multipart se apliquem de forma previsível." "JavaScript" "Pronto,AreaPayload" {
        properties {
            "status" "Pronto"
            "area" "AreaPayload"
            "codigo" "lib/core/setFormDataHeaders.js"
        }
    }
    helpersAxiosURLSearchParams = component "Classe substituta de URLSearchParams" "Classe substituta de URLSearchParams que codifica os pares em percent-encoding com mais no lugar de espaço, usada onde a classe nativa não existe, para que a codificação de query e de formulário continue consistente." "JavaScript" "Pronto,AreaPayload" {
        properties {
            "status" "Pronto"
            "area" "AreaPayload"
            "codigo" "lib/helpers/AxiosURLSearchParams.js"
        }
    }
    helpersEstimateDataURLDecodedBytes = component "Estimador do tamanho de URL de dados" "Estima o tamanho em bytes decodificados de URLs data: sem alocar buffers, para que maxContentLength rejeite cargas grandes demais antes de qualquer memória ser reservada." "JavaScript" "Pronto,AreaPayload" {
        properties {
            "status" "Pronto"
            "area" "AreaPayload"
            "codigo" "lib/helpers/estimateDataURLDecodedBytes.js"
        }
    }
    helpersFormDataToBlob = component "FormData para Blob" "Converte FormData em um Blob multipart nativo, contando os bytes UTF-8 dos campos sem cópias de codificação e impondo o limite de tamanho do corpo antes de montá-lo, e compõe dados de File existentes por referência, para que uploads grandes evitem buffers extras." "JavaScript" "Pronto,AreaPayload" {
        properties {
            "status" "Pronto"
            "area" "AreaPayload"
            "codigo" "lib/helpers/formDataToBlob.js"
        }
    }
    helpersFormDataToJSON = component "Conversor de FormData para JSON" "Transforma as entradas de FormData em objetos aninhados interpretando caminhos com colchetes e pontos, com limite de profundidade e leitura que falha cedo, para que envios de formulário virem JSON com segurança." "JavaScript" "Pronto,AreaPayload" {
        properties {
            "status" "Pronto"
            "area" "AreaPayload"
            "codigo" "lib/helpers/formDataToJSON.js"
        }
    }
    helpersFromDataURI = component "Decodificador de data URI" "Decodifica data: URIs da RFC 2397 em um Buffer ou Blob, aplicando o mediatype padrão da especificação, para que cargas embutidas funcionem no Node como nos navegadores." "JavaScript" "Pronto,AreaPayload" {
        properties {
            "status" "Pronto"
            "area" "AreaPayload"
            "codigo" "lib/helpers/fromDataURI.js"
        }
    }
    helpersReadBlob = component "Leitor de blocos de Blob" "Lê um Blob como iterador assíncrono usando stream, arrayBuffer ou um iterador, o que estiver disponível, para que a codificação multipart funcione em ambientes com APIs de Blob diferentes." "JavaScript" "Pronto,AreaPayload" {
        properties {
            "status" "Pronto"
            "area" "AreaPayload"
            "codigo" "lib/helpers/readBlob.js"
        }
    }
    helpersToFormData = component "Codificador de objeto para FormData" "Serializa objetos aninhados em FormData ou URLSearchParams com chaves entre colchetes e limite de profundidade de 100, impondo esse limite para que cargas muito profundas falhem com um erro claro." "JavaScript" "Pronto,AreaPayload" {
        properties {
            "status" "Pronto"
            "area" "AreaPayload"
            "codigo" "lib/helpers/toFormData.js"
        }
    }
    helpersToURLEncodedForm = component "Codificador de corpo urlencoded" "Codifica objetos como application/x-www-form-urlencoded, gravando Buffers do Node em base64, para que envios de formulário mantenham valores binários intactos sem um serializador à parte." "JavaScript" "Pronto,AreaPayload" {
        properties {
            "status" "Pronto"
            "area" "AreaPayload"
            "codigo" "lib/helpers/toURLEncodedForm.js"
        }
    }
}

group "Streams e progresso" {
    helpersAxiosTransformStream = component "Stream de transformação com limite de taxa" "Limita a vazão e emite progresso a partir de um stream Transform do Node usando uma janela de tempo deslizante, para que uploads e downloads possam ter a taxa limitada pela opção maxRate." "JavaScript (só Node)" "Pronto,AreaStreaming" {
        properties {
            "status" "Pronto"
            "area" "AreaStreaming"
            "codigo" "lib/helpers/AxiosTransformStream.js"
        }
    }
    helpersZlibHeaderTransformStream = component "Stream de reparo do cabeçalho zlib" "Acrescenta um cabeçalho zlib padrão quando um corpo deflate não tem um, porque alguns servidores enviam deflate cru que o inflate do Node rejeita, para que a descompressão ainda funcione." "JavaScript (só Node)" "Pronto,AreaStreaming" {
        properties {
            "status" "Pronto"
            "area" "AreaStreaming"
            "codigo" "lib/helpers/ZlibHeaderTransformStream.js"
        }
    }
    helpersFormDataToStream = component "Stream de formulário multipart" "Envia as partes do FormData como bytes multipart em stream, com boundary gerado e tamanho calculado, para que uploads grandes cheguem à pilha HTTP do Node sem manter o corpo inteiro em buffer." "JavaScript (só Node)" "Pronto,AreaStreaming" {
        properties {
            "status" "Pronto"
            "area" "AreaStreaming"
            "codigo" "lib/helpers/formDataToStream.js"
        }
    }
    helpersProgressEventReducer = component "Redutor de eventos de progresso com limite" "Limita as contagens de bytes carregados, calcula taxa e tempo restante com um medidor de velocidade e limita a frequência dos callbacks, para que os ouvintes de progresso recebam eventos estáveis e precisos em vez de rajadas brutas." "JavaScript" "Pronto,AreaStreaming" {
        properties {
            "status" "Pronto"
            "area" "AreaStreaming"
            "codigo" "lib/helpers/progressEventReducer.js"
        }
    }
    helpersSpeedometer = component "Estimador de taxa de transferência" "Calcula bytes por segundo sobre um buffer circular fixo de amostras recentes e não informa nada até passar uma janela mínima, para que as primeiras taxas não disparem." "JavaScript" "Pronto,AreaStreaming" {
        properties {
            "status" "Pronto"
            "area" "AreaStreaming"
            "codigo" "lib/helpers/speedometer.js"
        }
    }
    helpersThrottle = component "Limitador de frequência de chamadas" "Limita uma função a uma frequência definida e reserva a última chamada com um timer, devolvendo auxiliares de flush, para que os eventos de progresso saiam em ritmo estável sem perder o valor final." "JavaScript" "Pronto,AreaStreaming" {
        properties {
            "status" "Pronto"
            "area" "AreaStreaming"
            "codigo" "lib/helpers/throttle.js"
        }
    }
    helpersTrackStream = component "Rastreador de progresso de stream" "Envolve um ReadableStream em outro que conta bytes e dispara os callbacks de progresso e de término uma única vez, para que uploads com fetch informem progresso sem manter o corpo em buffer." "JavaScript (Web Streams)" "Pronto,AreaStreaming" {
        properties {
            "status" "Pronto"
            "area" "AreaStreaming"
            "codigo" "lib/helpers/trackStream.js"
        }
    }
}

group "Erros e cancelamento" {
    cancelCancelToken = component "Cancelamento por token" "Implementa a API de cancelamento por token, em que a promise de um token avisa todas as requisições inscritas, para que requisições relacionadas sejam abortadas juntas com uma só chamada." "JavaScript" "Pronto,AreaErrors" {
        properties {
            "status" "Pronto"
            "area" "AreaErrors"
            "codigo" "lib/cancel/CancelToken.js"
        }
    }
    cancelCanceledError = component "Tipo de erro de cancelamento" "Estende o AxiosError com o código ERR_CANCELED e a marca __CANCEL__, para que isCancel distinga cancelamentos do usuário de falhas de rede sem inspecionar mensagens." "JavaScript" "Pronto,AreaErrors" {
        properties {
            "status" "Pronto"
            "area" "AreaErrors"
            "codigo" "lib/cancel/CanceledError.js"
        }
    }
    cancelIsCancel = component "Auxiliar de verificação de cancelamento" "Testa se um valor lançado traz a marca __CANCEL__ em vez de usar instanceof, para que o cancelamento seja detectado mesmo quando os erros cruzam realms ou cópias do módulo no mesmo processo." "JavaScript" "Pronto,AreaErrors" {
        properties {
            "status" "Pronto"
            "area" "AreaErrors"
            "codigo" "lib/cancel/isCancel.js"
        }
    }
    coreAxiosError = component "Classe de erro estruturado" "Leva code, config, request e response em cada falha e oculta chaves secretas da configuração e credenciais de URL, para que os erros registrados em log não vazem credenciais." "JavaScript" "Pronto,AreaErrors" {
        properties {
            "status" "Pronto"
            "area" "AreaErrors"
            "codigo" "lib/core/AxiosError.js"
        }
    }
    helpersHttpStatusCode = component "Constantes de códigos de status HTTP" "Mapeia nomes legíveis, como NotFound, para os códigos numéricos de status, incluindo apelidos descontinuados mantidos por compatibilidade, para que quem chama evite números mágicos nas verificações de validateStatus." "JavaScript" "Pronto,AreaErrors,Dados" {
        properties {
            "status" "Pronto"
            "area" "AreaErrors"
            "codigo" "lib/helpers/HttpStatusCode.js"
            "nota" "Mantém apelidos descontinuados (veja as entradas @deprecated no código) por compatibilidade com versões anteriores."
        }
    }
    helpersComposeSignals = component "Compositor de sinais de cancelamento" "Mescla os sinais de cancelamento do usuário e um timeout em um único AbortSignal, cancelando as inscrições ao terminar, para que a requisição seja abortada pelo gatilho que disparar primeiro, sem vazar listeners." "JavaScript" "Pronto,AreaErrors" {
        properties {
            "status" "Pronto"
            "area" "AreaErrors"
            "codigo" "lib/helpers/composeSignals.js"
        }
    }
    helpersIsAxiosError = component "Verificador de tipo do erro do Axios" "Verifica a flag isAxiosError em objetos simples, sem usar instanceof, para que erros vindos de outras cópias do axios continuem sendo reconhecidos por quem chama." "JavaScript" "Pronto,AreaErrors" {
        properties {
            "status" "Pronto"
            "area" "AreaErrors"
            "codigo" "lib/helpers/isAxiosError.js"
        }
    }
}

group "Plataforma e utilitários" {
    classesFormData = component "Seletor de FormData do ambiente" "Exporta o FormData global quando existe e recorre ao pacote form-data, para que processos Node tenham uma classe multipart mesmo sem FormData global." "JavaScript (só Node)" "Pronto,AreaPlatform" {
        properties {
            "status" "Pronto"
            "area" "AreaPlatform"
            "codigo" "lib/env/classes/FormData.js"
        }
    }
    envData = component "Constante da versão do pacote" "Exporta a string VERSION da biblioteca como uma constante única, que os cabeçalhos padrão e as mensagens de descontinuação leem para informar a versão em execução." "JavaScript" "Pronto,AreaPlatform,Dados" {
        properties {
            "status" "Pronto"
            "area" "AreaPlatform"
            "codigo" "lib/env/data.js"
        }
    }
    helpersBind = component "Auxiliar de função com this fixo" "Envolve uma função para que ela sempre rode com um valor fixo de this, o que permite ao axios expor métodos da instância como funções simples que podem ser repassadas com segurança." "JavaScript" "Pronto,AreaPlatform" {
        properties {
            "status" "Pronto"
            "area" "AreaPlatform"
            "codigo" "lib/helpers/bind.js"
        }
    }
    helpersDeprecatedMethod = component "Emissor de aviso de descontinuação" "Imprime no console um aviso que nomeia um método descontinuado e seu substituto, para que quem chama veja a orientação de migração sem que a chamada lance exceção." "JavaScript" "Pronto,AreaPlatform" {
        properties {
            "status" "Pronto"
            "area" "AreaPlatform"
            "codigo" "lib/helpers/deprecatedMethod.js"
        }
    }
    helpersNull = component "Módulo nulo para o navegador" "Exporta null como módulo substituto, para que o build do navegador troque adaptadores só do Node pelo campo browser do package.json sem trazer módulos internos do Node." "JavaScript (só navegador)" "Pronto,AreaPlatform" {
        properties {
            "status" "Pronto"
            "area" "AreaPlatform"
            "codigo" "lib/helpers/null.js"
        }
    }
    helpersSpread = component "Espalhador de argumentos de array" "Envolve uma função para que ela receba um array como lista de argumentos, o que permite que cadeias de promises passem vários resultados a callbacks como axios.spread." "JavaScript" "Pronto,AreaPlatform" {
        properties {
            "status" "Pronto"
            "area" "AreaPlatform"
            "codigo" "lib/helpers/spread.js"
        }
    }
    classesBlob = component "Exportação do Blob do navegador" "Exporta o Blob global ou null quando ausente, para que os builds de navegador referenciem Blob sem lançar exceção em workers ou ambientes antigos que não o têm." "JavaScript (só navegador)" "Pronto,AreaPlatform" {
        properties {
            "status" "Pronto"
            "area" "AreaPlatform"
            "codigo" "lib/platform/browser/classes/Blob.js"
        }
    }
    classesFormData2 = component "Exportação do FormData do navegador" "Exporta o FormData global ou null quando ausente, para que a plataforma do navegador detecte o suporte a multipart sem uma referência rígida ao global." "JavaScript (só navegador)" "Pronto,AreaPlatform" {
        properties {
            "status" "Pronto"
            "area" "AreaPlatform"
            "codigo" "lib/platform/browser/classes/FormData.js"
        }
    }
    classesURLSearchParams = component "Exportação do URLSearchParams do navegador" "Usa o URLSearchParams nativo quando existe e recorre ao AxiosURLSearchParams caso contrário, para que a codificação de query funcione também em navegadores antigos." "JavaScript (só navegador)" "Pronto,AreaPlatform" {
        properties {
            "status" "Pronto"
            "area" "AreaPlatform"
            "codigo" "lib/platform/browser/classes/URLSearchParams.js"
        }
    }
    browserIndex = component "Descritor da plataforma navegador" "Descreve as capacidades do navegador sinalizando isBrowser, listando os protocolos suportados e ligando o conjunto de classes do navegador, para que o código compartilhado escolha o comportamento do navegador em tempo de execução." "JavaScript (só navegador)" "Pronto,AreaPlatform" {
        properties {
            "status" "Pronto"
            "area" "AreaPlatform"
            "codigo" "lib/platform/browser/index.js"
        }
    }
    commonUtils = component "Detecção de ambiente compartilhada" "Detecta ambientes de navegador padrão, web worker e React Native a partir de window, document e navigator, para que o axios escolha o comportamento certo de XSRF e FormData em cada um." "JavaScript" "Pronto,AreaPlatform" {
        properties {
            "status" "Pronto"
            "area" "AreaPlatform"
            "codigo" "lib/platform/common/utils.js"
        }
    }
    platformIndex = component "Fachada da plataforma" "Reúne o descritor da plataforma Node e a detecção de ambiente compartilhada em um único objeto, para que os módulos importem uma só API de plataforma e o build do navegador a troque pelo empacotador." "JavaScript" "Pronto,AreaPlatform" {
        properties {
            "status" "Pronto"
            "area" "AreaPlatform"
            "codigo" "lib/platform/index.js"
        }
    }
    classesBuffer = component "Adaptador do Buffer do Node" "Envolve a criação de Buffer atrás de uma verificação de disponibilidade, para que os codificadores de formulário e de corpo tratem valores binários no Node e continuem seguros onde Buffer não existe." "JavaScript (só Node)" "Pronto,AreaPlatform" {
        properties {
            "status" "Pronto"
            "area" "AreaPlatform"
            "codigo" "lib/platform/node/classes/Buffer.js"
        }
    }
    classesFormData3 = component "Reexportação do FormData do Node" "Reexporta o pacote form-data no Node, para que a codificação multipart use uma implementação completa, com boundaries e streams de arquivo, onde não há FormData nativo." "JavaScript (só Node)" "Pronto,AreaPlatform" {
        properties {
            "status" "Pronto"
            "area" "AreaPlatform"
            "codigo" "lib/platform/node/classes/FormData.js"
        }
    }
    classesURLSearchParams2 = component "Reexportação do URLSearchParams do Node" "Reexporta a classe URLSearchParams do módulo url do Node, para que a serialização de query no servidor use a mesma classe do parser embutido da plataforma." "JavaScript (só Node)" "Pronto,AreaPlatform" {
        properties {
            "status" "Pronto"
            "area" "AreaPlatform"
            "codigo" "lib/platform/node/classes/URLSearchParams.js"
        }
    }
    nodeIndex = component "Descritor da plataforma Node" "Descreve o ambiente Node com isNode, classes e protocolos, e gera strings de boundary aleatórias com crypto, para que os corpos multipart tenham boundaries imprevisíveis." "JavaScript (só Node)" "Pronto,AreaPlatform" {
        properties {
            "status" "Pronto"
            "area" "AreaPlatform"
            "codigo" "lib/platform/node/index.js"
        }
    }
    libUtils = component "Conjunto de utilitários compartilhados" "Oferece verificações de tipo, iteração segura de objetos e proteções contra poluição de protótipo usadas em toda a biblioteca, para que os auxiliares ignorem chaves herdadas que poderiam alterar o comportamento da requisição." "JavaScript" "Pronto,AreaPlatform" {
        properties {
            "status" "Pronto"
            "area" "AreaPlatform"
            "codigo" "lib/utils.js"
        }
    }
}
