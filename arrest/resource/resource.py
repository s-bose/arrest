# pylint: disable=W0707


import re
import typing
from urllib.parse import urljoin, urlsplit
import httpx
import inspect

from typing import Optional, Pattern, Type, Callable, MutableMapping, Mapping, Any
from functools import partial
from pydantic import BaseModel
from pydantic.fields import FieldInfo

from arrest.http import Methods
from arrest.exceptions import ArrestHTTPException
from arrest import params
from arrest.utils import is_optional

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
    request: Optional[Any] = None
    response: Optional[Any] = None
    kwargs: Optional[dict] = {}
    callback: Optional[Callable] = None


class Resource:
    _handlers: MutableMapping[str, ResourceHandler]

    def __init__(
        self,
        name: str,
        route: str,
        response_model: Optional[Type[BaseModel]] = None,
        handlers: list[ResourceHandler] | list[Mapping[str, dict]] = None,
    ) -> None:
        self.base_url = "/"  # will be filled once bound to a service
        self.name = name
        self.route = route[1:] if route.startswith("/") else route
        self.response_model = response_model
        self.handlers = []
        self._handler_mapping: Mapping[Pattern, ResourceHandler] = {}

        if handlers:
            self.handlers = handlers

        self.get = partial(self.request, method=Methods.GET)
        self.post = partial(self.request, method=Methods.POST)
        self.put = partial(self.request, method=Methods.PUT)
        self.patch = partial(self.request, method=Methods.PATCH)
        self.delete = partial(self.request, method=Methods.DELETE)

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
        ), "missing base url, perhaps resource not bound to any service?"

        resource_route, handler_route = (
            urlsplit(self.route).path,
            urlsplit(handler.route).path,
        )
        if len(handler_route) > 1:
            handler_route = (
                handler_route[1:] if handler_route.startswith("/") else handler_route
            )

        fq_url = urljoin(
            urljoin(self.base_url, resource_route), handler_route
        )  # TODO - use plain posixpath.join()
        fq_url_regex = self.compile_path(fq_url)
        self._handler_mapping[fq_url_regex] = handler

    async def request(
        self,
        url: str,
        method: Methods,
        **kwargs,
    ) -> BaseModel | list[BaseModel] | dict | None:
        request: BaseModel | None = kwargs.get("request", None)

        if len(url) > 1:
            url = url[1:] if url.startswith("/") else url
        fq_url = urljoin(urljoin(self.base_url, self.route), url)

        headers, query_params, body_params = {}, {}, {}

        for route, handler in self._handler_mapping.items():
            if re.fullmatch(route, fq_url) is not None:
                request_type = handler.request
                if request_type and not is_optional(request_type):
                    if not request:
                        raise ValueError(
                            f"request of type {request_type.__name__} is required"
                        )
                    if not isinstance(request, request_type):
                        raise ValueError(
                            f"handler for {fq_url} expects request class {request_type.__name__}, found {type(request)}"
                        )

                    for field, field_info in request.model_fields:
                        if isinstance(field_info, params.Query):
                            query_params[field] = getattr(request, field, None)
                        elif isinstance(field_info, params.Header):
                            headers[field] = getattr(request, field, None)
                        elif isinstance(field_info, params.Body, FieldInfo):
                            body_params[field] = getattr(
                                request, field, None
                            )  # TODO - serialize datetime objs in case
                        else:
                            raise ValueError(
                                f"Invalid field class specified: {field_info}"
                            )

                headers[
                    "Content-Type"
                ] = "application/json"  # TODO -temporary, remove once we support other request formats

                response_type = handler.response or self.response_model
                try:
                    async with httpx.AsyncClient() as client:
                        match method:
                            case Methods.GET:
                                response = await client.get(
                                    url=fq_url, headers=headers, params=query_params
                                )
                            case Methods.POST:
                                response = await client.post(
                                    url=fq_url,
                                    headers=headers,
                                    params=query_params,
                                    data=body_params,
                                )
                            case Methods.PUT:
                                response = await client.put(
                                    url=fq_url,
                                    headers=headers,
                                    params=query_params,
                                    data=body_params,
                                )
                            case Methods.PATCH:
                                response = await client.patch(
                                    url=fq_url,
                                    headers=headers,
                                    params=query_params,
                                    data=body_params,
                                )
                            case Methods.DELETE:
                                response = await client.delete(
                                    url=fq_url,
                                    headers=headers,
                                    params=query_params,
                                    data=body_params,
                                )

                        response.raise_for_status()
                        response_body = response.json()

                        if handler.callback:
                            if inspect.iscoroutinefunction(handler.callback):
                                return await handler.callback(response_body)
                            return handler.callback(response_body)

                        parsed_response = response_body

                        if response_type:
                            parsed_response: list[
                                response_type
                            ] | response_type | dict = None
                            if isinstance(response_body, list):
                                parsed_response = [
                                    response_type(**item) for item in response_body
                                ]

                            else:
                                parsed_response = response_type(**response_body)

                        return parsed_response

                except httpx.HTTPStatusError as exc:
                    err_response_body = response.json()
                    raise ArrestHTTPException(
                        status_code=exc.response.status_code, data=err_response_body
                    )

                except httpx.TimeoutException:
                    raise ArrestHTTPException(
                        status_code=httpx.codes.INTERNAL_SERVER_ERROR,
                        data="request timed out",
                    )

                except httpx.RequestError:
                    raise ArrestHTTPException(
                        status_code=httpx.codes.INTERNAL_SERVER_ERROR,
                        data="error occured while making request",
                    )

    def compile_path(self, path: str) -> Pattern[str]:
        """
        Given a path string, like: "/{username:str}",
        returns a capturing group: "/(?P<username>[^/]+)"

        inspired by:
        https://github.com/encode/starlette/blob/master/starlette/routing.py::compile_path()
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
