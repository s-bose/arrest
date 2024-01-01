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

    2. Use `alias` in your pydantic field (if you are using pydantic@v2 then you need to use `serialization_alias` instead).

    3. Set the pydantic config to `allow_population_by_field_name` (if pydantic@v2, use `ConfigDict.populate_by_name`).

    ```python
    class UserRequest(BaseModel):
        x_user_agent: str = Header(serialization_alias="x-user-agent")

        model_config = ConfigDict(populate_by_name=True)

    await service.user.post("/", request=UserRequest(x_user_agent="mozila"))
    # header = {"x-user-agent": "mozila"}
    ```

    ```python
    # using pydantic@v1

    class UserRequest(BaseModel):
        x_user_agent: str = Header(alias="x-user-agent")

        class Config:
            allow_population_by_field_name = True

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

### Additional Configuration
Arrest also allows providing other http parameters such as cookies, auth, transport, etc, or even your own instance of `httpx.AsyncClient` (or other classes subclassing it), if you choose to do so.
If you want to customize the httpx client and specify more parameters either at resource-level or at service-level, you can check out [Resources & Services](resources-services.md/#resources).

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
