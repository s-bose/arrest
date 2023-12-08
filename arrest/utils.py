import posixpath
from typing import Any, Type
from urllib.parse import urljoin

import orjson
from pydantic import BaseModel
from pydantic.version import VERSION as PYDANTIC_VERSION


def join_url(base_url: str, *urls: list[str]) -> str:
    path = posixpath.join(*[url.lstrip("/") for url in urls])
    if not urls[-1].endswith("/"):
        path = path.rstrip("/")
    return urljoin(base_url, path)


def extract_model_field(model: BaseModel, field: str) -> dict:
    """
    reuse pydantic's own deserializer to extract single field
    as a json parsed dict
    """
    default = {}

    if PYDANTIC_VERSION.startswith("2."):
        value = model.model_dump_json(include={field}, by_alias=True)
    else:
        value = model.json(include={field})
    value = orjson.loads(value)
    if not value:
        return default
    return value


def jsonify(obj: Any) -> Any:
    return orjson.loads(orjson.dumps(obj))


def validate_request_model(type_: Type[BaseModel], obj: Any) -> BaseModel:
    if PYDANTIC_VERSION.startswith("2."):
        return type_.model_validate(obj)
    return type_.parse_obj(obj)
