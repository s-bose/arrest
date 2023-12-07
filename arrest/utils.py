import posixpath
from urllib.parse import urljoin

import orjson
from pydantic import BaseModel
from pydantic.version import VERSION as PYDANTIC_VERSION


def join_url(base_url: str, *urls) -> str:
    path = posixpath.join(*[url.lstrip("/") for url in urls])
    if not urls[-1].endswith("/"):
        path = path.rstrip("/")
    return urljoin(base_url, path)


def extract_model_field(model: BaseModel | None, field: str) -> dict:
    """
    reuse pydantic's own deserializer to extract single field
    as a json parsed dict
    """
    default = {}

    if not model:
        return default

    if PYDANTIC_VERSION.startswith("2."):
        value = model.model_dump_json(include={field})
    else:
        value = model.json(include={field})
    value = orjson.loads(value)
    if not value:
        return default
    return value


# def jsonify(obj: Any) -> dict | list:
#     try:
#         return orjson.dumps()
