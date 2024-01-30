Arrest additionally offers integration to [OpenAPI specification](https://swagger.io/specification/) (formerly Swagger).

With it, you can generate the necessary boilerplates for Arrest services and resources directly from the API route specifications.
Arrest uses [datamodel-code-generator](https://github.com/koxudaxi/datamodel-code-generator) under the hood to generate the data transfer models in Pydantic, and add Arrest resource and service templates on top of that.

## Usage

```bash
pip install "arrest[openapi]"

poetry add 'arrest[openapi]'
```

This installs two additional dependencies.
1. [datamodel-code-generator](https://github.com/koxudaxi/datamodel-code-generator)
2. [jinja2](https://github.com/pallets/jinja/)




!!! Note
    this feature is experimental and does not quite cover the extensive range of features of OpenAPI
    specification. We will be gradually rolling out new features from OpenAPI specification that also
    suits the functionalities of Arrest.
