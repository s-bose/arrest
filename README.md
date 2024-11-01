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

Here is an example of a typical client-side functions for interacting with an HTTP Service.
![](./docs/assets/screenshot_httpx.png)

And here is the same functionality achieved using Arrest.
![](./docs/assets/screenshot_arrest.png)


## Contents

1. [Installation](#installation)
2. [Getting Started](#getting-started)
3. [Contributing](#contributing)

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

##


## Contributing

Please see the [CONTRIBUTING.md](CONTRIBUTING.md) for more information.
