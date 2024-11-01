## Regarding Path Parameter idiosyncrasies
If you decide to specify your path parameters using kwargs, only two options are there.
- Using kwargs as path parameters
- Embedding path parameters as f-strings

The second option is less error-prone as the full URL path is being constructed, while the first option is preferable if you don't like working with f-strings.
It is an experimental feature which I thought would be beneficial but only time will tell how useful it really is.


## Pydantic V1 Issues
If you are using pydantic v1, it is highly recommended to switch to v2 which offers stricter type-safety, validation and faster parsing.
However, if you are still using it, here are a few caveats I observed that you might want to take into consideration:

1. In v1, `int` and `float` are implicitly coerced to `str`, whereas in v2 this raises a `ValidationError`, because v2 [by default disables type coercion](https://docs.pydantic.dev/latest/api/config/#pydantic.config.ConfigDict.coerce_numbers_to_str)
    from `int` and `float` to `str`. This might be a problem when you are using pydantic request models in v1. For example, consider the following:

    ```python
    from pydantic import BaseModel
    from arrest.params import Query

    class UserRequest(BaseModel):
        id: str

    await service.user.post("/profile", request=UserRequest(id=15)) # request body = {"id": "15"}
    ```

The above will throw a `ValidationError` in pydantic v2 unless you have `coerce_numbers_to_str=True` in `ConfigDict`

2. In pydantic v1, `parse_obj_as` helper function is used to convert objects of one type to another arbitrarty python type, as opposed to using `TypeAdapter` from Pydantic v2. The `parse_obj_as` function is inconsistent with the type conversions in comparison to `TypeAdapter`, because it does not throw a `ValidationError` if
an object of class B is attempted to be parsed as class A. For example, consider this:

    ```python
    from pydantic import BaseModel
    from arrest import Resource
    from .service import service

    class UserRequest(BaseModel):
        id: Optional[int] = None
        name: Optional[str] = None

    class FooBar(BaseModel):
        foo: str
        bar: str

    service.add_resource(
        Resource(
            name="user",
            path="/user",
            handlers=[
                ("POST", "/profile", UserRequest),
            ]
        )
    )
    await service.user.post("/profile", request=FooBar(foo="foo", bar="bar"))
    ```

The above will fail in v2 with ValidationError during attempting to parse the supplied request instance of `FooBar` as `UserRequest`.
But it will succeed and a request will be sent but the body will be an empty `UserRequest` instance, i.e. `{"id": None, "name": None}`.

**Note**: this can still raise ValidationError in v1, if, let's say, the `UserRequest` fields are all required, and non-overlapping with the fields in `FooBar`.
