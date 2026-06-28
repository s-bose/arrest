<h1 align="center" style="font-size: 3rem; margin: 0">
Arrest
</h1>

---

<div align="center">
    <p>
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
            <img src="https://img.shields.io/pypi/v/arrest">
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
</div>

- **Documentation**: https://s-bose.github.io/arrest/

---

Arrest is a **type-safe HTTP client** for Python built on [httpx](https://www.python-httpx.org/) and [Pydantic](https://docs.pydantic.dev/). Define your REST APIs declaratively — routes, request/response models, retries, and error handling in one place — and get full static analysis, autocomplete, and runtime validation for every call.

### Features

- **Type-safe** — Pydantic models, dataclasses, dicts, lists, and XML models for request and response validation
- **Declarative** — Services, resources, and handlers keep your API surface organized
- **JSON, Form, Multipart, and XML** — `application/json`, `application/x-www-form-urlencoded`, `multipart/form-data`, and `application/xml` content types
- **Retries** — Built-in exponential backoff via tenacity, or transport-level retries via httpx
- **Exception handling** — Custom hooks per exception type, clean `RequestError` for transport failures
- **OpenAPI codegen** — Generate Arrest services and Pydantic models from an OpenAPI spec
- **`H()` helper** — IDE-friendly handler definitions with keyword-argument autocomplete
- **Unified `Response[T]`** — One response type for all HTTP status codes with `is_success`, `is_client_error`, etc.

---

## Installation

### uv
```bash
uv add arrest
```

### pip
```bash
pip install arrest
```

### OpenAPI support (optional)
```bash
uv add 'arrest[openapi]'
```

---

## Quickstart

```python
from arrest import H, Resource, Service, GET, POST

user = Resource(
    route="/users",
    handlers=[
        H(GET, "/"),
        H(GET, "/{user_id}"),
        H(POST, "/", request=NewUserRequest, response=UserResponse),
    ],
)

svc = Service(
    name="api",
    url="https://api.example.com/v1",
    resources=[user],
)

# GET /users
resp = await svc.users.get("/")
if resp.is_success:
    print(resp.data)

# POST /users with type-safe request body
resp = await svc.users.post("/", request=NewUserRequest(name="Alice", email="a@b.com"))
```

---

## XML, Form, and File uploads

```python
from pydantic_xml import BaseXmlModel, element
from arrest.params import Form, File
from arrest.types import UploadFile

# XML request/response
class XmlPayload(BaseXmlModel, tag="payload"):
    key: str = element()
    value: str = element()

# Form-encoded
class Login(BaseModel):
    username: str = Form(...)
    password: str = Form(...)

# Multipart file upload
class Profile(BaseModel):
    name: str = Form(...)
    avatar: UploadFile = File(...)
```

---

## OpenAPI codegen

```bash
arrest --url https://petstore3.swagger.io/api/v3/openapi.json -o ./generated
```

Generates `models.py`, `resources.py`, and `services.py` from any OpenAPI spec.

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

---

## License

MIT
