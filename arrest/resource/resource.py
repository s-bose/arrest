import re
from urllib.parse import urljoin, urlsplit

from typing import Optional, Pattern, Type, get_args, MutableMapping, Mapping
from functools import partial
from pydantic import BaseModel, ValidationError

from arrest.http import Methods
from arrest.exceptions import MethodNotAllowed

# Match parameters in URL paths, eg. '{param}', and '{param:int}'
PARAM_REGEX = re.compile("{([a-zA-Z_][a-zA-Z0-9_]*)(:[a-zA-Z_][a-zA-Z0-9_]*)?}")

CONVERTER_REGEX: Mapping[str, str] = {
    "str": "[^/]+",
    "int": "[0-9]+",
    "float": r"[0-9]+(\.[0-9]+)?",
}


class ResourceHandler(BaseModel):
    method: Methods
    route: str
    request: Optional[Type[BaseModel]]
    response: Optional[Type[BaseModel]]
    kwargs: Optional[dict]

    # @model_validator(mode="after")
    # def validate_params(self):
    #     route = self.route
    #     request = self.request
    #     for match in PARAM_REGEX.finditer(route):
    #         path_param, param_type = match.groups("str")

    #         path_param = request.model_fields.get(path_param)
    #         print(get_args(path_param.annotation)[0])


class Resource:
    _handlers: MutableMapping[str, ResourceHandler]

    def __init__(
        self, name: str, route: str, response_model: Optional[Type[BaseModel]] = None
    ) -> None:
        self.base_url = None  # will be filled once bound to a service
        self.name = name
        self.route = route
        self.response_model = response_model
        self._handlers = {}

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
        self.__bind_handler_route(
            ResourceHandler(
                method=method,
                route=route,
                request=request,
                response=response,
                kwargs=kwargs,
            )
        )

    def add_handlers(self, handlers: list[ResourceHandler] | list[Mapping[str, dict]]):
        """
        bulk insert multiple handlers either by a list of handler objs,
        or a list of dict structs
        """
        for handler in handlers:
            if isinstance(handler, ResourceHandler):
                self.__bind_handler_route(handler)
            else:
                self.__bind_handler_route(ResourceHandler(**handler))

    def __bind_handler_route(self, handler: ResourceHandler) -> None:
        """
        compose a fully-qualified url by joining base service url, resource url
        and handler url,
        and map that to the handler object.
        Note: If there are duplicate handlers or any combination resulting in
        duplicate fq-url, the later will take precendence.
        """
        assert (
            self.base_url
        ), "missing base url, perhaps resource not bound to any service"

        resource_route, handler_route = (
            urlsplit(self.route).path,
            urlsplit(handler.route).path,
        )
        fq_url = urljoin(self.base_url, resource_route, handler_route)
        self._handlers[fq_url] = handler

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

    def compile_path(self, path: str) -> Pattern[str]:
        """
        Given a path string, like: "/{username:str}",
        returns a capturing group: "/(?P<username>[^/]+)"

        inspired from: https://github.com/encode/starlette/blob/master/starlette/routing.py::compile_path()
        """
        path_regex = "^"
        idx = 0
        parsed_path_params = set()

        for match in PARAM_REGEX.finditer(path):
            param_name, converter_type = match.groups("str")
            converter_type = converter_type.lstrip(":")

            assert (
                converter_type in CONVERTER_REGEX
            ), f"Invalid converter specified, available converters {CONVERTER_REGEX.keys()}"

            converter_regex = CONVERTER_REGEX[converter_type]
            path_regex += re.escape(path[idx : match.start()])
            path_regex += f"(?P<{param_name}>{converter_regex})"
            if param_name in parsed_path_params:
                raise ValueError(f"Duplicate param name {param_name} at path {path}")
            parsed_path_params.add(param_name)

            idx = match.end()

        path_regex += re.escape(path[idx:]) + "$"
        return re.compile(path_regex)
