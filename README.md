<p align="center">
    <a href="https://pepy.tech/projects/arrest">
        <img src="https://static.pepy.tech/badge/arrest" alt="PyPI Downloads">
    </a>
    <a href="https://github.com/s-bose/arrest/actions/workflows/tests.yml">
        <img src="https://github.com/s-bose/arrest/actions/workflows/tests.yml/badge.svg">
    </a>
    <a href="https://codecov.io/github/s-bose/arrest">
        <img src="https://codecov.io/github/s-bose/arrest/graph/badge.svg?token=VBU3156QHP">
    </a>
    <a href="https://pypi.python.org/pypi/arrest">
        <img src="https://img.shields.io/pypi/v/arrest.svg">
    </a>
    <a href="https://www.codefactor.io/repository/github/s-bose/arrest">
        <img src="https://www.codefactor.io/repository/github/s-bose/arrest/badge" alt="CodeFactor">
    </a>
    <a href="https://github.com/s-bose/arrest">
        <img src="https://img.shields.io/pypi/pyversions/arrest" alt="PyPI - Python Versions">
    </a>
    <a href="https://github.com/s-bose/arrest/blob/master/LICENSE">
        <img src="https://img.shields.io/pypi/l/arrest" alt="PyPI - License">
    </a>
</p>

---

# Arrest

- Documentation: https://s-bose.github.io/arrest/

Enable data validation for REST APIs.

Arrest is an HTTP client library with an easy and declarative way of defining, managing, and calling RESTful HTTP APIs with type validation, retries, exception handling, and other batteries included.

Arrest lets you define your RESTful APIs in a simple encapsulation that takes care of the following:
1. Type validation for HTTP request and response data
2. HTTP request retries
3. Manage your services definitions in one place
4. Exception handling
5. Hooks for custom exceptions
6. Callbacks
7. Automatic code generation from OpenAPI Schema

## Contents

1. [Installation](#installation)
2. [Getting Started](#getting-started)
3. [Examples](#examples)
4. [Contributing](#contributing)
5. [Roadmap](#roadmap)

## Installation

### Using pip
```bash
pip install arrest
```

### Using poetry
```bash
poetry add arrest
```

### Using uv
```bash
uv add arrest
```

## Getting Started

Assuming you already have arrest installed in your system, let us create a simple connection.
We have a REST endpoint `htthttps://www.xyz-service.default.local.cluster/api/v1` which has a resource `/users` with method `GET`.

```python
import logging
from arrest import Resource, Service
from arrest.exceptions import ArrestHTTPException


xyz_service = Service(
    name="xyz",
    url="https://www.xyz-service.default.local.cluster/api/v1",
    resources=[
        Resource(
            route="/users",
            handlers=[
                ("GET", "/"),
                ("GET", "/{user_id:int}"),
                ("POST", "/")
            ]
        )
    ]
)

try:
    response = await xyz_service.users.get("/123")
except ArrestHTTPException as exc:
    logging.warning(f"{exc.status_code} {exc.data}")
```

This will make an HTTP GET request to `https://www.xyz-service.default.local.cluster/api/v1/users/123`.

You can also provide a request type for your handlers. This can be done by passing a third entry to your handler tuple containing the pydantic class, or pass it directly to the handler dict or `ResourceHandler` initialization.

```python
from pydantic import BaseModel

class UserRequest(BaseModel):
    name: str
    email: str
    password: str
    role: str

Resource(
    route="/users,
    handlers=[
        ("POST", "/", UserRequest) # or ResourceHandler(method="POST", route="/", request=UserRequest)
                                   # or {"method": "POST", "route": "/", "request": UserRequest}
    ]
)

await service.users.post("/", request={
    "name": "John Doe",
    "email": "john_doe@gmail.com",
    "password": "secret",
    "role": "admin"
    }
)
```

This gets automatically validated and parsed as `UserRequest` before sending the request payload to the server. If any validation error is raised the request won't go.


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

user_id = "123"
response = await svc.user.get(f"/{user_id}") # type: UserResponse
```

Here, the JSON response from `https://www.xyz-service.default.local.cluster/api/v1/users/123` will be deserialized into `UserResponse` model instance.

For more info, please check the [docs](https://s-bose.github.io/arrest/getting-started)

## Examples

You can check out the `example` folder under the project repository to get a feel of how to use Arrest.

The `example_service` contains a minimal FastAPI application for task management with CRUD endpoints for `users` and `tasks`.

To generate the Arrest boilerplate from the OpenAPI specs, simply run the FastAPI application using `uvicorn` at [http://127.0.0.1:8080/docs](), and run the arrest CLI as followed:

```bash
$ arrest -u http://localhost:8080/openapi.json -d example_service
```
This will generate `models.py`, containing the Pydantic schemas corresponding to the OpenAPI components, a `resources.py` containing the RESTful resource definitions and a `services.py` containing the service definition that includes the resources.

To use the service, simply call `example_service.users.get("")`.


## Contributing

Please see the [CONTRIBUTING.md](CONTRIBUTING.md) for more information.

## Roadmap

Arrest is under active development. Listed below are a few ideas for the next release. Any sort of contribution towards them is very much welcome.

1. Support for non-JSON request and response types.

Arrest is currently limited by its strict requirement of the APIs being JSON compliant.
The following types would be supported in the next release:

- `FormData` requests

```python
from arrest.types import FormData

class UserForm(FormData):
    username: str
    password: str
```

- `UrlEncoded` requests

    ```python
    from arrest.types import UrlEncoded

    class UserRegister(UrlEncoded):
        email: str
        password: str
    ```

- `XML` responses

```python
from pydantic import Field
from arrest.types import XMLResponse

class UserResponse(XMLResponse):
    id: str
    username: str
    email: str
    role: str = Field(alias="@role")
```

For requests, I think its beneficial to have types for `application/form-data` and `application/x-www-form-urlencoded` with the added parsing and validation of Pydantic.
`FormData` and `UrlEncoded` classes themselves will be inherited from `pydantic.BaseModel`.

For responses, it would be nice to have a way to parse the XML response into some sort of data model, because you most probably would always do that (unless you like working with raw strings).
`XMLResponse` is similarly inherited from `pydantic.BaseModel`. If you use just `XMLResponse` in declaring your handler response type, the response will automatically be converted into a python dictionary.

- As of now, I have no plans for making a request type for XML. But what would be a better alternative is the ability to do something like this:

```python
from arrest import Resource
from arrest.types import XMLResponse

user = Resource(
    route="/users",
    handlers=[
        ("POST", "/user_data", str, XMLResponse)
    ]
)


user_data = """<User>
    <Id>123</Id>
    <Name>John</Name>
    <Email>john@email</Email>
    <Role>admin</Role>
</User>"""

response = await service.user.post("/user_data", data=user_data, headers={"Content-Type": "application/xml"})

assert response == {"Id": "123", "Name": "John", "Email": "john@email", "Role": "admin"}
```

The problem with using a data model for XML requests is the fact that the deserialization of the model might not always produce an XML string that conforms to the expected schema.

However, I would encourage anyone who has any idea about any of this, or a better way to support these types, to [open an issue](https://github.com/s-bose/arrest/issues) and start a discussion.
