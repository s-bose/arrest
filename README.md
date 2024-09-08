# Arrest

[![Tests](https://github.com/s-bose/arrest/actions/workflows/tests.yml/badge.svg)](https://github.com/s-bose/arrest/actions/workflows/tests.yml)

[![codecov](https://codecov.io/github/s-bose/arrest/graph/badge.svg?token=VBU3156QHP)](https://codecov.io/github/s-bose/arrest)

[![PyPi](https://img.shields.io/pypi/v/arrest.svg)](https://pypi.python.org/pypi/arrest)

- Documentation: https://s-bose.github.io/arrest/

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

Making it a breeze to interface with another HTTP service from your Python code.

## Installation

```bash
pip install arrest
```

## Getting Started

```python
import logging
from arrest import Resource, Service
from arrest.exceptions import ArrestHTTPException


xyz_service = Service(
    name="xyz",
    url="http://www.xyz-service.default.local.cluster:80",
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
