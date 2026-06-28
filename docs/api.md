# API Documentation

## `Service`
::: arrest.service.Service
    options:
        show_source: false
        members:
            - __init__
            - add_resource

## `Resource`
::: arrest.resource.Resource
    options:
        show_source: false
        members:
            - __init__
            - request
            - get
            - post
            - put
            - patch
            - delete
            - head
            - options
            - handler
## `ArrestConfig`
::: arrest._config.ArrestConfig
    options:
        show_source: false
        members:
            - httpx_args
            - merge

All httpx client arguments and Arrest-specific settings live here. Pass an instance
to `Service(...)`, `Resource(...)`, or merge per-call via `request(...)`.

**Key fields:**

| Field | Type | Description |
|---|---|---|
| `headers` | `dict[str, str]` | Default request headers (merged additively) |
| `cookies` | `dict[str, Any]` | Default request cookies (merged additively) |
| `params` | `dict[str, Any]` | Default query params (merged additively) |
| `timeout` | `float \| None` | Request timeout in seconds |
| `auth` | `Any \| None` | Authentication credentials |
| `follow_redirects` | `bool \| None` | Whether to follow redirects |
| `raise_for_status` | `bool \| None` | If `True`, non-2xx raises `ArrestHTTPException` |
| `client` | `AsyncClient \| None` | A shared `httpx.AsyncClient` instance |
| `max_retries` | `int \| None` | Arrest-level retry count (tenacity) |
| `verify` | `SSLContext \| bool \| str \| None` | SSL verification |
| `cert` | `CertTypes \| None` | SSL client certificate |
| `http2` | `bool \| None` | Enable HTTP/2 |
| `proxy` | `ProxyTypes \| None` | Proxy configuration |
| `mounts` | `Mapping[str, AsyncBaseTransport] \| None` | Transport mounts |
| `limits` | `Limits \| None` | Connection pool limits |
| `transport` | `AsyncBaseTransport \| None` | Custom transport |
| `trust_env` | `bool \| None` | Trust environment variables |
| `event_hooks` | `Mapping[str, list[Callable]] \| None` | Request/response event hooks |
| `default_encoding` | `str \| Callable \| None` | Default response encoding |

## `ResourceHandler`

::: arrest.handler.ResourceHandler

## Exceptions

### ArrestError
::: arrest.exceptions.ArrestError
base class for all Exception. Used in situations that are not one of the following

### RequestError
::: arrest.exceptions.RequestError
raised for transport-level failures (timeout, DNS errors, connection refused).

* `.message` — **str** description of the error

### ArrestHTTPException
::: arrest.exceptions.ArrestHTTPException
raised for non-2xx HTTP responses when `raise_for_status=True` is set.

* `.status_code` — **int** HTTP status code
* `.data` — **Any** response body (JSON dict, XML model, string, etc.)

### NotFoundException
::: arrest.exceptions.NotFoundException
base class for all NotFound-type exceptions

### HandlerNotFound
::: arrest.exceptions.HandlerNotFound
raised when no matching handler is found for the requested path

* `.message` - **str**


* `.message` - **str**


### ConversionError
::: arrest.exceptions.ConversionError
raised when Arrest cannot convert path-parameter type using any of the existing converters


## OpenAPIGenerator
::: arrest.openapi.OpenAPIGenerator
