# Arrest

[![Tests](https://github.com/s-bose/arrest/actions/workflows/tests.yml/badge.svg)](https://github.com/s-bose/arrest/actions/workflows/tests.yml)

[![codecov](https://codecov.io/github/s-bose/arrest/graph/badge.svg?token=VBU3156QHP)](https://codecov.io/github/s-bose/arrest)

[![PyPi](https://img.shields.io/pypi/v/arrest.svg)](https://pypi.python.org/pypi/arrest)

- Documentation: https://s-bose.github.io/arrest/
0.30.6
Enable data validation for REST APIs.

Arrest provides an easy and declarative way of defining, managing, and calling RESTful HTTP APIs with type validation, retries, exception handling, and other batteries included.

Arrest lets you define your RESTful API services in a simple encapsulation that takes care of the following:
1. Type validation for request and response data
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
