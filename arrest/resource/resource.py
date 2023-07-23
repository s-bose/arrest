import re

from typing import Optional, List, Type, get_args
from functools import partial
from pydantic import BaseModel, model_validator

from arrest.http import Methods
from arrest.exceptions import MethodNotAllowed

# Match parameters in URL paths, eg. '{param}', and '{param:int}'
PARAM_REGEX = re.compile("{([a-zA-Z_][a-zA-Z0-9_]*)(:[a-zA-Z_][a-zA-Z0-9_]*)?}")


class ResourceHandler(BaseModel):
    method: Methods
    route: str
    request: Optional[Type[BaseModel]]
    response: Optional[Type[BaseModel]]
    kwargs: Optional[dict]

    @model_validator(mode="after")
    def validate_params(self):
        route = self.route
        request = self.request
        for match in PARAM_REGEX.finditer(route):
            path_param, param_type = match.groups("str")
            if not path_param in request.model_fields:
                raise ValueError(
                    f"{path_param} defined in route but not present in request model"
                )

            path_param = request.model_fields.get(path_param)
            print(get_args(path_param.annotation)[0])


class Resource:
    _handlers: List[ResourceHandler]

    def __init__(
        self, name: str, route: str, response_model: Optional[Type[BaseModel]] = None
    ) -> None:
        self.base_url = None
        self.name = name
        self.route = route
        self.response_model = response_model
        self._handlers = []

        self.get = partial(self._make_request_async, method=Methods.GET)
        self.post = partial(self._make_request_async, method=Methods.POST)
        self.put = partial(self._make_request_async, method=Methods.PUT)
        self.patch = partial(self._make_request_async, method=Methods.PATCH)
        self.delete = partial(self._make_request_async, method=Methods.DELETE)

    def add_handler(
        self,
        method: Methods,
        route: str,
        *,
        request: Optional[Type[BaseModel]] = None,
        response: Optional[Type[BaseModel]] = None,
        **kwargs,
    ):
        self._handlers.append(
            ResourceHandler(
                method=method,
                route=route,
                request=request,
                response=response,
                kwargs=kwargs,
            )
        )

    async def _make_request_async(
        self,
        method: Methods,
        url: str,
        **kwargs,
    ):
        for handler in self._handlers:
            if handler.route == url:
                if method != handler.method:
                    raise MethodNotAllowed
