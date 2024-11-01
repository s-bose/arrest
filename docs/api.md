# API Documentation

## `Service`
::: arrest.service.Service
    options:
        show_source: false
        members:
            - __init__
            - add_resource
            - request

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
## Httpx Client Arguments
::: arrest._config.HttpxClientInputs

**Parameters:**

* **auth** - *(optional)* An authentication class to use when sending
requests.
* **params** - *(optional)* Query parameters to include in request URLs, as
a string, dictionary, or sequence of two-tuples.
* **headers** - *(optional)* Dictionary of HTTP headers to include when
sending requests.
* **cookies** - *(optional)* Dictionary of Cookie items to include when
sending requests.
* **verify** - *(optional)* SSL certificates (a.k.a CA bundle) used to
verify the identity of requested hosts. Either `True` (default CA bundle),
a path to an SSL certificate file, an `ssl.SSLContext`, or `False`
(which will disable verification).
* **cert** - *(optional)* An SSL certificate used by the requested host
to authenticate the client. Either a path to an SSL certificate file, or
two-tuple of (certificate file, key file), or a three-tuple of (certificate
file, key file, password).
* **http2** - *(optional)* A boolean indicating if HTTP/2 support should be
enabled. Defaults to `False`.
* **proxies** - *(optional)* A dictionary mapping HTTP protocols to proxy
URLs (*deprecated*).
* **mounts** - *(optional)* A dictionary mapping HTTP protocols to proxy
URLs
* **timeout** - *(optional)* The timeout configuration to use when sending
requests.
* **follow_redirects** - *(optional)* A boolean indicating whether to follow redirects. [See more](https://www.python-httpx.org/quickstart/#redirection-and-history)
* **limits** - *(optional)* The limits configuration to use.
* **max_redirects** - *(optional)* The maximum number of redirect responses
that should be followed.
* **event_hooks** - *(optional)* - A dictionary to set event hook callbacks for request and response events. [See more](https://www.python-httpx.org/advanced/#event-hooks)
* **transport** - *(optional)* A transport class to use for sending requests
over the network.
* **trust_env** - *(optional)* Enables or disables usage of environment
variables for configuration.
* **default_encoding** - *(optional)* The default encoding to use for decoding
response text, if no charset information is included in a response Content-Type
header. Set to a callable for automatic character set detection. Default: "utf-8".


**Parameters not included**

* **base_url** - Already used internally in `Resource`, therefore no need to set it from kwargs
* **app** - Not required currently as Arrest is primarily built to make external http requests

## `ResourceHandler`

::: arrest.handler.ResourceHandler

## Exceptions

### ArrestError
::: arrest.exceptions.ArrestError
base class for all Exception. Used in situations that are not one of the following

### ArrestHTTPException
::: arrest.exceptions.ArrestHTTPException
used for exceptions during HTTP calls

* `.status_code` - **str** status code of the exception, 500 for internal server error
* `.data` - **str** json response for the exception

### NotFoundException
::: arrest.exceptions.NotFoundException
base class for all NotFound-type exceptions

### HandlerNotFound
::: arrest.exceptions.HandlerNotFound
raised when no matching handler is found for the requested path

* `.message` - **str**

### ResourceNotFound
::: arrest.exceptions.ResourceNotFound
raised when no matching resource is found for the service

* `.message` - **str**


### ConversionError
::: arrest.exceptions.ConversionError
raised when Arrest cannot convert path-parameter type using any of the existing converters


## OpenAPIGenerator
::: arrest.openapi.OpenAPIGenerator
