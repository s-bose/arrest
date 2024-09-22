import dataclasses
import enum
import inspect
import logging
import posixpath
import re
from collections import deque
from functools import wraps
from types import GeneratorType
from typing import Any, Optional, TypeVar

import orjson
import tenacity
from pydantic import BaseModel

try:
    from pydantic import TypeAdapter
except ImportError:
    pass

from arrest._config import PYDANTIC_V2
from arrest.logging import logger
from arrest.types import ExceptionHandler, ExceptionHandlers

if not PYDANTIC_V2:  # pragma: no cover
    try:
        from pydantic import parse_obj_as
    except ImportError:
        pass

T = TypeVar("T")


def sanitize_name(name: str) -> str:
    name = name.lower().replace(" ", "_")
    return re.sub("[^A-Za-z0-9]+", "_", name)


def join_url(base_url: str, *urls: list[str]) -> str:
    path = posixpath.join(base_url, *[url.lstrip("/") for url in urls])
    if not urls[-1].endswith("/"):
        path = path.rstrip("/")
    return path


def extract_resource_and_suffix(path: str) -> tuple[str, str]:
    parts = path.lstrip("/").split("/")
    resource, suffix = parts[0], "/".join(parts[1:])
    if suffix:
        return resource, f"/{suffix}"
    if path.endswith("/"):
        return resource, suffix + "/"
    return resource, suffix


def extract_model_field(model: BaseModel, field: str) -> dict:
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


def validate_model(type_: T, obj: Any) -> T:  # pragma: no cover
    """generic type validator / parser for validating / parsing any python object
    to a given python type.

    Args:
        type_ (Any): A valid python type
        obj (Any): A valid python object

    Returns:
        T: type converted python object
    """
    if PYDANTIC_V2:
        type_adapter = TypeAdapter(type_)
        return type_adapter.validate_python(obj)

    return parse_obj_as(type_, obj)


def jsonable_encoder(obj: Any) -> Any:
    """a json-compatible encoder that works similar to fastapi's `jsonable_encoder`
    for the most part.

    See: https://github.com/tiangolo/fastapi/blob/master/fastapi/encoders.py#L102

    Following things are unsupported
    1. custom_encoders
    2. include & exclude fields
    3. sqlalchemy safe

    Args:
        obj (Any): python object to be json-serialized

    Returns:
        Any: json-serialized object
    """
    if isinstance(obj, BaseModel):
        if PYDANTIC_V2:
            obj_dict = obj.model_dump()
        else:
            obj_dict = obj.dict()

        if "__root__" in obj_dict:
            obj_dict = obj_dict["__root__"]

        return jsonable_encoder(obj_dict)

    if dataclasses.is_dataclass(obj):
        return jsonable_encoder(dataclasses.asdict(obj))

    if isinstance(obj, enum.Enum):
        return obj.value

    # if isinstance(obj, PurePath):
    #     return str(obj)

    if isinstance(obj, (str, int, float, type(None))):
        return obj

    if isinstance(obj, dict):
        encoded_dict = {}
        for key, val in obj.items():
            encoded_key = jsonable_encoder(key)
            encoded_value = jsonable_encoder(val)

            encoded_dict[encoded_key] = encoded_value
        return encoded_dict

    if isinstance(obj, (list, set, frozenset, GeneratorType, tuple, deque)):
        encoded_list = []
        for item in obj:
            encoded_list.append(jsonable_encoder(item))

        return encoded_list

    # fallback
    try:
        data = jsonify(obj)  # use orjson parser
    except Exception as e:
        errors: list[Exception] = []
        errors.append(e)
        try:
            data = vars(obj)  # try parsing __dict__
        except Exception as e:
            errors.append(e)
            raise ValueError(errors) from e

    return jsonable_encoder(data)


def retry(*, n_retries: int, exceptions: tuple[Exception]):
    def wrapper(func):
        @wraps(func)
        def sync_wrapped(*args, **kwargs):
            __retrying = tenacity.Retrying(
                stop=tenacity.stop_after_attempt(n_retries),
                wait=tenacity.wait_random_exponential(
                    multiplier=1, max=60
                ),  # Randomly wait up to 2^x * 1 seconds between each retry
                retry=(tenacity.retry_if_exception_type(exceptions)),
                before_sleep=tenacity.before_sleep_log(logger, logging.INFO),
                after=tenacity.after_log(logger, logging.INFO),
                reraise=True,
            )
            return __retrying(func, *args, **kwargs)

        @wraps(func)
        async def wrapped(*args, **kwargs):
            __retrying = tenacity.AsyncRetrying(
                stop=tenacity.stop_after_attempt(n_retries),
                wait=tenacity.wait_random_exponential(
                    multiplier=1, max=60
                ),  # Randomly wait up to 2^x * 1 seconds between each retry
                retry=(tenacity.retry_if_exception_type(exceptions)),
                before_sleep=tenacity.before_sleep_log(logger, logging.INFO),
                after=tenacity.after_log(logger, logging.INFO),
                reraise=True,
            )
            return await __retrying(func, *args, **kwargs)

        if inspect.iscoroutinefunction(func):
            return wrapped

        return sync_wrapped

    return wrapper


def lookup_exception_handler(
    exc_handlers: Optional[ExceptionHandlers], exc: Exception
) -> Optional[ExceptionHandler]:
    if not exc_handlers:
        return None

    for cls in type(exc).__mro__:
        if cls in exc_handlers:
            return exc_handlers[cls]
