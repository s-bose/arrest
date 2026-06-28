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
from httpx import Headers, QueryParams
from httpx._types import FileTypes
from pydantic import BaseModel, TypeAdapter

from arrest.logging import logger
from arrest.params import ParamTypes, RequestArgs, _File, _Param
from arrest.types import ExceptionHandler, ExceptionHandlers, UploadFile

T = TypeVar("T")


def sanitize_name(name: str) -> str:
    name = name.lower().replace(" ", "_")
    return re.sub("[^A-Za-z0-9]+", "_", name)


def join_url(base_url: str, *urls: str) -> str:
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


def extract_model_field(model: BaseModel, field: str) -> dict[Any, Any]:
    """
    reuse pydantic's own deserializer to extract single field
    as a json parsed dict
    """
    default: dict[Any, Any] = {}

    value = model.model_dump_json(include={field}, by_alias=True)
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
    type_adapter = TypeAdapter(type_)
    return type_adapter.validate_python(obj)


def is_rootmodel(obj: Any):
    """checks whether a pydantic object is a rootmodel instance"""
    return hasattr(obj, "root")


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
        obj_dict = obj.model_dump()
        return jsonable_encoder(obj_dict)

    if dataclasses.is_dataclass(obj):
        return jsonable_encoder(dataclasses.asdict(obj))  # type: ignore[arg-type]

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


def retry(*, n_retries: int, exceptions: tuple[type[Exception], ...]):
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


def extract_file_params(model: BaseModel, field: str):
    """
    Extracts file parameters from a Pydantic model field.

    Args:
        model (BaseModel): The Pydantic model instance.
        field (str): The name of the field to extract.

    Returns:
        dict: A dictionary containing the extracted file parameters.
    """
    default: dict[str, FileTypes] = {}

    field_info = model.__class__.model_fields.get(field, None)
    if not isinstance(field_info, _File):
        raise ValueError(f"Field '{field}' is not a file field")

    data = getattr(model, field, None)

    if isinstance(data, bytes):
        default[field] = data

    elif isinstance(data, UploadFile):
        if data.file is None:
            raise ValueError(f"UploadFile for field '{field}' has no file provided")

        default[field] = (data.filename, data.file, data.content_type)

    elif isinstance(data, str):
        default[field] = data.encode()

    return default


def lookup_exception_handler(
    exc_handlers: ExceptionHandlers, exc: Exception
) -> Optional[ExceptionHandler]:
    if not exc_handlers:
        return None

    for cls in type(exc).__mro__:
        if cls in exc_handlers:
            return exc_handlers[cls]


def extract_request_params(
    request_type: Any,
    request_data: Any,
    headers: dict[str, str] | None = None,
    query: dict[str, Any] | None = None,
) -> RequestArgs:
    header_params: dict[str, str] = headers or {}
    query_params: dict[str, Any] = query or {}
    body_params: dict[str, Any] = {}
    file_params: dict[str, FileTypes] = {}

    if request_type:
        # perform type validation on `request_data`
        request_data = validate_model(type_=request_type, obj=request_data)

    if is_rootmodel(request_data):
        return RequestArgs(
            header=Headers(header_params),
            query=QueryParams(query_params),
            body=jsonable_encoder(request_data),
            content_type="application/json",
        )

    if isinstance(request_data, BaseModel):
        model_fields = request_data.__class__.model_fields
        is_json_body = False
        is_form_body = False

        for field_name, field_info in model_fields.items():
            if not isinstance(field_info, _Param):
                body_params |= extract_model_field(request_data, field_name)
                is_json_body = True
            else:
                match field_info._param_type:
                    case ParamTypes.query:
                        query_params |= extract_model_field(request_data, field_name)
                    case ParamTypes.header:
                        header_params |= extract_model_field(request_data, field_name)
                    case ParamTypes.body:
                        body_params |= extract_model_field(request_data, field_name)
                        is_json_body = True
                    case ParamTypes.form:
                        is_form_body = True
                        body_params |= extract_model_field(request_data, field_name)
                    case ParamTypes.file:
                        is_form_body = True
                        file_params |= extract_file_params(request_data, field_name)

        if is_json_body and is_form_body:
            raise ValueError(
                "Cannot mix JSON body fields (annotated with Body() or unannotated)"
                " with form fields (annotated with Form() or File()) in the same request model"
            )

        if is_form_body:
            if file_params:
                return RequestArgs(
                    header=Headers(header_params),
                    query=QueryParams(query_params),
                    body=body_params if body_params else None,
                    files=file_params if file_params else None,
                    content_type="multipart/form-data",
                )
            return RequestArgs(
                header=Headers(header_params),
                query=QueryParams(query_params),
                body=body_params if body_params else None,
                files=file_params if file_params else None,
                content_type="application/x-www-form-urlencoded",
            )

        return RequestArgs(
            header=Headers(header_params),
            query=QueryParams(query_params),
            body=jsonable_encoder(body_params) if body_params else None,
            files=file_params if file_params else None,
            content_type="application/json" if body_params else None,
        )

    body_params = request_data

    return RequestArgs(
        header=Headers(header_params),
        query=QueryParams(query_params),
        body=jsonable_encoder(body_params) if body_params else None,
        files=file_params if file_params else None,
        content_type="application/json" if body_params else None,
    )


def build_body_kwargs(
    body: Any,
    files: Any,
    content_type: str | None,
) -> dict[str, Any]:
    """Map a content-type signal to the appropriate httpx body kwargs."""
    if not body and not files:
        return {}
    if content_type == "multipart/form-data":
        return {"data": body, "files": files}
    if content_type == "application/x-www-form-urlencoded":
        return {"data": body}
    return {"json": body} if body else {}
