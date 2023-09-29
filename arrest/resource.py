# pylint: disable=W0707
import typing
from typing import Optional, Pattern, Type, Callable, Mapping, Any
import inspect
from functools import partial
import re
import json
import httpx
from pydantic import BaseModel, ValidationError
from pydantic.fields import FieldInfo
from pydantic.version import VERSION as PYDANTIC_VERSION

from arrest.http import Methods
from arrest.exceptions import ArrestHTTPException
from arrest import params
from arrest.params import ParamTypes
from arrest.utils import is_optional, join_url, deserialize
from arrest.defaults import HEADER_DEFAULTS, TIMEOUT_DEFAULT

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
    callback: Optional[Callable] = None
    url: Optional[str] = None
    url_regex: Optional[Pattern] = None


class Resource:
    def __init__(
        self,
        name: Optional[str] = None,
        *,
        route: str,
        headers: Optional[dict] = HEADER_DEFAULTS,
        response_model: Optional[Type[BaseModel]] = None,
        handlers: list[ResourceHandler]
        | list[Mapping[str, Any]]
        | list[tuple[Any, ...]] = [],
    ) -> None:
        self.base_url = "/"  # will be filled once bound to a service
        self.route = route
        derived_name = name if name else self.route.strip("/").split("/")[0]
        self.name = derived_name if derived_name else "root"
        self.response_model = response_model
        self.headers = headers
        self.routes: dict[tuple[Methods, str], ResourceHandler] = {}

        for _handler in handlers:
            try:
                if isinstance(_handler, dict):
                    self._bind_handler(handler=ResourceHandler(**_handler))
                elif isinstance(_handler, tuple):
                    if len(_handler) < 2:
                        raise ValueError(
                            "Too few arguments to unpack. Expected atleast 2"
                        )
                    if len(_handler) > 5:
                        raise ValueError(
                            f"Too many arguments to unpack. Expected 5, got {len(_handler)}"
                        )

                    method, route, rest = (
                        _handler[0],
                        _handler[1],
                        _handler[2:],
                    )

                    self._bind_handler(
                        handler=ResourceHandler(
                            method=method,
                            route=route,
                            request=len(rest) >= 1 and rest[0] or None,
                            response=len(rest) >= 2 and rest[1] or None,
                            callback=len(rest) >= 3 and rest[2] or None,
                        )
                    )
                else:
                    self._bind_handler(handler=_handler)
            except ValidationError:
                raise ValueError("cannot initialize handler signature")

        self.get = partial(self.request, method=Methods.GET)
        self.post = partial(self.request, method=Methods.POST)
        self.put = partial(self.request, method=Methods.PUT)
        self.patch = partial(self.request, method=Methods.PATCH)
        self.delete = partial(self.request, method=Methods.DELETE)

    def initialize_handlers(self, base_url: Optional[str] = None) -> None:
        """
        specifically used to inject `base_url` from a Service class to
        downstream Resources.
        Should not be used separately (unless you want to break things)
        """
        handlers = self.routes.values()

        for handler in handlers:
            self._bind_handler(base_url=base_url, handler=handler)

    def _bind_handler(
        self, base_url: Optional[str] = None, *, handler: ResourceHandler
    ) -> None:
        """
        compose a fully-qualified url by joining base service url, resource url
        and handler url,
        and map that to the handler object.
        Note: If there are duplicate handlers or any combination resulting in
        duplicate fq-url, the later will take precendence.
        """

        base_url = base_url or self.base_url
        handler.url = join_url(base_url, self.route, handler.route)
        handler.url_regex = self.compile_path(handler.url)

        self.routes[(handler.method, handler.route)] = handler

    async def request(
        self,
        url: str,
        method: Methods,
        **kwargs,
    ) -> BaseModel | list[BaseModel] | dict | None:
        request_data: BaseModel | None = kwargs.get("request", None)

        fq_url = join_url(self.base_url, self.route, url)

        if not (handler := self.routes.get((method, url), None)):
            raise ValueError(f"could not find a mapping for <{method!s}: {url}>")

        if handler.url_regex.fullmatch(fq_url) is None:
            raise ValueError(f"Could not parse requested url: {fq_url}")

        RequestType = handler.request  # pylint: disable=C0103

        if request_data:
            params = self.__extract_request_params(request_data)

        # apply type validation if Request Type present in handler definition
        if RequestType:
            if not isinstance(request_data, RequestType) or (
                is_optional(RequestType)
                and type(request_data) not in typing.get_args(RequestType)
            ):
                expected_types = (
                    (RequestType,)
                    if not is_optional(RequestType)
                    else typing.get_args(RequestType)
                )

                expected_types = ",".join(tp.__name__ for tp in expected_types)
                raise ValueError(
                    f"expected request types: {expected_types}; found {type(request_data).__name__}"
                )

                response_type = handler.response or self.response_model
                timeout = httpx.Timeout(TIMEOUT_DEFAULT, connect=TIMEOUT_DEFAULT)
                try:
                    # TODO - add the followign default params to init
                    # - headers X
                    # - params (query_params)
                    # - auth
                    # - cookies
                    async with httpx.AsyncClient(
                        timeout=timeout, headers=self.headers
                    ) as client:
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
                                    json=body_params,
                                )
                            case Methods.PUT:
                                response = await client.put(
                                    url=fq_url,
                                    headers=headers,
                                    params=query_params,
                                    data=json.dumps(body_params),
                                )
                            case Methods.PATCH:
                                response = await client.patch(
                                    url=fq_url,
                                    headers=headers,
                                    params=query_params,
                                    data=json.dumps(body_params),
                                )
                            case Methods.DELETE:
                                response = await client.delete(
                                    url=fq_url,
                                    headers=headers,
                                    params=query_params,
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

    def __extract_request_params(
        self, request_data: BaseModel
    ) -> dict[ParamTypes, dict]:
        headers, query_params, body_params = self.headers, {}, {}

        model_fields: dict = (
            request_data.__fields__
            if PYDANTIC_VERSION.startswith("2.")
            else request_data.model_fields
        )

        for field, field_info in model_fields.items():
            if isinstance(field_info, params.Query):
                query_params |= deserialize(request_data, field)
            elif isinstance(field_info, params.Header):
                headers |= deserialize(request_data, field)
            elif isinstance(field_info, (params.Body, FieldInfo)):
                body_params |= deserialize(request_data, field)
            else:
                raise ValueError(f"Invalid field class specified: {field_info}")

        return {
            ParamTypes.header: headers,
            ParamTypes.query: query_params,
            ParamTypes.body: body_params,
        }
