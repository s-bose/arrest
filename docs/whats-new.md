### Added support for decorating custom handlers for your resource.

Earlier in v0.1.9 the decorator could only be used with a resource under its parent service's scope:

```python
@myservice.user.handler("/path")
async def path_handler(self, url, *args, **kwargs):
    ...
```

This was not a clear separation of concern. Ideally in Arrest, we want you to be able to define everything relating to a resource within the resource, and everything relating to a service within the service, and simply interface the resources with your service, or multiple services.
In v0.1.10, you can use the handler with your resource, without having to connect it to a service first and use the service's scope:

```python
# resource.py
from arrest import Resource

user = Resource(
    route="/user",
    handlers=[...]
)

@user.handler("/upload-pic")
async def upload_user_profile_pic(self, url, *arg, *kwarg):
    ...

...

# service.py
from .resource import user

myservice = Service(
    name="myservice",
    url="http://example.com",
    resources=[user]
)

...

# somewhere_else.py
from .service import myservice

await myservice.user.upload_user_profile_pic(...)
```

!!! Note
    Connecting your resource to a service is still mandatory if you want to use the complete url. If you just call the method from your resource instance directly, since its still not bound to a service (thus a `base_url`), it would try to make an api call to `/user/upload-pic`, instead of `http://example.com/user/upload-pic`


### Standardized the names of resource and services from parsing the OpenAPI Specification.

Certain names for resources and services had whitespaces and special characters, which resulted in the generated code having illegal variable names (such as `OpenAPI service: 2.1 = Service(...)`)

v0.1.10 standardizes all variable names of the generated service and resource to lower and snake_cased.

### Add support for root-level resources.

You can now define root-level resources (i.e., having base routes of either `""` or `"/"`)
There can be only one root-level resource, for obvious reasons.
You can set them up as normal `Resource` instances with `route=""` or `route="/`" and a corresponding handler `(<Method>, "")` (e.g. `www.example.com`) or `(<Method>, "/")` (e.g. `www.example.com/`)

In order to make the call to the root-resource, you simply invoke the http methods on the service directly, without specifying a resource.

```python
await my_service.get("") # or my_service.get("/")
```

!!! Note
    This is only applicable if you have a path with no suffix at the root level. i.e. `www.example.com/`.
    If you want to access `www.example.com/path`, then the following won't work.

    ```python
    Resource(route="/", handlers=[("GET", "/path")])
    ...

    await service.get("/path") # throws ResourceNotFound
    ```

    Because `/path` constitutes a resource on its own, not a subpath for a root-resource `/`, hence the following would need to be written

    ```python
    Resource(route="/path", handlers=[("GET", "")])
    ...

    await service.path.get("") # works!
    ```

    General rule-of-thumb is, a RESTful resource always has a path prefix, and arrest resources should preferrably be designed around that
    notion. If you have an endpoint with only the root-level being the accessible API, you might want to create a root-resource with
    a single handler.


### Standardized retry mechanism with more flexibility

The previous built-in retry mechanism was too restrictive and lacked configurability. In the new version, there will not be any retry by default.
This is to reduce as much side-effect as possible from the HTTP calls in favour of developer expectations. If you want to enable retries there are a few different ways.

1. Use the standard retry mechanism from httpx transport

    ```python

    from httpx import AsyncHTTPTransport
    from arrest import Resource, Service

    transport = AsyncHTTPTransport(retries=3)

    my_service = Service(
        name="myservice",
        url="http://example.com",
        resources=[user],
        transport=transport
    )
    ```
    or, if you are running your own httpx client instance, you can also configure it there.

    ```python
    my_service = Service(
        name="myservice",
        url="http://example.com",
        resources=[user],
        client=httpx.AsyncClient(transport=transport)
    )
    ```

    This will retry the request in case of `httpx.ConnectError` or `httpx.ConnectTimeout`. [Read more](https://www.python-httpx.org/advanced/transports/)

2. Use the retry mechanism from arrest

    Arrest provides an additional keyword-argument `retry` either at service-level, or at individual resource-level.
    It is defaulted to `None`, should you opt for no retries (the default behaviour). However, you can set it to any
    valid integer resembling the number of times it should retry.

    Arrest uses [tenacity](https://github.com/jd/tenacity) under-the-hood for its internal retry process.
    It uses [random exponential backoff](https://tenacity.readthedocs.io/en/latest/api.html#tenacity.wait.wait_random_exponential)
    and in the event of any exception.

    ```python
    my_service = Service(
        name="myservice",
        url="http://example.com",
        resources=[user],
        retry=3
    )
    ```

3. Use your own retry mechanism

    If you want more fine-grained control over your retries, you can disable the in-built retry (`retry=None`), or keep it unset (default None)
    and write your own decorator that wraps around your anciliary function that calls the arrest service under the decorator.
    Here is an example using another popular library [backoff](https://github.com/litl/backoff)

    ```python
    import backoff
    from arrest.exceptions import ArrestHTTPException

    @backoff.on_exception(
        backoff.expo,
        (
            ArrestHTTPException,
            Exception
        ),
        max_retries=5,
        jitter=backoff.full_jitter
    )
    async def fn_caller():
        return await my_service.foo.get("/bar")
    ```

    !!! Note
        When calling the arrest service, do remember that the original httpx exceptions are rethrown as `ArrestHTTPException`
        with the appropriate information. These include the following:

        - `httpx.HTTPStatusError` - for capturing HTTP non-200 error codes, rethrown as `ArrestHTTPException` with the
            same status code and message
        -  `httpx.TimeoutException` - for capturing any request timeout, rethrown as `ArrestHTTPException` with the
            status code 408 (Request Timeout)
        - `httpx.RequestError` - any other error during making the request, rethrown as `ArrestHTTPException` with the
        status code 500 (Internal Server Error)

        Any other exception will be thrown as-is.


### Add support for passing any Python-type* to the request and response type definitions for handlers.

* Needs more clarification as to which types are allowed


### Add custom exception handlers

If you need to enable some custom functionality for any exception during the lifetime of the HTTP request, you can now add
custom exception handlers.

### Add support for writing query parameters into the url string

So far the query parameters had to be provided as an additional keyword-argument to the method caller as `service.get("/users", query={"limit": 10})`.
This was due to the fact that the url pattern matching for the correct handler was based on the complete url parameter, including the query params (the first argument of the method caller).
However, now that condition is removed, you can write the query parameters in the url string as `?limit=10`.

```python
await service.users.get("/all?limit=10&role=admin")
```
