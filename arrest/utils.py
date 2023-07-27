import typing
import types


def is_optional(field) -> bool:
    return typing.get_origin(field) in (typing.Union, types.UnionType) and type(
        None
    ) in typing.get_args(field)


def join_url(*urls) -> str:
    return "/".join([url.strip("/") for url in urls])
