import posixpath
from typing import Any, Type

import orjson
from pydantic import BaseModel, TypeAdapter

from arrest._config import PYDANTIC_V2


if not PYDANTIC_V2:  # pragma: no cover
    try:
        from pydantic import parse_obj_as
    except ImportError:
        pass


def join_url(base_url: str, *urls: list[str]) -> str:
    path = posixpath.join(base_url, *[url.lstrip("/") for url in urls])
    if not urls[-1].endswith("/"):
        path = path.rstrip("/")
    return path


def extract_model_field(model: BaseModel, field: str) -> dict:  # pragma: no cover
    """
    reuse pydantic's own deserializer to extract single field
    as a json parsed dict
    """
    default = {}

    if PYDANTIC_V2:
        value = model.model_dump_json(include={field}, by_alias=True)
    else:
        value = model.json(include={field}, by_alias=True)
    value = orjson.loads(value)
    if not value:
        return default
    return value


def jsonify(obj: Any) -> Any:
    return orjson.loads(orjson.dumps(obj))


def validate_model(type_: Type[BaseModel], obj: Any) -> BaseModel:  # pragma: no cover
    if PYDANTIC_V2:
        type_adapter = TypeAdapter(type_)
        return type_adapter.validate_python(obj)

    return parse_obj_as(type_, obj)
