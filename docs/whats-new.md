- Feat: Added support for decorating custom handlers for your resource.

    Earlier in v0.1.9 the decorator could only be used with a resource under its parent service's scope:

    ```python
    @myservice.user.handler("/path")
    async def path_handler(self, url, *args, **kwargs):
        ...
    ```

    This was not a clear separation of concern. Ideally in Arrest, we want you to be able to define everything relating to a resource within the resource, and everything relating to a service within the service, and simply interface the resources with your service, or multiple services.
    In v0.1.10, you can use the handler with your resource, without having to connect it to a service first and use the service's scope:

    ```python
    # resource.py
    from arrest import Resource

    user = Resource(
        route="/user",
        handlers=[...]
    )

    @user.handler("/upload-pic")
    async def upload_user_profile_pic(self, url, *arg, *kwarg):
        ...

    ...

    # service.py
    from .resource import user

    myservice = Service(
        name="myservice",
        url="http://example.com",
        resources=[user]
    )

    ...

    # somewhere_else.py
    from .service import myservice

    await myservice.user.upload_user_profile_pic(...)
    ```

    !!! Note
        Connecting your resource to a service is still mandatory if you want to use the complete url. If you just call the method from your resource instance directly, since its still not bound to a service (thus a `base_url`), it would try to make an api call to `/user/upload-pic`, instead of `http://example.com/user/upload-pic`


- Fix: Standardized the names of resource and services from parsing the OpenAPI Specification.

    Certain names for resources and services had whitespaces and special characters, which resulted in the generated code having illegal variable names (such as `OpenAPI service: 2.1 = Service(...)`)

    v0.1.10 standardizes all variable names of the generated service and resource to lower and snake_cased.

- Feat: Add support for root-level resources.

    You can now define root-level resources (i.e., having base routes of either `""` or `"/"`)

- Feat: Add support for passing any Python-type* to the request and response type definitions for handlers.

- TODO - do we need the resource-level `response_model=` definition?
