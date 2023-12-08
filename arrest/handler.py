import difflib
import re
from typing import Callable, NamedTuple, Pattern, Type

from pydantic import AnyUrl, BaseModel

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
        request (Type[BaseModel], optional):
            Pydantic type to validate the request with
        response (Type[BaseModel], optional):
            Pydantic type to deserialize the HTTP response
        callback (Callable, optional):
            A callable (sync or async) to execute with the HTTP
            response
    """

    method: Methods
    route: str
    request: Type[BaseModel] | None = None
    response: Type[BaseModel] | None = None
    callback: Callable | None = None
    path_format: str | None = None
    path_regex: Pattern | None = None
    param_types: dict[str, type] | None = None

    def parse_path(self, method: Methods, path: str | AnyUrl, **kwargs) -> str | AnyUrl | None:
        if method != self.method:
            return None

        if kwargs:
            return self.__resolve_path_param(path, **kwargs)

        return self.__parse_exact_path(path)

    def __parse_exact_path(self, path: str | AnyUrl) -> str | AnyUrl | None:
        if self.path_regex.fullmatch(path):
            return path

    def __resolve_path_param(self, path: str | AnyUrl, **kwargs) -> str | AnyUrl | None:
        params = self.__extract_path_params(path)
        if params is None:
            return None

        params |= kwargs

        try:
            parsed_path, remaining_params = replace_params(
                path=self.path_format,
                path_params=params,
                param_types=self.param_types,
            )
        except ConversionError as exc:
            logger.warning(str(exc), exc_info=True)
            return None
        if remaining_params:
            return None

        return self.__parse_exact_path(parsed_path)

    def __extract_path_params(self, path: str | AnyUrl) -> dict | None:
        differ = difflib.Differ()
        diff = list(differ.compare(self.path_format.split("/"), path.split("/")))

        left = [delta.lstrip("- ") for delta in diff if delta.startswith("- ")]
        right = [delta.lstrip("+ ") for delta in diff if delta.startswith("+ ")]

        params = dict(zip(left, right))
        for key in list(params):
            if not (match := re.match("{(.*)}", key)):
                return None

            params[match.group(1)] = params.pop(key)

        return {k: v for k, v in params.items() if v}
