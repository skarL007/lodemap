        // People and external systems. Externo/Nuvem draw a dashed orange border.
        devApp = person "Application developer" "Writes the application code that installs axios and calls it to send HTTP requests from Node.js or the browser." {
            properties {
                "status" "Done"
            }
        }

        nodeRuntime = softwareSystem "Node.js runtime" "Provides the http, https, http2, zlib and stream modules and the TCP/TLS sockets that the Node adapter drives." "Externo" {
            properties {
                "status" "Done"
            }
        }

        browserXhr = softwareSystem "Browser XMLHttpRequest" "The browser's built-in XMLHttpRequest API, used by the XHR adapter for requests, upload/download progress events and aborts." "Externo,WebBrowser" {
            properties {
                "status" "Done"
            }
        }

        fetchApi = softwareSystem "Fetch API" "The fetch, Request and Response globals of browsers, Node.js, Deno and Bun, used by the fetch adapter, including streamed bodies." "Externo" {
            properties {
                "status" "Done"
            }
        }

        proxyServer = softwareSystem "HTTP proxy" "Optional forward proxy (configured or taken from the proxy environment variables) through which the Node adapter routes requests." "Externo,Nuvem" {
            properties {
                "status" "Done"
            }
        }

        remoteServer = softwareSystem "Remote HTTP server" "The web API or site that receives the request and returns the response axios hands back to the caller." "Externo,Nuvem" {
            properties {
                "status" "Done"
            }
        }
