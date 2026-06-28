import difflib
import re
from typing import Any, Callable, NamedTuple, Pattern, overload

from pydantic import BaseModel, ConfigDict, PrivateAttr

from arrest.converters import replace_params
from arrest.exceptions import ConversionError
from arrest.http import Methods
from arrest.logging import logger


class HandlerKey(NamedTuple):
    method: Methods
    route: str


class ResourceHandler(BaseModel):
    """
    A pydantic class defining a resource handler

    Parameters:
        method (Methods):
            HTTP Method for the handler
        route (str):
            Unique path to the handler from its parent resource
        request (T, optional):
            Python type to validate the request with
        response (T, optional):
            Python type to deserialize the HTTP response
        callback (Callable, optional):
            A callable (sync or async) to execute with the HTTP
            response
        headers (dict, optional):
            default Headers for the handlers, can be overridden
            by runtime headers
    """

    model_config = ConfigDict(extra="forbid")

    method: Methods
    route: str
    request: Any | None = None
    response: Any | None = None
    callback: Callable | None = None
    headers: dict[str, str] | None = None

    _path_format: str | None = PrivateAttr(default=None)
    _path_regex: Pattern | None = PrivateAttr(default=None)
    _param_types: Any = PrivateAttr(default=None)

    def parse_path(self, method: Methods, path: str, **kwargs) -> str | None:
        if method != self.method:
            return None

        if kwargs:
            return self.__resolve_path_param(path, **kwargs)

        return self.__parse_exact_path(path)

    def __parse_exact_path(self, path: str) -> str | None:
        if not self._path_regex:
            return None
        if self._path_regex.fullmatch(path):
            return path

    def __resolve_path_param(self, path: str, **kwargs) -> str | None:
        params = self.__extract_path_params(path)
        if params is None:
            return None

        if not self._path_format or not self._param_types:
            return None
        params |= kwargs

        try:
            parsed_path, remaining_params = replace_params(
                path=self._path_format,
                path_params=params,
                param_types=self._param_types,
            )
        except ConversionError as exc:
            logger.warning(str(exc), exc_info=True)
            return None
        if remaining_params:
            return None

        return self.__parse_exact_path(parsed_path)

    def __extract_path_params(self, path: str) -> dict | None:
        if not self._path_format:
            return None
        differ = difflib.Differ()
        diff = list(differ.compare(self._path_format.split("/"), path.split("/")))

        left = [delta.lstrip("- ") for delta in diff if delta.startswith("- ")]
        right = [delta.lstrip("+ ") for delta in diff if delta.startswith("+ ")]

        params = dict(zip(left, right))
        for key in list(params):
            if not (match := re.match("{(.*)}", key)):
                return None

            params[match.group(1)] = params.pop(key)

        return {k: v for k, v in params.items() if v}


@overload
def H(
    method: Methods, route: str, *, headers: dict[str, str] | None = None
) -> ResourceHandler: ...
@overload
def H(
    method: Methods, route: str, request: Any, *, headers: dict[str, str] | None = None
) -> ResourceHandler: ...
@overload
def H(
    method: Methods,
    route: str,
    request: Any,
    response: Any,
    *,
    headers: dict[str, str] | None = None,
) -> ResourceHandler: ...
@overload
def H(
    method: Methods,
    route: str,
    request: Any,
    response: Any,
    callback: Callable[..., Any],
    *,
    headers: dict[str, str] | None = None,
) -> ResourceHandler: ...


def H(
    method: Methods,
    route: str,
    request: Any = None,
    response: Any = None,
    callback: Callable[..., Any] | None = None,
    *,
    headers: dict[str, str] | None = None,
) -> ResourceHandler:
    return ResourceHandler(
        method=method,
        route=route,
        request=request,
        response=response,
        callback=callback,
        headers=headers,
    )
