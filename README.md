# Arrest

[![Tests](https://github.com/s-bose/arrest/actions/workflows/tests.yml/badge.svg)](https://github.com/s-bose/arrest/actions/workflows/tests.yml)

[![codecov](https://codecov.io/github/s-bose/arrest/graph/badge.svg?token=VBU3156QHP)](https://codecov.io/github/s-bose/arrest)

[![PyPi](https://img.shields.io/pypi/v/arrest.svg)](https://pypi.python.org/pypi/arrest)

- Documentation: https://s-bose.github.io/arrest/

Enable data validation for REST APIs.

Built on top of Pydantic and httpx.
Arrest is like a postman client for your microservice apis. It provides a simple layer of Pydantic encapsulation over Httpx HTTP calls to ensure structural integrity of your api definitions in a single file, as well as provide Pydantic's strength of data validation.

## Installation

```bash
pip install arrest
```

## Getting Started

```python

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
