import typing
import types
import json
from pydantic import BaseModel
from pydantic.version import VERSION as PYDANTIC_VERSION


def is_optional(field) -> bool:
    return typing.get_origin(field) in (typing.Union, types.UnionType) and type(
        None
    ) in typing.get_args(field)


def join_url(*urls) -> str:
    return "/".join([url.strip("/") for url in urls])


def deserialize(model: BaseModel, field: str, default={}) -> dict:
    """
    reuse pydantic's own deserializer to extract single field
    as a json parsed dict
    """
    if PYDANTIC_VERSION.startswith("2."):
        value = model.model_dump_json(include={field})
    else:
        value = model.json(include={field})
    if not value:
        return default
    return json.loads(value)
