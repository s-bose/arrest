# API Documentation

## `Service`
::: arrest.service.Service
    options:
        show_source: false
        members:
            - __init__
            - add_resource
            - request

## `Resource`
::: arrest.resource.Resource
    options:
        show_source: false
        members:
            - __init__
            - request
            - get
            - post
            - put
            - patch
            - delete
            - head
            - options

## `ResourceHandler`

::: arrest.handler.ResourceHandler

## Exceptions

### ArrestError
::: arrest.exceptions.ArrestError
base class for all Exception. Used in situations that are not one of the following

### ArrestHTTPException
::: arrest.exceptions.ArrestHTTPException
used for exceptions during HTTP calls

* `.status_code` - **str** status code of the exception, 500 for internal server error
* `.data` - **str** json response for the exception

### NotFoundException
::: arrest.exceptions.NotFoundException
base class for all NotFound-type exceptions

### HandlerNotFound
::: arrest.exceptions.HandlerNotFound
raised when no matching handler is found for the requested path

* `.message` - **str**

### ResourceNotFound
::: arrest.exceptions.ResourceNotFound
raised when no matching resource is found for the service

* `.message` - **str**


### ConversionError
::: arrest.exceptions.ConversionError
raised when Arrest cannot convert path-parameter type using any of the existing converters
