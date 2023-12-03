## Regarding Path Parameter idiosyncrasies
If you decide to specify your request parameters using kwargs, only two options are there.
- Using kwargs as path parameters
- Using kwargs as query parameters

You can specify path parameters in two ways, either by forming an f-string yourself or by providing them as keyword-arguments.
You can also specify query parameters as keyword-arguments if the request path string ends with `?`

The problem in this approach is that we have no way of knowing whether the path you supplied in the Arrest request is a complete path or a partial path to be filled by path parameters in kwargs.

Hence, if you decide to use kwargs, the following caveats need to be rememberred.
1. If you use kwargs as path parameters you can only specify path parameters in kwargs. Query parameters can be supplied as a pydantic model in the `request` argument.

2. If you use kwargs as query parameters, we assume that the path until `?` is a complete path. So we skip searching for a handler by constructing the path and find the handler whose route directly matches the requested path excluding `?`
