# Arrest

Enable data validation for REST APIs.

Built on top of Pydantic and httpx.
Arrest is like a postman client for your microservice apis. It provides a simple layer of Pydantic encapsulation over Httpx HTTP calls to ensure structural integrity of your api definitions in a single file, as well as provide Pydantic's strength of data validation.

## TODOS

- add root resource "/"
- add logging support
- pretty print apispec + generate swagger docs
- config / setting option
- add database support

- add mocker for `httpx.AsyncClient.request()`
