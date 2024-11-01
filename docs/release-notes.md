## 0.1.10 (Latest)

### Added

- Added support for decorating custom handlers for your resource using `@my_resource.handler(/path/to/something)`.

- Added support for root-level resources. Now you can add a resource with a route of `""` or `"/"`. However, a service can only have only one root-level resource.

- Added a more flexible retry mechanism with better user control. You can now choose between the built-in retry mechanism, the retry from `HTTPTransport` class by `httpx`, or configure your own custom retry wrapper. Or you can opt to choose the default behaviour of no retries.

- Added support for any serializable python types as request and response types. This includes Pydantic basemodel and rootmodels, dataclasses, and python types which are json serializable.

- Added custom exception handlers. You can write your custom hooks on specific exceptions made by the HTTP calls and attach them to your service.

- Add support for writing query parameters into the url string. You can now write the query parameters as part of the url string, i.e. `service.user.get("/all?limit=10&role=admin")`.

- Add support for default GET handlers for resources. When defining arrest Resources, a default GET handler to the resource root is always added by default.

- Add named constants for HTTP Methods. You can simply use `from arrest import GET`, and create handlers using the named constant for method, `(GET, "/", UserRequest, UserResponse)`.

### Fixed

- Fixed the generated names of resource and services having whitespaces and special characters after parsing the OpenAPI Specification by standardizing the naming with using lower case and snake_case

- Fixed improper imports of pydantic schemas from the OpenAPI generation. Certain schema names in the generated OpenAPI spec caused some import issues, which was fixed.


For more information, check out [What's New](whats-new.md)

## 0.1.9

Feb 14, 2024

### Fixed

- Fixed pydantic dependency to support `>=1.10.13`

## 0.1.8

Jan 31, 2024

### Added

- Added optional OpenAPI Integration to automatically generate the Pydantic models, Arrest resources and services from the specification.

## 0.1.7

### <Yanked, not available>

## 0.1.6

### <Yanked, not available>

## 0.1.5

Jan 2, 2024

### Added

- Added support for most of the HTTPX client arguments as kwargs to be passed into both Service and Resource class. This includes things like cookies, auth, transport, cert etc. That way you can reuse a transport object in all your resources / services.
- Added backoff retries for all the http calls with configurable no. of retries.
- Added support for providing your own `httpx.AsyncClient` instance as a field in both `Service` and `Resource` class. This can also be any other class that subclasses `httpx.AsyncClient` (for example, the Oauth2 client from authlib).
- Added a new decorator `.handler(...)` for a resource to decorate a custom user-defined function for a resource sub-path. This enables more fine-grained control over the http calls and also injects the a reference to the resource instance inside the function for easier access.


### Misc

- General bug fixes
- Documentation changes


## 0.1.4

Dec 15, 2023

### Fixed

- Fix [#11](https://github.com/s-bose/arrest/issues/11) - url paths are now constructed using posixpath. Assuming all the components of the path are put in a hierarchical manner (service -> resource -> handler)

## 0.1.3

Dec 10, 2023

### Added

- Added backwards compatibility with pydantic@1.10.13 and above

### Misc

- General code and documentation refactor

## 0.1.2

Dec 8, 2023

### Fixed

- Fixed issue with paths ending / not-ending with trailing slashes
- Fixed root handlers not getting matched
- Refactored test suite

### Added

- Added header and query kwargs for request

### Misc

- General refactors

## 0.1.1

Dec 2, 2023

### Minor release


## 0.1.0

Dec 2, 2023

### Initial release - minor
