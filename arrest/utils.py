import typing
import types


def is_optional(field) -> bool:
    return typing.get_origin(field) in (typing.Union, types.UnionType) and type(
        None
    ) in typing.get_args(field)
