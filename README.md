# Arrest

[![Tests](https://github.com/s-bose/arrest/actions/workflows/tests.yml/badge.svg)](https://github.com/s-bose/arrest/actions/workflows/tests.yml)

[![Coverage](https://codecov.io/github/s-bose/arrest/graph/badge.svg?token=VBU3156QHP)](https://codecov.io/github/s-bose/arrest)

[![PyPi](https://img.shields.io/pypi/v/arrest.svg)](https://pypi.python.org/pypi/arrest)

Enable data validation for REST APIs.

Built on top of Pydantic and httpx.
Arrest is like a postman client for your microservice apis. It provides a simple layer of Pydantic encapsulation over Httpx HTTP calls to ensure structural integrity of your api definitions in a single file, as well as provide Pydantic's strength of data validation.

## TODOS

- add logging support
- pretty print apispec + generate swagger docs
- config / setting option
- add database support
