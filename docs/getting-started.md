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
We also provide a few additional classes that you can assign to your pydantic fields. They are inherited from pydantic's `FieldInfo` to ensure compatibility.

### Headers
```python
from arrest.params import Header

class HeaderRequest(BaseModel):
    x_max_age: str = Header(...)
    x_cookie: str = Header(...)
```

We will automatically convert any non-str values to str and convert `snake_case` to `kebab-case` before sending the fields as headers in the request.
You can also specify resource-wide headers as a dict in your resource definition.
```python
Resource(route="/abc", headers={"x-age": "20"}, handlers=[...]) # this will now be used for any request from resource `abc`
```


### Query
```python
from arrest.params import Query

class QueryRequest(BaseModel):
    limit: int = Query(...)
    name: str = Query(...)
    index: int | None = Query()
```

For query no such formatting is done. Whatever field is marked as `Query` will be attached as a query parameter in the request.
```
http://example.com/abc?limit=100&name=abc&index=145
```


### Body
```python
from arrest.params import Body

class BodyRequest(BaseModel):
    name: str = Body(...)
    email: str
    password: str
    role: Optional[str]
    is_active: bool
```

For body, you don't need to explicitly mark a field as `Body`. But when you do, you get the extra validation features of pydantic's `FieldInfo`. [see more](https://docs.pydantic.dev/latest/api/fields/#pydantic.fields.FieldInfo)

```python
class BodyRequest(BaseModel):
    name: str = Body(default="jeff", gt=10)
    email: str
    password: str
    role: Optional[str]
    is_active: bool
```


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

There are many ways you can supply the path param. The most common way is to use a python f-string.

```python

```
