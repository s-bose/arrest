import json
import posixpath
from urllib.parse import urljoin

from pydantic import BaseModel
from pydantic.version import VERSION as PYDANTIC_VERSION


def join_url(base_url: str, *urls) -> str:
    path = posixpath.join(*[url.lstrip("/") for url in urls])
    if not urls[-1].endswith("/"):
        path = path.rstrip("/")
    return urljoin(base_url, path)


def deserialize(model: BaseModel | None, field: str, default={}) -> dict:
    """
    reuse pydantic's own deserializer to extract single field
    as a json parsed dict
    """
    if PYDANTIC_VERSION.startswith("2."):
        value = model.model_dump_json(include={field})
    else:
        value = model.json(include={field})
    value = json.loads(value)
    if not value:
        return default
    return value


def process_header(
    model: BaseModel | None, field: str, header: dict | None = {}
) -> dict:
    header_dict = header | deserialize(model, field)

    return {k.replace("_", "-"): str(v) for k, v in header_dict.items()}


def process_body(
    model: BaseModel | None, field: str, body: dict | None = {}
) -> dict:
    return body | deserialize(model, field)


def process_query(
    model: BaseModel | None, field: str, query: dict | None = {}
) -> dict:
    return query | deserialize(model, field)
