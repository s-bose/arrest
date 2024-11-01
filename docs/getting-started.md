Assuming you already have arrest installed in your system, let us create a simple connection.
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
There are no retries built-in in Arrest. However they can be configured in many different ways.
You can use the retry mechanism from httpx transport (e.g. `httpx.AsyncHTTPTransport(retries=3)`), or use the `retry` field in `Service` or `Resource` specific setting and provide the number of retries. Arrest uses [tenacity](https://github.com/jd/tenacity) under-the-hood for its internal retries.

If you want to learn more, please refer to [this](whats-new.md#standardized-retry-mechanism-with-more-flexibility)



---
## Timeouts
Arrest also provides a default timeout of 120 seconds (2 minutes) in all its http requests.
If you want to provide a custom timeout, you can put it at a service-level or at a resource-level in the `timeout` argument.
Alternatively, if you want to disable timeouts, you can do so by setting `timeout=httpx.Timeout(None)`.

The `timeout` can take either an integer value for the number of seconds, or an instance of `httpx.Timeout`.


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
    route="/abc,
    handlers=[
        ("POST", "/", UserRequest) # or ResourceHandler(method="POST", route="/", request=UserRequest)
                                   # or {"method": "POST", "route": "/", "request": UserRequest}
    ]
)
```

Notice how we only supplied `route` for our resource? Arrest automatically infers the resource name based on the resource route. Hence we have deduced our resource to be `abc`.

Now that our handler is initialized with a request, we can make a request with instances of type `UserRequest`

!!! note "Important"
    All fields in the pydantic model by default will be sent as the JSON body payload. If you want to send other params such as `headers` or `query`, see below.

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
    if you specify a response type to your handler, the callback needs to accept argument of appropriate response type.

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
The most important one is `ArrestHTTPException` which wraps the httpx-specific errors that might occur from making a request.
Any response that does not have a success status code (i.e. 200-299) will throw an `ArrestHTTPException` with the appropriate `status_code` and `data`.

!!! example

    ```python
    try:
        response = await xyz_service.users.get("/123")
    except ArrestHTTPException as exc:
        logging.warning(f"{exc.status_code} {exc.data}")
        # do something with the error response
    ```

Any other error such as `TimeoutException` or `RequestError` will result in a `ArrestHTTPException` with `status_code=500`
See [API Documentation](api.md) for further details.


---
## Adding a custom handler
If you want to add a custom function to handle an api request and have complete control over the request and response, you can use the `Resource.handler` decorator to decorate an async function and write your own custom logic.
You have to specify the path relative to the resource in the decorators argument.
This function will be registered as a method to the same resource you're decorating it with and can be accessed as `await resource.function_name(...)`
You can also invoke the function as a free function as `await function_name(...)`

!!! Important
    Creating a handler this way does not have any data validation or pydantic wrapping enabled. Neither does it do exception handling.
    It only does the default retry on httpx Exceptions using `backoff`.

If you use the decorator, the first two arguments of your decorated function will have to be defined as `self` and `url`.
The `url` will be the fully-constructed path using the service's `base_url`, the resource's `route` and the provided `path` in the decorator, should you choose to use it,

The `self` argument is a reference to the same resource instance you're decorating the function with, this means you can access all the members of the `Resource` class inside your function. Including `self._client`, which is where your custom client instance is stored if you have set it during your resource initialization (or injected it via service).

You can also access all the httpx related args using `self._httpx_args` which is a `TypedDict`, so you can easily instantiate your own AsyncClient by unpacking and initializing with those args.

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
        async with httpx.AsyncClient(**self._httpx_args) as client:
            resp = await client.get(urlnew)

        # or
        resp = await self._client.get(urlnew) # if client is specified


    metadata = await svc.user.download_user_metadata(meta_id=123)

    # or
    metadata = await download_user_metadata(meta_id=123)
    ```
