Assuming you already have arrest installed, let's create a simple connection.
We have a REST endpoint `http://example.com/api/v1` which has a resource `/user` with method `GET`.

```python
from arrest import Service, Resource

example_svc = Service(
    name="example",
    url="http://example.com/api/v1",
    resources=[
        Resource(
            name="user",
            route="/user",
            handlers=[
                ("GET", "/")
            ]
        )
    ]
)
```

Now that our service is defined, we can proceed to use it elsewhere.

```python
await example_svc.user.get("/")
```

If we want to enable exception handling, simply import `ArrestHTTPException`, or more generic `ArrestError`

```python
from arrest.exceptions import ArrestHTTPException

try:
    resp = await example_svc.user.get("/")
except ArrestHTTPException as exc:
    print(f"{exc.status_code} {exc.data}")

return resp
```

---
## Using Methods
We have the following HTTP Methods available. They can be found in `arrest.http.Methods` enum.

```
GET
POST
PUT
PATCH
DELETE
HEAD
OPTIONS
```
There are also equivalent helper functions for each of these methods available for your resource.
Simply run `.get`, `.post`, `.put`, `.patch`, `.delete`, `.head`, `.options`.
Or you can directly make use of `.request()` and supply the method in it.

---
## Retries
There are no retries built into Arrest. However they can be configured in many different ways.
You can use the retry mechanism from httpx transport (e.g. `httpx.AsyncHTTPTransport(retries=3)`), or use the `max_retries` field in `Service` or `Resource` specific setting and provide the number of retries. Arrest uses [tenacity](https://github.com/jd/tenacity) under-the-hood for its internal retries.

If you want to learn more, please refer to [the FAQ](faq.md#how-do-retries-work)



---
## Timeouts
Arrest also provides a default timeout of 120 seconds (2 minutes) in all its http requests.
If you want to provide a custom timeout, you can set it at the service level or at the resource level with the `timeout` argument.
Alternatively, if you want to disable timeouts, you can do so by setting `timeout=httpx.Timeout(None)`.

The `timeout` can take either an integer value for the number of seconds, or an instance of `httpx.Timeout`.

If you set `timeout=None`, this is equivalent to `timeout=httpx.Timeout(None)`, which will disable timeouts for the client.


```python
from arrest import Service, Resource


example_svc = Service(
    name="example",
    url="http://example.com/api/v1",
    resources=[
        Resource(
            name="user",
            route="/user",
            handlers=[
                ("GET", "/")
            ]
        )
    ],
    timeout=240 # 4 minutes
)
```

---
## Using the `H()` helper for type-safe handler definitions

Instead of writing raw tuples `("GET", "/", Request, Response)`, you can use
the `H()` helper for keyword-argument clarity and full IDE autocomplete:

```python
from arrest import H, Resource, GET, POST

user_resource = Resource(
    name="users",
    route="/users",
    handlers=[
        H(GET, "/"),
        H(POST, "/", request=NewUserRequest, response=UserResponse),
        H(GET, "/{user_id:str}", response=UserResponse),
        H(PATCH, "/{user_id:str}", request=UpdateUserRequest),
        H(GET, "/{user_id:str}/posts", response=List[PostResponse], headers={"x-custom": "value"}),
    ],
)
```

`H()` returns a `ResourceHandler` and accepts all the same arguments:

| Argument | Type | Description |
|---|---|---|
| `method` | `Methods` | HTTP method (required) |
| `route` | `str` | Handler path relative to the resource (required) |
| `request` | `Any` | Python type to validate request body |
| `response` | `Any` | Python type to deserialize the response |
| `callback` | `Callable` | A sync or async callback executed with the response |
| `headers` | `dict[str, str]` | Default headers for this handler (keyword-only) |

The old tuple syntax `("GET", "/", ...)` and dict syntax still work, so existing
code continues to function.

---
## Understanding `Response[T]`

Every call to a resource handler returns a `Response[T]` — a unified wrapper
that bundles the parsed payload together with transport-level metadata.

```python
resp = await svc.users.get("/")

# Inspect the outcome
resp.is_success        # True if 200–299
resp.is_client_error   # True if 400–499
resp.is_server_error   # True if 500–599
resp.status_code       # int

# Access the parsed body (type-safe if you specified a response model)
user: UserResponse = resp.data

# Access transport-level details
print(resp.url)         # httpx.URL
print(resp.elapsed)     # timedelta | None
print(resp.raw.headers) # raw httpx.Response headers
```

Unlike earlier versions, non-2xx responses **do not** raise `ArrestHTTPException`.
Only transport-level failures (timeout, DNS errors, connection refused) do.
A `404` or `500` response from the server now produces a normal `Response` object
with `is_client_error` or `is_server_error` set to `True`.

```python
resp = await svc.users.get("/999")
if resp.is_client_error:
    print(f"Not found: {resp.status_code}")
    print(resp.data)  # the error body, if any
```

!!! note "Migration"
    If you were catching `ArrestHTTPException` for non-2xx status codes,
    replace the `try/except` with an `if resp.is_success` check instead.
    Alternatively, enable `raise_for_status=True` on your Service, Resource, or
    per-call to restore the legacy behaviour.
    See [What's New](whats-new.md) for details.

---
## Using a Pydantic model for request
You can also provide an additional request type for your handlers. This can be done by passing a third entry to your handler tuple containing the pydantic class, or pass it directly to the handler dict or `ResourceHandler` initialization.

```python
from pydantic import BaseModel

class UserRequest(BaseModel):
    name: str
    email: str
    password: str
    role: str

Resource(
    route="/abc",
    handlers=[
        ("POST", "/", UserRequest) # or ResourceHandler(method="POST", route="/", request=UserRequest)
                                   # or {"method": "POST", "route": "/", "request": UserRequest}
    ]
)
```

Notice how we only supplied `route` for our resource? Arrest automatically infers the resource name based on the resource route. Hence arrest deduces our resource to be `abc`.

Now that our handler is initialized with a request, we can make a request with instances of type `UserRequest`

!!! note "Important"
    All fields in the pydantic model by default will be sent as the JSON body payload.
    If you want to send other params such as `headers`, `query`, or use `Form` / `File`
    for form-encoded requests, see [Configuring your request](configuring-request.md).

---
## Using a pydantic model for response
Similar to request, you can pass an additional fourth argument in the handler tuple for specifying a pydantic model for the handler.
If provided it will automatically deserialize the returned success json response into either a model instance or a list of model instances.

```python
class UserResponse(BaseModel):
    name: str
    email: str
    role: str
    created_at: datetime
    updated_at: datetime
    is_deleted: bool

Resource(
    route="/user",
    handlers=[
        ("GET", "/{user_id}", None, UserResponse), # if no request type to be supplied, leave it as `None`
    ]
)

response = await svc.user.get(f"/{user_id}") # type: UserResponse
```

---
## Using a callback
Sometimes you want to chain a call to another function with the response you get from the api. This can be something like logging or auditing somewhere or triggering another api.
You can already do that by calling the function after awaiting the api call response.
However, Arrest provides a dedicated `callback` option for each handler, which can be passed as the fifth argument to the handler tuple (or set as a field in the dict or `ResourceHandler`).
`callback` can take any callable that can be either sync or async.
If it is specified, the response type from the api call will be the response type of the callback.

!!! Note
    If you specify a response type to your handler, the callback needs to accept argument of appropriate response type.

Any exception thrown by the callback is re-raised.

```python
async def demo_callback(data: Any):
    await asyncio.sleep(1)
    logging.info("foo has been barred")
    return None

service.add_resource(
    Resource(
        route="/user",
        handlers=[
            ResourceHandler(
                method=Methods.GET,
                route="/",
                callback=demo_callback,
            )
        ],
    )
)

response = await service.user.get("/")
# >>> foo has been barred
# response == None
```

---
## Handling exceptions
All of Arrest's exceptions/errors subclass `ArrestError`.

- **`RequestError`** — raised for transport-level failures (timeout, DNS errors,
  connection refused). It carries a `message` string.
- **`ArrestHTTPException`** — raised *only* when `raise_for_status=True` is set
  and the server responds with a non-2xx status. Carries `status_code` and `data`.
- **`ResponseError`** — raised when the response body cannot be parsed.
- **`HandlerNotFound`** — raised when no matching handler is found for the request.

!!! example

    ```python
    from arrest.exceptions import RequestError, ArrestHTTPException

    try:
        response = await xyz_service.users.get("/123")
        if not response.is_success:
            print(f"Error: {response.status_code}")
    except RequestError as exc:
        logging.warning(f"Request failed: {exc.message}")
    ```


---
## Adding a custom handler
If you want to add a custom function to handle an api request and have complete control over the request and response, you can use the `Resource.handler` decorator to decorate an async function and write your own custom logic.
You have to specify the path relative to the resource in the decorators argument.
This function will be registered as a method to the same resource you're decorating it with and can be accessed as `await resource.function_name(...)`
You can also invoke the function as a free function as `await function_name(...)`

!!! Important
    Creating a handler this way does not have any data validation or pydantic wrapping enabled. Neither does it do exception handling.
    It only does the default retry on exceptions using `tenacity`.

If you use the decorator, the first two arguments of your decorated function will have to be defined as `self` and `url`.
The `url` will be the fully-constructed path using the service's `base_url`, the resource's `route` and the provided `path` in the decorator, should you choose to use it,

The `self` argument is a reference to the same resource instance you're decorating the function with, this means you can access all the members of the `Resource` class inside your function. Including `self._client`, which is where your custom client instance is stored if you have set it during your resource initialization (or injected it via service).

You can also access all the httpx related args using `self.httpx_args` which is a dictionary, so you can easily instantiate your own AsyncClient by unpacking it.

Or you can just roll with your own custom logic.

Once defined you have to access the function via the resource instance, as it is now a member of your resource.

!!! example

    ```python
    res = Resource(
        route="/user",
        handlers=[
            ("GET", "/"),
            ("POST", "/"),
        ]
    )

    svc = Service(
        name="my_service",
        url="http://www.example.com",
    )

    svc.add_resource(res)

    @svc.user.handler("/media")
    async def download_user_metadata(self, url, *, meta_id: int):
        # url == http://www.example.com/user/media
        urlnew = f"{url}/{meta_id}
        async with httpx.AsyncClient(...) as client:
            resp = await client.get(urlnew)
            ...

        # or
        async with httpx.AsyncClient(**self.httpx_args) as client:
            resp = await client.get(urlnew)

        # or
        resp = await self._client.get(urlnew) # if client is specified


    metadata = await svc.user.download_user_metadata(meta_id=123)

    # or
    metadata = await download_user_metadata(meta_id=123)
    ```
