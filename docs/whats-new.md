## Added support for decorating custom handlers for your resource.

Earlier in v0.1.9 the decorator could only be used with a resource under its parent service's scope:

```python
@myservice.user.handler("/path")
async def path_handler(self, url, *args, **kwargs):
    ...
```

This was not a clear separation of concern. Ideally in Arrest, we want you to be able to define everything relating to a resource within the resource, and everything relating to a service within the service, and simply interface the resources with your service, or multiple services. In v0.1.10, you can use the handler with your resource, without having to connect it to a service first and use the service's scope:

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

## Standardized the names of resource and services from parsing the OpenAPI Specification.

Certain names for resources and services had whitespaces and special characters, which resulted in the generated code having illegal variable names (such as `OpenAPI service: 2.1 = Service(...)`)

v0.1.10 standardizes all variable names of the generated service and resource to lower and snake_cased.

## Add support for root-level resources.

You can now define root-level resources (i.e., having base routes of either `""` or `"/"`) There can be only one root-level resource, for obvious reasons. You can set them up as normal `Resource` instances with `route=""` or `route="/`" and a corresponding handler `(<Method>, "")` (e.g. `www.example.com`) or `(<Method>, "/")` (e.g. `www.example.com/`)

In order to make the call to the root-resource, you simply invoke the http methods on the service directly, without specifying a resource.

```python
await my_service.get("") # or my_service.get("/")
```

!!! Note
    This is only applicable if you have a path with no suffix at the root level. i.e. `www.example.com/`. If you want to access `www.example.com/path`, then the following won't work.

```python
Resource(route="/", handlers=[("GET", "/path")])

await service.get("/path") # throws ResourceNotFound
```

Because `/path` constitutes a resource on its own, not a subpath for a root-resource `/`, hence the following would need to be written

```python
Resource(route="/path", handlers=[("GET", "")])

await service.path.get("") # works!
```

General rule-of-thumb is, a RESTful resource always has a path prefix, and arrest resources should preferrably be designed around that
notion. If you have an endpoint with only the root-level being the accessible API, you might want to create a root-resource with
a single handler.

## Standardized retry mechanism with more flexibility

The previous built-in retry mechanism was too restrictive and lacked configurability. In the new version, there will not be any retry by default. This is to reduce as much side-effect as possible from the HTTP calls in favour of developer expectations. If you want to enable retries there are a few different ways.

### _Use the standard retry mechanism from httpx transport_

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

### _Use the retry mechanism from arrest_

Arrest provides an additional keyword-argument `retry` either at service-level, or at individual resource-level. It is defaulted to `None`, should you opt for no retries (the default behaviour). However, you can set it to any valid integer resembling the number of times it should retry.

Arrest uses [tenacity](https://github.com/jd/tenacity) under-the-hood for its internal retry process. It uses [random exponential backoff](https://tenacity.readthedocs.io/en/latest/api.html#tenacity.wait.wait_random_exponential) and in the event of any exception.

```python
my_service = Service(
    name="myservice",
    url="http://example.com",
    resources=[user],
    retry=3
)
```

### _Use your own retry mechanism_

If you want more fine-grained control over your retries, you can disable the in-built retry (`retry=None`), or keep it unset (default None) and write your own decorator that wraps around your anciliary function that calls the arrest service under the decorator. Here is an example using another popular library [backoff](https://github.com/litl/backoff)

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
    When calling the arrest service, do remember that the original httpx exceptions are rethrown as `ArrestHTTPException` with the appropriate information. These include the following:

    - `httpx.HTTPStatusError` - for capturing HTTP non-200 error codes, rethrown as `ArrestHTTPException` with the same status code and message
    - `httpx.TimeoutException` - for capturing any request timeout, rethrown as `ArrestHTTPException` with the status code 408 (Request Timeout)
    - `httpx.RequestError` - any other error during making the request, rethrown as `ArrestHTTPException` with the status code 500 (Internal Server Error)


## Add support for passing any Python-type* to the request and response type definitions for handlers.

With v0.1.10, you can use any python type (that is json-serializable, ofcourse) for request and response in the handler definitions.
The following types are tested for full support:
1. `primitive types`
2. `pydantic.BaseModel`
3. `dataclasses.dataclass`
4. `pydantic.RootModel` (v2 only)
5. `dict` and `typing.Dict`
6. `list` and `typing.List`
7. `typing.Optional` and `typing.Union`

You can use any combination of them to define your request and response types, and the requests / responses will be parsed according to the type definitions.

!!! Example
    ```python
    from arrest import Resource, Service
    user = Resource(
                name="users",
                route="/users",
                handlers=[
                    ("GET", "", None, UserSchema),
                    ("POST", "", UserCreate, UserSchema),
                    ("GET", "/{user_id}", None, UserSchema),
                    ("GET", "/all", None, list[UserSchema])
                ]
            )

    my_service = Service(
        name="myservice",
        url="http://example.com",
        resources=[user],
    )

    response = await my_service.user.get("/all?limit=10") # list[UserSchema]
    ```

## Add custom exception handlers

If you need to enable some custom functionality for any exception during the lifetime of the HTTP request, you can now add custom exception handlers.
Oftentimes, you would like to reraise the exception as a `fastapi.HTTPException` if you are proxying the requests to the service. A typical example use-case would look something like this:

```python
from arrest.exceptions import ArrestHTTPException, ArrestError

def http_exc_handler(exc: ArrestHTTPException):
        raise HTTPException(status_code=exc.status_code, detail=exc.data)

def err_handler(_exc: ArrestError):
    raise HTTPException(status_code=500, detail="Something went wrong")

def generic_err_handler(_exc: Exception):
    logging.warning("Something went wrong")


my_service = Service(
    name="myservice",
    url="http://example.com",
    resources=[user],
)

service.add_exception_handlers(
    exc_handlers={
        Exception: generic_err_handler,
        ArrestHTTPException: http_exc_handler,
        ArrestError: err_handler,
    }
)
```

This makes the service automatically call the appropriate exception handler function upon receiving the specific exception after making the request.

**Note** - Arrest rethrows the `httpx` exceptions as `ArrestHTTPException`, hence you won't be able to, for example, use exception handlers for `httpx.HTTPStatusError`.


## Add support for writing query parameters into the url string

So far the query parameters had to be provided as an additional keyword-argument to the method caller as `service.get("/users", query={"limit": 10})`. This was due to the fact that the url pattern matching for the correct handler was based on the complete url parameter, including the query params (the first argument of the method caller). However, now that condition is removed, you can also write the query parameters in the url string as `?limit=10`.

```python
await service.users.get("/all?limit=10&role=admin")
```

## Add support for default GET handlers for resources

Arrest now automatically adds a default GET handler to the resource route, which means, if your resource looks like this:

```python
user = Resource(
    name="user",
    route="/user"
)
```

You wouldn't need to add any handler for the resource root, you can directly call `service.user.get("")` Additionally, if you specify `response_model` keyword-argument in the Resource initializer, the GET response will be automatically parsed as the `response_model`.

```python
user = Resource(
    name="user",
    route="/user",
    response_model=UserSchema
)

response = await service.user.get("")
assert isinstance(response, UserSchema) # True
```

!!! Note
    This works by splitting the resource route into the resource's base route, and the suffix, which becomes the default GET handler route. For example, if your resource route is `"/users"`, the default handler will be `("GET", "")`, and you can call `service.users.get("")` But if your resource route is `"/users/"`, the default handler will be `("GET", "/")`, and you can call `service.users.get("/")`.


This also works similarly for root-level resources for the service.
If your root-level resource is at `"/"`, you can call `service.get("/")` or `service.root.get("/")`,
but if the root-level resource is at `""`, you have to call `service.get("")` or `service.root.get("")`.


You can overwrite the default handler by rewriting it in the handlers list.

```python
user = Resource(
    name="user",
    route="/user",
    handlers=[
        ("GET", "", UserSchema), # overwrites default ("GET", "")
        ("GET", "/{usder_id:str}", UserSchema)
    ]
)
```

## Fixed improper imports of pydantic schemas from the OpenAPI generation

The OpenAPI schema that is generated by FastAPI can have weird names for the schema components. If your FastAPI endpoint does not have a predefined Pydantic model for it's request but instead you are using them as the endpoint function parameters, the generated schema name will be

```python
@app.post("/foo")
async def post_custom_request_with_query_header_body(
    request: Request,
    foo: str = Body(...),
    bar: str = Body(...),
    x_api_key: str = Header(...),
    x_secret: str = Header(...),
    limit: Optional[int] = Query(10),
    user_id: Optional[str] = Query(None),
):
    ...
```

The above endpoint generates the following openapi schema:

```json
"Body_post_custom_request_with_query_header_body_custom_post": {
    "properties": {
        "foo": {
        "type": "string",
        "title": "Foo"
        },
        "bar": {
        "type": "string",
        "title": "Bar"
        }
    },
    "type": "object",
    "required": [
        "foo",
        "bar"
    ],
    "title": "Body_post_custom_request_with_query_header_body_custom_post"
    }
```

When parsing this OpenAPI schema, the generated pydantic schema uses correct pascal-casing (`class BodyPostCustomRequestWithQueryHeaderBodyCustomPost`), but when importing them in the generated `resources.py` they were incorrectly using the snake_case name from the OpenAPI specification. This has been fixed now, and both `models.py` and `resources.py` will have the correct PascalCase named imports of the schema models.

## Named constants for HTTP Methods

Instead of writing HTTP methods as string literals, or using `arrest.http.Methods` enum, you can also import them as constants.

```python
from arrest import GET, POST, Resource

user = Resource(
    name="user",
    route="/user",
    handlers=[
        (GET, "/"),
        (POST, "/login")
    ]
)
```
