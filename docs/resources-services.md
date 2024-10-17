## Resources
A resource can be thought of as an entity that provides one or more HTTP verb accessors and / or subresources.

Resources have a base `route`, a `name`, (or derived from `route`), and a list of handlers.

Handlers are a list of paths and their correspnding HTTP verb. These are the many different ways of interacting with the said resource.

For example, you can define a resource as followed:

```python
user = Resource(
    route="/users",
    handlers=[
        ("GET", "/"),
        ("POST", "/"),
        ("PUT", "/{user_id:int}"),
        ("DELETE", "/{user_id:int}"),
        ("GET", "/posts"),
        ("POST", "/posts"),
    ]
)
```

---
### Resource-wide response model
You can define a resource-level response model if you want to streamline the output structure for all the handlers to the same response model.

```python

from pydantic import BaseModel
from arrest import Resource

class UserResponse(BaseModel):
    ...

user = Resource(
    route="/users",
    handlers=[
        ("GET", "/"),
        ("POST", "/"),
        ("PUT", "/{user_id:int}"),
        ("DELETE", "/{user_id:int}"),
    ],
    response_model=UserResponse
)
```

---
### Using a client directly

You can choose to run with your own `httpx.AsyncClient` instance. Simply set the `client` field to your resource.

```python
...
import httpx

my_client = httpx.AsyncClient(...)

user = Resource(
    route="/users",
    handlers=[
        ("GET", "/"),
        ("POST", "/"),
        ("PUT", "/{user_id:int}"),
        ("DELETE", "/{user_id:int}"),
    ],
    response_model=UserResponse,
    client=my_client
)
```

You can also use any instance that is a subclass of `httpx.AsyncClient` (e.g. [AsyncOauth2Client from authlib](https://docs.authlib.org/en/latest/client/httpx.html#httpx-oauth-2-0))

The caveat is that you have to manually close the client after you are done. Usually by `await client.aclose()` or something else.

!!! Note
    There is also a `client` field in `Services`. You can also use it to set a service-wide shared client instance

---
### Using httpx arguments
You can directly pass most of the httpx client arguments as kwargs for the Resource instance. This allows you to have a more fine-grained control on configuring the httpx client.

For the full list of available arguments, please check [here](api.md/#httpx-client-arguments)

## Services
Services are the main entrypoint to your API calls. A service is a single url endpoint of a server whose REST APIs you are going to interface.
A service has the following core fields.

- *name* - name of the service
- *url* - URl of the service (without any trailing slashes)
- *resources* - a list of resources for this service

---
### Using a client directly

You can choose to run with your own `httpx.AsyncClient` instance. Simply set the `client` field to your service.

This client will override any client set by any resource, and will be shared across all the http calls.

```python
...
import httpx

my_client = httpx.AsyncClient(...)

user = Resource(
    route="/users",
    handlers=[
        ("GET", "/"),
        ("POST", "/"),
        ("PUT", "/{user_id:int}"),
        ("DELETE", "/{user_id:int}"),
    ],
    response_model=UserResponse,
    client=my_client
)
```

As stated previously, you are in charge of closing the client.

---
### Using httpx arguments
You can directly pass most of the httpx client arguments as kwargs for the Service instance.

This will override these fields if also set from any resource under this service.

For the full list of available arguments, please check [here](api.md/#httpx-client-arguments)


## Root resources

Root resources are special resource definitions that have an empty (root) route (`""`) or (`"/"`).
These are usually top-level endpoints usually used for ping or healthcheck.
We use the reserved name `root` to identify these root resources.
If you want to integrate a root resource in your service, simply add it to the list of resources.

```python
from arrest import Service, Resource

service = Service(
    name="myservice",
    url="http://example.com",
    resources=[
        Resource(
            route="",
            handlers=[
                ("GET", ""),
                ("GET", "/health")
            ]
        )
    ]
)
```

!!! Note
    You can only have one root resource. A resource that has its base route `""`, and another having base route of `"/"` are both root resources and one will override the other.
    If you want to have both `""` and `"/"` routes accessible, specify them as separate handlers in your root resource

    ```python
    Resource(
        route="",
        handlers=[
            ("GET", ""),
            ("GET", "/"),
            ("GET", "/health")
        ]
    )
    ```

To call the endpoints of root resource, you call the HTTP method on the service directly, only specifying the path.
Alternatively, you can use `.root` to explicitly specify the root resource and call its handlers by path and method.

!!! Example

    ```python
    from arrest import Resource, Service

    root_resource = Resource(
        route="",
        handlers=[
            ("GET", ""),       # 1
            ("GET", "/"),      # 2
            ("GET", "/health") # 3
        ]
    )

    myservice = Service(
        name="myservice",
        url="http://example.com",
        resources=[root_resource]
    )

    await myservice.get("")        # calls #1
    await myservice.get("/")       # calls #2
    await myservice.get("/health") # calls #3

    await myservice.root.get("/")  # also works
    ```
