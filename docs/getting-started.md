# Getting Started

Assuming you already have arrest installed in your system, let us create a simple connection.
We have a REST endpoint `http://example.com/api/v1` which has a resource `/user` with method `GET`

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


## Configuring your request
If you want to enrich your HTTP request with additional arguments such as headers or query parameters, you can specify them in the HTTP request as dictionaries in `headers` and `query` fields.
Additionally, Arrest offers custom field types `Header`, `Query` and `Body`, which are inherited from pydantic's [`FieldInfo`](https://docs.pydantic.dev/latest/api/fields/#pydantic.fields.FieldInfo), that you can use in defining your pydantic request model.


### Header

You can use the `headers` keyword-argument in the request method to directly pass a set of key-value pairs as headers.

!!! example "using `headers` kwarg"

    ```python
    await service.user.get("/posts", headers={"x-max-age": "20", "x-organization": "abc-123"})
    ```

If you want resource-wide shared header definition, you can set it in the `Resource` definition as well. You can use both of these together as all the headers will be collected and sent as a whole.

!!! example "using `Resource.headers`"

    ```python
    service.add_resource(
        Resource(
            route="/user",
            handlers=[
                (Methods.GET, "/profile"),
            ],
            headers={"x-organization": "abc-123"}
        )
    )

    await service.user.get("/posts", headers={"x-max-age": "20"})
    ```

If you want to define your headers as part of your request model, use `arrest.params.Header` to specify the header fields in your request.
This is useful when you want to group together all the components of your request inside one data model.

!!! example "using `Header` class"

    ```python
    from arrest.params import Header

    class HeaderRequest(BaseModel):
        x_max_age: str = Header(...)
        x_cookie: str = Header(...)

    await service.user.get("/posts", request=HeaderRequest(x_max_age="20", "x_cookie": "xyz"))
    ```

!!! warning
    Arrest does NOT convert any non-str values to str and convert `snake_case` to `kebab-case` before sending the fields as headers in the request.
    If you want to send `kebab-case` headers you need to:
    1. specify them as `kebab-case` in the dictionary passed to the `headers` keyword or Resource class definition.
    2. Use `serialization_alias` in your pydantic field info.

    ```python
    class UserRequest(BaseModel):
        x_user_agent: str = Header(serialization_alias="x-user-agent")

    await service.user.post("/", request=UserRequest(x_user_agent="mozila"))
    # header = {"x-user-agent": "mozila"}
    ```


### Query
Similar to headers, you can provide your request-specific query parameters as a dict to the `query` kwarg in the request method.

!!! example "using `query` kwarg"

    ```python
    await service.user.get("/posts", query={"limit": 100, "username": "abc"})
    ```

If you want to define your query parameters as part of your request model, use `arrest.params.Query` to specify the query fields in your request.
Whatever field is marked as `Query` will be attached as a query parameter in the request.

!!! example "using `Query` class"

    ```python
    from arrest.params import Query

    class QueryRequest(BaseModel):
        limit: int = Query(...)
        name: str = Query(...)
        index: int | None = Query()

    await service.user.get("/posts", request=QueryRequest(limit=100, name="abc", index=10))
    ```



### Body

Request body is supplied with the keyword argument `request` in your call.
This can be a pydantic instance, a simple dictionary, a list or any object that can be jsonified.

However, if the handler for the path has a request type specified, the request body must match the type (or be convertible to it).
You can make use of `arrest.params.Body` when defining the body fields, although fields that don't have any defaults will be automatically parsed as body.

!!! example "using request type"

    ```python
    from arrest.params import Body

    class BodyRequest(BaseModel):
        name: str = Body(...)
        email: str
        password: str
        role: Optional[str]
        is_active: bool

    # both of the following should work
    await service.user.post("/", request=BodyRequest(name="abc", email="abc@email.com", password="123", role="ADMIN", is_active=False))
    await service.user.post("/", request={"name": "abc", "email": "abc@email.com", "password": "123", "role": "ADMIN", "is_active": False})
    ```

If you do not have a request type specified to the handler, you can still pass a pydantic object but no model validation will take place and Arrest will extract the fields as per their defaults.
You can also pass a plain dictionary or a list as request. They will get passed as json payload.

!!! note "regarding json payloads"
    Arrest uses `orjson` for serializing the request payload. This was chosen because the stdlib `json` does not parse datetime which `orjson` does.

### Path parameters
Path parameters are a bit tricky as they are not set as pydantic fields.
To define a handler that takes a path parameter, you have to specify the path-params inside curlys with (optional) their types.

```python
Resource(
    route="/abc",
    handlers=[
        ("GET", "/user/{user_id}"),
        ("GET", "/user/{user_id:uuid}"),
        ("GET", "/user/{user_id}/comments/{comment_id:int}")
    ]
)
```

!!! note "Regarding multiple handlers"
    If you specify handlers with the same path parameter but different type hints, the most recent one will override all the others. So in the above example, we only have one handler `GET /user/{user_id:uuid}`

    This is because we keep track of unique handlers with the pair `<method, route>` where `route` is the handler route with its type hint removed.
    Subsequent handler definitions with varying path parameter types will thus override the entry.

There are many ways you can supply the path param. The most common way is to use a python f-string (considering the path-param is dynamic)

```python
...
user_id = uuid.UUID("ca80a889-8811-4e65-86bb-5e7c0c6e07cf")

...
service.abc.get(f"/user/{user_id}")
```

Alternatively, you can pass it as a static string.
```python
service.abc.get("/user/ca80a889-8811-4e65-86bb-5e7c0c6e07cf")
```

if f-strings are not cool enough for you, there is another alternative, albeit experimental, where you can pass the path-parameter(s) as kwargs in your request function.

```python
service.abc.get("/user", user_id=user_id)
# or
service.abc.get(f"/user/{user_id}/comments", comment_id=comment_id)
```

!!! Note
    If the resource contains only one handler and that handler url contains multiple path params like this:

    ```python
    Resource(
        route="/user",
        handlers=[
            (Methods.POST, "/profile/{id:int}/comments/{comment_id:int}"),
        ],
    )
    ```

    then you can pass all the path_params as kwargs in the request by specifying the url as `/user`

    ```python
    user.post("/profile", id=123, comment_id=456)
    user.post("/profile/123", comment_id=456)
    user.post("/profile/123/comments", comment_id=456)
    user.post("/profile/123/comments/456") # all 4 would work
    ```

    However if it contains specific paths from `/profile`, then you need to specify the sub-resource name of the specific `profile`

    ```python
    Resource(
        route="/user",
        handlers=[
            (Methods.POST, "/profile/{id:int}"),
            (Methods.POST, "/profile/{id:int}/comments/{comment_id:int}"),
        ],
    )

    user.post("/profile", id=123, comments=456) # wont work
    user.post("/profile/123/comments/", comments=456) # will work
    ```

!!! note "About url paths"
    If the endpoint you are trying to call ends with a trailing slash (/), you need to specify the relative path to the handler also with the trailing slash (/).

    ```python
    (GET,  ""),
    (GET, "/")
    ```
    are considered two different handlers.
    This does not apply when you are passing kwargs as path-parameters and Arrest will construct and find a match for the full path.

    ```python
    # both will work
    user.post("/profile/123/comments", comments=456)
    user.post("/profile/123/comments/", comments=456)

    ```
## Using converters
Arrest uses converters for the following types to validate and stringify the passed kwarg path-params to construct the url.
- `int`
- `float`
- `str`
- `UUID`

If you want to run with a custom datatype as path-param, you can add a converter and regex for it by subclassing `arrest.converters.Converter` and add the converter to Arrest by `add_converter(...)`


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
