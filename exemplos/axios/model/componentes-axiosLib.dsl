// Gerado por scripts/esqueleto.py a partir de .lodemap/decisoes-modelo.json. Edite o JSON, não este arquivo.

group "Client and configuration" {
    libAxios = component "Default instance factory" "Builds the default axios instance and factory for custom instances, re-exporting cancel, error and helper APIs from one entry point so consumers import a single module." "JavaScript" "Pronto,AreaClient" {
        properties {
            "status" "Done"
            "area" "AreaClient"
            "codigo" "lib/axios.js"
        }
    }
    coreMethodList = component "Supported HTTP methods list" "Lists the frozen set of HTTP method names that get shorthand functions, including PURGE, LINK and QUERY, so adding a method requires one edit in one place." "JavaScript" "Pronto,AreaClient,Dados" {
        properties {
            "status" "Done"
            "area" "AreaClient"
            "codigo" "lib/core/methodList.js"
        }
    }
    defaultsIndex = component "Default configuration object" "Defines the built-in config, including JSON parsing, transform functions, adapters and validateStatus, and picks the right form encoders, so every instance starts from one baseline." "JavaScript" "Pronto,AreaClient" {
        properties {
            "status" "Done"
            "area" "AreaClient"
            "codigo" "lib/defaults/index.js"
        }
    }
    defaultsTransitional = component "Transitional behavior flags" "Holds boolean switches for legacy behaviors such as silent JSON parsing and interceptor ordering, so maintainers can change defaults in one place during a migration." "JavaScript" "Pronto,AreaClient,Dados" {
        properties {
            "status" "Done"
            "area" "AreaClient"
            "codigo" "lib/defaults/transitional.js"
        }
    }
}

group "Request pipeline" {
    coreAxios = component "Request orchestration class" "Holds per-instance defaults and interceptors, merges each call's config, and generates the shorthand methods, so every request runs through one ordered pipeline." "JavaScript" "Pronto,AreaPipeline" {
        properties {
            "status" "Done"
            "area" "AreaPipeline"
            "codigo" "lib/core/Axios.js"
        }
    }
    coreInterceptorManager = component "Interceptor stack manager" "Keeps request and response interceptors in an ordered stack with synchronous and runWhen flags, and skips entries ejected mid-run, so removals during a request do not break the chain." "JavaScript" "Pronto,AreaPipeline" {
        properties {
            "status" "Done"
            "area" "AreaPipeline"
            "codigo" "lib/core/InterceptorManager.js"
        }
    }
    coreDispatchRequest = component "Request dispatch and transforms" "Runs request transforms, flattens the config, checks cancellation, calls the selected adapter, and then transforms the response, so every adapter sees the same prepared input." "JavaScript" "Pronto,AreaPipeline" {
        properties {
            "status" "Done"
            "area" "AreaPipeline"
            "codigo" "lib/core/dispatchRequest.js"
        }
    }
    coreMergeConfig = component "Config merge with precedence" "Merges two config objects into a null-prototype result using per-key rules for headers, auth and URLs, so later config layers override earlier ones without prototype leakage." "JavaScript" "Pronto,AreaPipeline" {
        properties {
            "status" "Done"
            "area" "AreaPipeline"
            "codigo" "lib/core/mergeConfig.js"
        }
    }
    coreSettle = component "Status-based promise settlement" "Resolves or rejects the request promise by applying validateStatus, mapping 4xx to ERR_BAD_REQUEST and other failures to ERR_BAD_RESPONSE, so adapters share one status rule." "JavaScript" "Pronto,AreaPipeline,Gate" {
        properties {
            "status" "Done"
            "area" "AreaPipeline"
            "codigo" "lib/core/settle.js"
        }
    }
    coreTransformData = component "Request and response transforms" "Runs the configured transformRequest or transformResponse functions in order with normalized headers, so each function sees the same header object and status code." "JavaScript" "Pronto,AreaPipeline" {
        properties {
            "status" "Done"
            "area" "AreaPipeline"
            "codigo" "lib/core/transformData.js"
        }
    }
    helpersResolveConfig = component "Request config resolver" "Turns the merged config into final URL, headers and body by applying basic auth, XSRF and FormData headers, so adapters receive a ready-to-send request description." "JavaScript" "Pronto,AreaPipeline" {
        properties {
            "status" "Done"
            "area" "AreaPipeline"
            "codigo" "lib/helpers/resolveConfig.js"
        }
    }
    helpersValidator = component "Option schema validator" "Checks option types against a schema and emits one-time deprecation warnings for removed transitional options, so misconfigured instances fail early with clear messages." "JavaScript" "Pronto,AreaPipeline,Gate" {
        properties {
            "status" "Done"
            "area" "AreaPipeline"
            "codigo" "lib/helpers/validator.js"
        }
    }
}

group "Transport adapters" {
    adaptersAdapters = component "Adapter selection registry" "Selects the first usable transport from a list of names or functions and rejects unknown ones, so Axios fails early with a clear reason when no adapter fits the runtime." "JavaScript" "Pronto,AreaAdapters" {
        properties {
            "status" "Done"
            "area" "AreaAdapters"
            "codigo" "lib/adapters/adapters.js"
        }
    }
    adaptersFetch = component "Fetch transport adapter" "Sends requests through the Fetch API with streamed bodies and progress tracking, so runtimes without XMLHttpRequest, such as workers and edge hosts, can still use Axios." "JavaScript (Fetch API)" "Pronto,AreaAdapters" {
        properties {
            "status" "Done"
            "area" "AreaAdapters"
            "codigo" "lib/adapters/fetch.js"
        }
    }
    adaptersHttp = component "Node HTTP transport" "Performs requests with Node's http and https modules, adding proxy tunneling, redirect handling, rate limits and decompression, which the browser-bound adapters cannot provide." "JavaScript (Node only)" "Pronto,AreaAdapters" {
        properties {
            "status" "Done"
            "area" "AreaAdapters"
            "codigo" "lib/adapters/http.js"
        }
    }
    adaptersXhr = component "Browser XHR transport" "Drives XMLHttpRequest in browsers and maps timeouts, aborts and status-0 responses to Axios errors, because XHR is the only transport with native upload progress there." "JavaScript (browser only)" "Pronto,AreaAdapters" {
        properties {
            "status" "Done"
            "area" "AreaAdapters"
            "codigo" "lib/adapters/xhr.js"
        }
    }
    helpersHttp2Sessions = component "HTTP/2 session pool" "Caches HTTP/2 sessions per authority and option set, reusing live connections and expiring idle ones after a timeout, so repeated requests avoid new TLS handshakes." "JavaScript (Node only)" "Pronto,AreaAdapters" {
        properties {
            "status" "Done"
            "area" "AreaAdapters"
            "codigo" "lib/helpers/Http2Sessions.js"
        }
    }
    helpersCallbackify = component "Async-to-callback wrapper" "Converts an async function into a callback-style one with an optional result reducer, so the HTTP adapter can wrap a custom async DNS lookup for Node's callback-based sockets." "JavaScript" "Pronto,AreaAdapters" {
        properties {
            "status" "Done"
            "area" "AreaAdapters"
            "codigo" "lib/helpers/callbackify.js"
        }
    }
    helpersShouldBypassProxy = component "Proxy bypass matcher" "Decides whether a host skips the proxy by canonicalizing IPv4 shorthand, octal and hex forms and unmapping IPv4-mapped IPv6, so bypass rules cannot be evaded by alternate spellings." "JavaScript" "Pronto,AreaAdapters" {
        properties {
            "status" "Done"
            "area" "AreaAdapters"
            "codigo" "lib/helpers/shouldBypassProxy.js"
        }
    }
}

group "URLs and headers" {
    coreAxiosHeaders = component "Case-insensitive header map" "Stores headers under normalized names with set, get and merge helpers, and rejects invalid names or values, because raw object headers silently duplicate keys in different casings." "JavaScript" "Pronto,AreaUrlHeaders" {
        properties {
            "status" "Done"
            "area" "AreaUrlHeaders"
            "codigo" "lib/core/AxiosHeaders.js"
        }
    }
    coreAssertParamsAcyclic = component "Params cycle guard" "Walks the merged params iteratively and throws ERR_BAD_OPTION_VALUE on true cycles, tracking the active path so shared but acyclic objects still pass, so circular params fail fast with a clear error instead of reaching the query serializer." "JavaScript" "Pronto,AreaUrlHeaders" {
        properties {
            "status" "Done"
            "area" "AreaUrlHeaders"
            "codigo" "lib/core/assertParamsAcyclic.js"
        }
    }
    coreBuildFullPath = component "Base URL joiner" "Joins baseURL with relative paths and refuses malformed or disallowed absolute URLs, redacting credentials and query secrets from the message, so errors stay safe to log." "JavaScript" "Pronto,AreaUrlHeaders,Gate" {
        properties {
            "status" "Done"
            "area" "AreaUrlHeaders"
            "codigo" "lib/core/buildFullPath.js"
        }
    }
    helpersBuildURL = component "Query string builder" "Appends serialized params to a URL while keeping reserved characters like colon and comma readable, and honors custom serializers, so generated query strings stay compact and predictable." "JavaScript" "Pronto,AreaUrlHeaders" {
        properties {
            "status" "Done"
            "area" "AreaUrlHeaders"
            "codigo" "lib/helpers/buildURL.js"
        }
    }
    helpersCombineURLs = component "URL segment joiner" "Joins a base URL and a relative path with exactly one slash, trimming trailing slashes from the base, so baseURL and url values never produce double or missing separators." "JavaScript" "Pronto,AreaUrlHeaders" {
        properties {
            "status" "Done"
            "area" "AreaUrlHeaders"
            "codigo" "lib/helpers/combineURLs.js"
        }
    }
    helpersCookies = component "Cookie read and write" "Reads and writes XSRF cookies via document.cookie or the Cookie Store API, splitting on semicolons instead of building a regex from the name to avoid ReDoS and wrong-cookie matches." "JavaScript" "Pronto,AreaUrlHeaders" {
        properties {
            "status" "Done"
            "area" "AreaUrlHeaders"
            "codigo" "lib/helpers/cookies.js"
        }
    }
    helpersIsAbsoluteURL = component "Absolute URL detector" "Detects an absolute URL by RFC 3986 scheme syntax or a leading double slash, so protocol-relative URLs skip baseURL joining." "JavaScript" "Pronto,AreaUrlHeaders" {
        properties {
            "status" "Done"
            "area" "AreaUrlHeaders"
            "codigo" "lib/helpers/isAbsoluteURL.js"
        }
    }
    helpersIsURLSameOrigin = component "Same-origin check" "Compares protocol, host and port with the page origin, so the XSRF header is sent only to same-origin URLs in standard browsers." "JavaScript" "Pronto,AreaUrlHeaders,Gate" {
        properties {
            "status" "Done"
            "area" "AreaUrlHeaders"
            "codigo" "lib/helpers/isURLSameOrigin.js"
        }
    }
    helpersNormalizeURLForProtocolCheck = component "URL protocol normalizer" "Strips leading control characters and embedded tabs or newlines the way WHATWG parsing does, so protocol checks see the same scheme the browser will use." "JavaScript" "Pronto,AreaUrlHeaders" {
        properties {
            "status" "Done"
            "area" "AreaUrlHeaders"
            "codigo" "lib/helpers/normalizeURLForProtocolCheck.js"
        }
    }
    helpersParseHeaders = component "Raw header parser" "Parses raw header text into an object and drops duplicates for headers Node itself ignores, so merged values match what Node's HTTP layer exposes." "JavaScript" "Pronto,AreaUrlHeaders" {
        properties {
            "status" "Done"
            "area" "AreaUrlHeaders"
            "codigo" "lib/helpers/parseHeaders.js"
        }
    }
    helpersParseProtocol = component "URL scheme extractor" "Extracts the scheme from a URL string with one regex and returns an empty string when none is found, so adapters can pick a transport by protocol." "JavaScript" "Pronto,AreaUrlHeaders" {
        properties {
            "status" "Done"
            "area" "AreaUrlHeaders"
            "codigo" "lib/helpers/parseProtocol.js"
        }
    }
    helpersSanitizeHeaderValue = component "Header value sanitizer" "Trims whitespace and strips control bytes from header values, and converts them to byte strings for fetch, so invalid characters cannot break the request or inject headers." "JavaScript" "Pronto,AreaUrlHeaders,Gate" {
        properties {
            "status" "Done"
            "area" "AreaUrlHeaders"
            "codigo" "lib/helpers/sanitizeHeaderValue.js"
        }
    }
}

group "Payload encoding" {
    coreCreateMultipartBody = component "Multipart body builder" "Builds a multipart Blob from FormData for the fetch adapter, generating a boundary when none is given and translating serialization failures into AxiosError codes (ERR_NOT_SUPPORT, ERR_BAD_OPTION_VALUE, ERR_BAD_REQUEST), so uploads can be size-limited or streamed." "JavaScript" "Pronto,AreaPayload" {
        properties {
            "status" "Done"
            "area" "AreaPayload"
            "codigo" "lib/core/createMultipartBody.js"
        }
    }
    coreSetFormDataHeaders = component "FormData header policy" "Copies FormData-generated headers into the request, either all of them or only content-type and content-length per formDataHeaderPolicy, so multipart boundaries apply predictably." "JavaScript" "Pronto,AreaPayload" {
        properties {
            "status" "Done"
            "area" "AreaPayload"
            "codigo" "lib/core/setFormDataHeaders.js"
        }
    }
    helpersAxiosURLSearchParams = component "URLSearchParams fallback class" "Fallback URLSearchParams class that percent-encodes pairs with plus for spaces, used where the native class is missing, so query and form encoding stay consistent." "JavaScript" "Pronto,AreaPayload" {
        properties {
            "status" "Done"
            "area" "AreaPayload"
            "codigo" "lib/helpers/AxiosURLSearchParams.js"
        }
    }
    helpersEstimateDataURLDecodedBytes = component "Data URL size estimator" "Estimates decoded byte length of data: URLs without allocating buffers, so maxContentLength can reject oversized payloads before any memory is committed." "JavaScript" "Pronto,AreaPayload" {
        properties {
            "status" "Done"
            "area" "AreaPayload"
            "codigo" "lib/helpers/estimateDataURLDecodedBytes.js"
        }
    }
    helpersFormDataToBlob = component "FormData to Blob" "Converts FormData into a native multipart Blob, counting UTF-8 field bytes without encoding copies and enforcing the body-size limit before building it, and composes existing File data by reference, so large uploads avoid extra buffers." "JavaScript" "Pronto,AreaPayload" {
        properties {
            "status" "Done"
            "area" "AreaPayload"
            "codigo" "lib/helpers/formDataToBlob.js"
        }
    }
    helpersFormDataToJSON = component "FormData to JSON converter" "Turns FormData entries into nested objects by parsing bracket and dot paths, with a depth cap and fail-fast parsing, so form submissions convert to JSON safely." "JavaScript" "Pronto,AreaPayload" {
        properties {
            "status" "Done"
            "area" "AreaPayload"
            "codigo" "lib/helpers/formDataToJSON.js"
        }
    }
    helpersFromDataURI = component "Data URI decoder" "Decodes RFC 2397 data: URIs into a Buffer or Blob, applying the spec default mediatype, so inline payloads work in Node the same as in browsers." "JavaScript" "Pronto,AreaPayload" {
        properties {
            "status" "Done"
            "area" "AreaPayload"
            "codigo" "lib/helpers/fromDataURI.js"
        }
    }
    helpersReadBlob = component "Blob chunk reader" "Reads a Blob as an async iterator using stream, arrayBuffer or iterator, whichever is available, so multipart encoding works across runtimes with different Blob APIs." "JavaScript" "Pronto,AreaPayload" {
        properties {
            "status" "Done"
            "area" "AreaPayload"
            "codigo" "lib/helpers/readBlob.js"
        }
    }
    helpersToFormData = component "Object to FormData encoder" "Serializes nested objects into FormData or URLSearchParams with bracket keys and a depth limit of 100, and enforces that limit so deep payloads fail with a clear error." "JavaScript" "Pronto,AreaPayload" {
        properties {
            "status" "Done"
            "area" "AreaPayload"
            "codigo" "lib/helpers/toFormData.js"
        }
    }
    helpersToURLEncodedForm = component "URL-encoded body encoder" "Encodes objects as application/x-www-form-urlencoded, writing Node Buffers as base64, so form posts keep binary values intact without a separate serializer." "JavaScript" "Pronto,AreaPayload" {
        properties {
            "status" "Done"
            "area" "AreaPayload"
            "codigo" "lib/helpers/toURLEncodedForm.js"
        }
    }
}

group "Streams and progress" {
    helpersAxiosTransformStream = component "Throttled transform stream" "Caps throughput and emits progress from a Node Transform stream using a sliding time window, so uploads and downloads can be rate-limited with the maxRate option." "JavaScript (Node only)" "Pronto,AreaStreaming" {
        properties {
            "status" "Done"
            "area" "AreaStreaming"
            "codigo" "lib/helpers/AxiosTransformStream.js"
        }
    }
    helpersZlibHeaderTransformStream = component "Zlib header repair stream" "Prepends a default zlib header when a deflate body lacks one, because some servers send raw deflate that Node's inflate rejects, so decompression still succeeds." "JavaScript (Node only)" "Pronto,AreaStreaming" {
        properties {
            "status" "Done"
            "area" "AreaStreaming"
            "codigo" "lib/helpers/ZlibHeaderTransformStream.js"
        }
    }
    helpersFormDataToStream = component "Multipart form stream" "Streams FormData parts as multipart bytes with a generated boundary and computed length, so large uploads reach Node's HTTP stack without buffering the whole body." "JavaScript (Node only)" "Pronto,AreaStreaming" {
        properties {
            "status" "Done"
            "area" "AreaStreaming"
            "codigo" "lib/helpers/formDataToStream.js"
        }
    }
    helpersProgressEventReducer = component "Throttled progress reducer" "Clamps loaded counts, computes rate and ETA with a speedometer, and throttles callbacks, so progress listeners receive steady, accurate events instead of raw bursts." "JavaScript" "Pronto,AreaStreaming" {
        properties {
            "status" "Done"
            "area" "AreaStreaming"
            "codigo" "lib/helpers/progressEventReducer.js"
        }
    }
    helpersSpeedometer = component "Transfer rate estimator" "Computes bytes per second over a fixed ring buffer of recent samples and reports nothing until a minimum window passes, so early rate figures do not spike." "JavaScript" "Pronto,AreaStreaming" {
        properties {
            "status" "Done"
            "area" "AreaStreaming"
            "codigo" "lib/helpers/speedometer.js"
        }
    }
    helpersThrottle = component "Call rate limiter" "Limits a function to a set frequency and trails the last call with a timer, returning flush helpers, so progress events are emitted at a steady rate without dropping the final value." "JavaScript" "Pronto,AreaStreaming" {
        properties {
            "status" "Done"
            "area" "AreaStreaming"
            "codigo" "lib/helpers/throttle.js"
        }
    }
    helpersTrackStream = component "Stream progress tracker" "Wraps a ReadableStream in another that counts bytes and fires progress and finish callbacks once, so fetch uploads report progress without buffering the body." "JavaScript (Web Streams)" "Pronto,AreaStreaming" {
        properties {
            "status" "Done"
            "area" "AreaStreaming"
            "codigo" "lib/helpers/trackStream.js"
        }
    }
}

group "Errors and cancellation" {
    cancelCancelToken = component "Token-based cancellation" "Implements the token-based cancellation API, where one token's promise notifies every subscribed request, so related requests can be aborted together with a single call." "JavaScript" "Pronto,AreaErrors" {
        properties {
            "status" "Done"
            "area" "AreaErrors"
            "codigo" "lib/cancel/CancelToken.js"
        }
    }
    cancelCanceledError = component "Cancellation error type" "Extends AxiosError with the ERR_CANCELED code and a __CANCEL__ flag, so isCancel can tell user cancellations apart from network failures without inspecting messages." "JavaScript" "Pronto,AreaErrors" {
        properties {
            "status" "Done"
            "area" "AreaErrors"
            "codigo" "lib/cancel/CanceledError.js"
        }
    }
    cancelIsCancel = component "Cancellation check helper" "Tests a thrown value for the __CANCEL__ marker instead of instanceof, so cancellation is detected even when errors cross realms or module copies in the same process." "JavaScript" "Pronto,AreaErrors" {
        properties {
            "status" "Done"
            "area" "AreaErrors"
            "codigo" "lib/cancel/isCancel.js"
        }
    }
    coreAxiosError = component "Structured error class" "Carries code, config, request and response on each failure, and redacts secret config keys and URL credentials, so logged errors do not leak credentials." "JavaScript" "Pronto,AreaErrors" {
        properties {
            "status" "Done"
            "area" "AreaErrors"
            "codigo" "lib/core/AxiosError.js"
        }
    }
    helpersHttpStatusCode = component "HTTP status code constants" "Maps readable names such as NotFound to numeric status codes, including deprecated aliases kept for compatibility, so callers avoid magic numbers in validateStatus checks." "JavaScript" "Pronto,AreaErrors,Dados" {
        properties {
            "status" "Done"
            "area" "AreaErrors"
            "codigo" "lib/helpers/HttpStatusCode.js"
            "nota" "Keeps deprecated aliases (see @deprecated entries in the source) for backward compatibility."
        }
    }
    helpersComposeSignals = component "Abort signal composer" "Merges user cancel signals and a timeout into one AbortSignal, unsubscribing on completion, so a request aborts on whichever trigger fires first without leaking listeners." "JavaScript" "Pronto,AreaErrors" {
        properties {
            "status" "Done"
            "area" "AreaErrors"
            "codigo" "lib/helpers/composeSignals.js"
        }
    }
    helpersIsAxiosError = component "Axios error type guard" "Checks for the isAxiosError flag on plain objects, not instanceof, so errors from other copies of axios are still recognized by callers." "JavaScript" "Pronto,AreaErrors" {
        properties {
            "status" "Done"
            "area" "AreaErrors"
            "codigo" "lib/helpers/isAxiosError.js"
        }
    }
}

group "Platform and utilities" {
    classesFormData = component "Environment FormData selector" "Exports the global FormData when present and falls back to the form-data package, so Node processes get a multipart class even without a global FormData." "JavaScript (Node only)" "Pronto,AreaPlatform" {
        properties {
            "status" "Done"
            "area" "AreaPlatform"
            "codigo" "lib/env/classes/FormData.js"
        }
    }
    envData = component "Package version constant" "Exports the library VERSION string as a single constant, which default headers and deprecation messages read to report the running release." "JavaScript" "Pronto,AreaPlatform,Dados" {
        properties {
            "status" "Done"
            "area" "AreaPlatform"
            "codigo" "lib/env/data.js"
        }
    }
    helpersBind = component "Bound function helper" "Wraps a function so it always runs with a fixed this value, which lets axios expose instance methods as plain functions that can be passed around safely." "JavaScript" "Pronto,AreaPlatform" {
        properties {
            "status" "Done"
            "area" "AreaPlatform"
            "codigo" "lib/helpers/bind.js"
        }
    }
    helpersDeprecatedMethod = component "Deprecation warning emitter" "Prints a console warning that names a deprecated method and its replacement, so callers see migration guidance without the call throwing." "JavaScript" "Pronto,AreaPlatform" {
        properties {
            "status" "Done"
            "area" "AreaPlatform"
            "codigo" "lib/helpers/deprecatedMethod.js"
        }
    }
    helpersNull = component "Null browser stub" "Exports null as a stand-in module, so the browser build can swap out Node-only adapters through the package browser field without pulling in Node built-ins." "JavaScript (browser only)" "Pronto,AreaPlatform" {
        properties {
            "status" "Done"
            "area" "AreaPlatform"
            "codigo" "lib/helpers/null.js"
        }
    }
    helpersSpread = component "Array argument spreader" "Wraps a function so it receives an array as its argument list, which lets promise chains pass multiple results to callbacks such as axios.spread." "JavaScript" "Pronto,AreaPlatform" {
        properties {
            "status" "Done"
            "area" "AreaPlatform"
            "codigo" "lib/helpers/spread.js"
        }
    }
    classesBlob = component "Browser Blob export" "Exports the global Blob or null when absent, so browser builds reference Blob without throwing in workers or older environments that lack it." "JavaScript (browser only)" "Pronto,AreaPlatform" {
        properties {
            "status" "Done"
            "area" "AreaPlatform"
            "codigo" "lib/platform/browser/classes/Blob.js"
        }
    }
    classesFormData2 = component "Browser FormData export" "Exports the global FormData or null when absent, so the browser platform can detect multipart support without a hard reference to the global." "JavaScript (browser only)" "Pronto,AreaPlatform" {
        properties {
            "status" "Done"
            "area" "AreaPlatform"
            "codigo" "lib/platform/browser/classes/FormData.js"
        }
    }
    classesURLSearchParams = component "Browser URLSearchParams export" "Uses the native URLSearchParams when present and falls back to AxiosURLSearchParams otherwise, so query encoding works in older browsers too." "JavaScript (browser only)" "Pronto,AreaPlatform" {
        properties {
            "status" "Done"
            "area" "AreaPlatform"
            "codigo" "lib/platform/browser/classes/URLSearchParams.js"
        }
    }
    browserIndex = component "Browser platform descriptor" "Describes browser capabilities by flagging isBrowser, listing supported protocols and wiring the browser class set, so shared code picks browser behavior at runtime." "JavaScript (browser only)" "Pronto,AreaPlatform" {
        properties {
            "status" "Done"
            "area" "AreaPlatform"
            "codigo" "lib/platform/browser/index.js"
        }
    }
    commonUtils = component "Shared environment detection" "Detects standard browser, web worker and React Native environments from window, document and navigator, so axios picks the right XSRF and FormData behavior in each." "JavaScript" "Pronto,AreaPlatform" {
        properties {
            "status" "Done"
            "area" "AreaPlatform"
            "codigo" "lib/platform/common/utils.js"
        }
    }
    platformIndex = component "Platform facade" "Merges the Node platform descriptor with shared environment detection into one object, so modules import a single platform API and the browser build swaps it through the bundler." "JavaScript" "Pronto,AreaPlatform" {
        properties {
            "status" "Done"
            "area" "AreaPlatform"
            "codigo" "lib/platform/index.js"
        }
    }
    classesBuffer = component "Node Buffer adapter" "Wraps Buffer creation behind an availability check, so form and body encoders can handle binary values on Node while staying safe where Buffer is absent." "JavaScript (Node only)" "Pronto,AreaPlatform" {
        properties {
            "status" "Done"
            "area" "AreaPlatform"
            "codigo" "lib/platform/node/classes/Buffer.js"
        }
    }
    classesFormData3 = component "Node FormData re-export" "Re-exports the form-data package on Node, so multipart encoding uses a full implementation with boundaries and file streams where no native FormData exists." "JavaScript (Node only)" "Pronto,AreaPlatform" {
        properties {
            "status" "Done"
            "area" "AreaPlatform"
            "codigo" "lib/platform/node/classes/FormData.js"
        }
    }
    classesURLSearchParams2 = component "Node URLSearchParams re-export" "Re-exports the URLSearchParams class from Node's url module, so server-side query serialization uses the same class as the platform's built-in parser." "JavaScript (Node only)" "Pronto,AreaPlatform" {
        properties {
            "status" "Done"
            "area" "AreaPlatform"
            "codigo" "lib/platform/node/classes/URLSearchParams.js"
        }
    }
    nodeIndex = component "Node platform descriptor" "Describes the Node runtime with isNode, classes and protocols, and generates random boundary strings with crypto, so multipart bodies get unpredictable boundaries." "JavaScript (Node only)" "Pronto,AreaPlatform" {
        properties {
            "status" "Done"
            "area" "AreaPlatform"
            "codigo" "lib/platform/node/index.js"
        }
    }
    libUtils = component "Shared utility toolkit" "Provides type checks, safe object iteration and prototype-pollution guards used across the library, so helpers ignore inherited keys that could alter request behavior." "JavaScript" "Pronto,AreaPlatform" {
        properties {
            "status" "Done"
            "area" "AreaPlatform"
            "codigo" "lib/utils.js"
        }
    }
}
