        // Pessoas e sistemas externos. Externo/Nuvem desenham uma borda laranja tracejada.
        devApp = person "Desenvolvedor da aplicação" "Escreve o código da aplicação que instala o axios e o chama para enviar requisições HTTP a partir do Node.js ou do navegador." {
            properties {
                "status" "Pronto"
            }
        }

        nodeRuntime = softwareSystem "Ambiente de execução Node.js" "Fornece os módulos http, https, http2, zlib e stream e os sockets TCP/TLS que o adaptador do Node controla." "Externo" {
            properties {
                "status" "Pronto"
            }
        }

        browserXhr = softwareSystem "XMLHttpRequest do navegador" "A API XMLHttpRequest embutida no navegador, usada pelo adaptador XHR para requisições, eventos de progresso de upload e download e cancelamentos." "Externo,WebBrowser" {
            properties {
                "status" "Pronto"
            }
        }

        fetchApi = softwareSystem "Fetch API" "Os globais fetch, Request e Response de navegadores, Node.js, Deno e Bun, usados pelo adaptador fetch, inclusive com corpos em stream." "Externo" {
            properties {
                "status" "Pronto"
            }
        }

        proxyServer = softwareSystem "Proxy HTTP" "Proxy de encaminhamento opcional (configurado ou lido das variáveis de ambiente de proxy) pelo qual o adaptador do Node roteia as requisições." "Externo,Nuvem" {
            properties {
                "status" "Pronto"
            }
        }

        remoteServer = softwareSystem "Servidor HTTP remoto" "A API web ou o site que recebe a requisição e devolve a resposta que o axios entrega a quem chamou." "Externo,Nuvem" {
            properties {
                "status" "Pronto"
            }
        }
