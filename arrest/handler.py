from typing import Callable, NamedTuple, Pattern, Type

from pydantic import BaseModel

from arrest.http import Methods


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
    url: str | None = None
    url_regex: Pattern | None = None
    path_params: dict[str, type] | None = None

    def extract_params(self, path: str) -> dict:
        match = self.url_regex.search(path)
        if match:
            return match.groupdict()
