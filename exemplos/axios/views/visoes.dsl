        !include visoes-geradas.dsl

        // Static views in views/visoes-geradas.dsl (esqueleto.py). Only the flows (dynamic views) live
        // here, written by the modeler. Every step needs a relationship that exists in the model.
        // Steps are numbered automatically by Structurizr, in the order they are written.

        dynamic axiosLib "FlowRequestLifecycle" "The life of one request in Node.js, from the application call to the response handed back." {
            title "Flow: request lifecycle (Node.js)"
            devApp -> libAxios "Calls axios(config) or axios.get(url) on the default instance"
            libAxios -> coreAxios "Forwards the call to the bound request method of the instance"
            coreAxios -> coreMergeConfig "Merges the instance defaults with the call config"
            coreAxios -> coreInterceptorManager "Runs the request interceptors, the last registered first"
            coreAxios -> coreDispatchRequest "Hands the merged config over for dispatch"
            coreDispatchRequest -> coreTransformData "Runs transformRequest to serialize the body and set content-type"
            coreDispatchRequest -> adaptersAdapters "Resolves config.adapter or the default list into one adapter"
            coreDispatchRequest -> adaptersHttp "Invokes the picked adapter, here the Node.js http adapter"
            adaptersHttp -> nodeRuntime "Sends the request over the http, https or http2 socket"
            nodeRuntime -> remoteServer "Carries the request to the server and brings the response back"
            adaptersHttp -> coreSettle "Settles the promise from the response status; out-of-range statuses reject"
            coreDispatchRequest -> coreTransformData "Runs transformResponse to parse the body, for example JSON"
            coreAxios -> coreInterceptorManager "Runs the response interceptors in registration order, then returns to the caller"
            autoLayout lr 150 50
        }

        dynamic axiosLib "FlowAdapterSelection" "How axios picks the transport for the current environment: xhr in browsers, http in Node.js, fetch as the fallback." {
            title "Flow: adapter selection by environment"
            coreDispatchRequest -> defaultsIndex "Reads the default adapter list, ['xhr', 'http', 'fetch']"
            coreDispatchRequest -> adaptersAdapters "Calls getAdapter with config.adapter or the default list"
            adaptersAdapters -> libUtils "Iterates the names and checks whether each entry is a name, a function or a custom adapter"
            adaptersAdapters -> adaptersXhr "Tries xhr first: it exists only where XMLHttpRequest does (browsers)"
            adaptersAdapters -> adaptersHttp "Tries http next: it exists only on Node.js, browser bundles get a null stub"
            adaptersAdapters -> adaptersFetch "Tries fetch last: it exists where the fetch globals do (Deno, Bun, workers)"
            adaptersAdapters -> coreAxiosError "Throws an unknown or unsupported adapter error if nothing is available"
            coreDispatchRequest -> adaptersHttp "Invokes the first available adapter; here Node.js, so http"
            autoLayout lr 150 50
        }

        dynamic axiosLib "FlowNodeHttpRequest" "What the Node.js http adapter does for one request: URL and headers, proxy, upload throttling and progress, and the decompressed response." {
            title "Flow: request through the Node.js http adapter"
            coreDispatchRequest -> adaptersHttp "Invokes the Node.js http adapter with the transformed config"
            adaptersHttp -> coreBuildFullPath "Joins baseURL and url into the request URL"
            adaptersHttp -> helpersBuildURL "Appends the serialized params to the URL"
            adaptersHttp -> coreAxiosHeaders "Builds the request headers"
            adaptersHttp -> helpersShouldBypassProxy "Matches the host against NO_PROXY rules"
            adaptersHttp -> proxyServer "Routes the request through the proxy when one is configured or set in the environment"
            adaptersHttp -> helpersAxiosTransformStream "Throttles the upload stream when maxRate is set"
            adaptersHttp -> helpersProgressEventReducer "Emits upload progress events as the body is written"
            adaptersHttp -> nodeRuntime "Sends the request; redirects are followed by the follow-redirects wrapper up to maxRedirects"
            nodeRuntime -> remoteServer "Carries the request and returns the response stream"
            adaptersHttp -> helpersZlibHeaderTransformStream "Repairs raw deflate streams before they are decompressed with zlib"
            adaptersHttp -> helpersProgressEventReducer "Emits download progress events as the response is read"
            adaptersHttp -> coreSettle "Settles the promise with the response, or rejects on a bad status or the maxContentLength limit"
            autoLayout lr 150 50
        }

        dynamic axiosLib "FlowCancelTimeout" "How a cancellation or a timeout stops a request in the fetch adapter and becomes a CanceledError or an AxiosError." {
            title "Flow: cancellation and timeout"
            coreDispatchRequest -> cancelCancelToken "Asks the token whether cancellation was already requested, before and after the adapter runs"
            coreDispatchRequest -> adaptersFetch "Invokes the fetch adapter with the signal, cancelToken and timeout of the config"
            adaptersFetch -> cancelCancelToken "Converts the cancel token into an abort signal"
            adaptersFetch -> helpersComposeSignals "Merges the user signal, the token signal and the timeout into one signal"
            helpersComposeSignals -> cancelCanceledError "Aborts with a CanceledError when the user signal or the token fires"
            helpersComposeSignals -> coreAxiosError "Aborts with an ECONNABORTED timeout error when the timer runs out"
            adaptersFetch -> fetchApi "Sends fetch with the composed signal; the runtime rejects it with an AbortError when it fires"
            adaptersFetch -> coreAxiosError "Rethrows the composed reason, or wraps any other failure as a network error"
            coreDispatchRequest -> cancelIsCancel "Tells a cancellation from other rejections before the error reaches the caller"
            autoLayout lr 150 50
        }

        dynamic axiosLib "FlowMultipartBody" "How an object or FormData body becomes a multipart request in Node.js: serialization, header policy and the streamed encoding." {
            title "Flow: multipart/FormData body"
            coreDispatchRequest -> coreTransformData "Runs transformRequest on the request data"
            coreTransformData -> defaultsIndex "Falls back to the default transforms, which pick the body serializer by content type"
            defaultsIndex -> helpersToFormData "Serializes a plain object into a FormData for multipart/form-data"
            helpersToFormData -> classesFormData3 "Creates the form-data instance because Node.js has no native FormData here"
            coreDispatchRequest -> adaptersHttp "Invokes the Node.js http adapter with the FormData body"
            adaptersHttp -> coreSetFormDataHeaders "Copies the FormData headers (boundary) into the request per formDataHeaderPolicy"
            adaptersHttp -> helpersFormDataToStream "Wraps spec-compliant FormData into a multipart byte stream"
            helpersFormDataToStream -> platformIndex "Generates the multipart boundary"
            helpersFormDataToStream -> helpersReadBlob "Reads Blob and File parts chunk by chunk"
            adaptersHttp -> helpersProgressEventReducer "Emits upload progress while the stream is sent"
            adaptersHttp -> nodeRuntime "Writes the multipart stream to the socket"
            autoLayout lr 150 50
        }

        dynamic axiosLib "FlowUrlAndHeaders" "How the URL and the request headers are resolved before the fetch adapter sends a request." {
            title "Flow: URL and header resolution"
            adaptersFetch -> helpersResolveConfig "Resolves URL, headers, auth and body policy from the config"
            helpersResolveConfig -> coreMergeConfig "Merges the raw config"
            helpersResolveConfig -> coreBuildFullPath "Resolves the full URL"
            coreBuildFullPath -> helpersIsAbsoluteURL "Skips joining when the url is already absolute"
            coreBuildFullPath -> helpersCombineURLs "Joins baseURL and the relative url, trimming duplicate slashes"
            coreBuildFullPath -> coreAxiosError "Throws on unsafe URLs, redacting any credentials"
            helpersResolveConfig -> helpersBuildURL "Appends the serialized params as the query string"
            helpersBuildURL -> helpersAxiosURLSearchParams "Encodes the params when the native URLSearchParams does not fit"
            helpersResolveConfig -> coreAxiosHeaders "Builds the merged request headers"
            coreAxiosHeaders -> helpersSanitizeHeaderValue "Strips unsafe characters from the header values"
            helpersResolveConfig -> helpersIsURLSameOrigin "Checks the origin before the XSRF header is added"
            helpersResolveConfig -> helpersCookies "Reads the XSRF cookie in standard browser environments"
            autoLayout lr 150 50
        }
