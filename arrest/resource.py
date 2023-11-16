# pylint: disable=W0707
from typing import Optional, Pattern, Type, Callable, Mapping, Any
from functools import partial
import re
import json
import httpx
from pydantic import BaseModel, ValidationError
from pydantic.fields import FieldInfo
from pydantic.version import VERSION as PYDANTIC_VERSION

from arrest.http import Methods
from arrest.exceptions import ArrestHTTPException
from arrest.params import ParamTypes, Query, Header, Body
from arrest.utils import join_url, deserialize
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
    request: Type[BaseModel] | None = None
    response: Type[BaseModel] | None = None
    callback: Callable | None = None
    url: str | None = None
    url_regex: Pattern | None = None


class Resource:
    def __init__(
        self,
        name: str | None = None,
        *,
        route: str,
        headers: dict | None = HEADER_DEFAULTS,
        timeout: int | None = TIMEOUT_DEFAULT,
        response_model: Type[BaseModel] | None = None,
        handlers: list[ResourceHandler]
        | list[Mapping[str, Any]]
        | list[tuple[Any, ...]] = [],
    ) -> None:
        self.base_url = "/"  # will be filled once bound to a service
        self.route = route
        derived_name = name if name else self.route.strip("/").split("/")[0]
        self.name = derived_name if derived_name else "root"
        self.response_model = response_model

        # TODO - add the following default params to init
        # - headers X
        # - params (query_params)
        # - auth
        # - cookies
        self.headers = headers
        self.timeout = httpx.Timeout(timeout=timeout, connect=timeout)

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

    def initialize_handlers(self, base_url: str | None = None) -> None:
        """
        specifically used to inject `base_url` from a Service class to
        downstream Resources.
        Should not be used separately (unless you want to break things)
        """
        handlers = self.routes.values()

        for handler in handlers:
            self._bind_handler(base_url=base_url, handler=handler)

    def _bind_handler(
        self, base_url: str | None = None, *, handler: ResourceHandler
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
    ) -> Any | None:
        """
        Parameters
        ----------

        request : BaseModel
            pydantic object containing the necessary fields to make an http
            request to the handler url

            must match the corresponding handler.request pydantic model

        **kwargs : dict
            keyword-args matching the request fields that can be alternatively
            passed
        """
        params: dict = None
        request_data: BaseModel | None = kwargs.get("request", None)

        fq_url = join_url(self.base_url, self.route, url)

        try:
            handler = next(
                _handler
                for _handler in self.routes.values()
                if _handler.url_regex.fullmatch(fq_url) is not None
            )
        except StopIteration:
            raise ValueError(f"Could not parse requested url: {fq_url}")

        RequestType = handler.request  # pylint: disable=C0103

        # apply type validation if Request Type present in handler definition

        if not self.__validate_request(RequestType, request_data):
            raise ValueError(
                f"type of {type(request_data).__name__} does not match provided type {RequestType.__name__}"
            )

        if request_data:
            params = self.__extract_request_params(request_data)
        else:
            params = self.__extract_request_params(kwargs)

        # response_type = handler.response or self.response_model

        return await self.__make_request(
            url=fq_url, method=method, params=params, response_type=None
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
        self, request_data: BaseModel | None, **kwargs
    ) -> dict[ParamTypes, dict]:
        headers, query_params, body_params = self.headers, {}, {}

        if not kwargs:
            return {
                ParamTypes.header: {},
                ParamTypes.query: {},
                ParamTypes.body: {},
            }
        if request_data:
            model_fields: dict = (
                request_data.__fields__
                if PYDANTIC_VERSION.startswith("2.")
                else request_data.model_fields
            )

            for field, field_info in model_fields.items():
                if isinstance(field_info, Query):
                    query_params |= deserialize(request_data, field)
                elif isinstance(field_info, Header):
                    headers |= deserialize(request_data, field)
                elif isinstance(field_info, (Body, FieldInfo)):
                    body_params |= deserialize(request_data, field)
                else:
                    raise ValueError(f"Invalid field class specified: {field_info}")

            return {
                ParamTypes.header: headers,
                ParamTypes.query: query_params,
                ParamTypes.body: body_params,
            }

    async def __make_request(
        self,
        url: str,
        method: Methods,
        params: dict,
        response_type: Optional[Type[BaseModel]],
    ):
        headers, query_params, body_params = (
            params[ParamTypes.header],
            params[ParamTypes.query],
            params[ParamTypes.body],
        )
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout, headers=headers
            ) as client:
                match method:
                    case Methods.GET:
                        response = await client.get(url=url, params=query_params)
                    case Methods.POST:
                        response = await client.post(
                            url=url,
                            params=query_params,
                            json=body_params,
                        )
                    case Methods.PUT:
                        response = await client.put(
                            url=url,
                            params=query_params,
                            data=json.dumps(body_params),
                        )
                    case Methods.PATCH:
                        response = await client.patch(
                            url=url,
                            params=query_params,
                            data=json.dumps(body_params),
                        )
                    case Methods.DELETE:
                        response = await client.delete(
                            url=url,
                            params=query_params,
                        )
                    case Methods.HEAD:
                        response = await client.head(url=url, params=query_params)

                response.raise_for_status()
                response_body = response.json()

                # parse response to pydantic model
                parsed_response = response_body
                if response_type:
                    if isinstance(response_body, list):
                        parsed_response = [
                            response_type(**item) for item in response_body
                        ]
                    elif isinstance(response_body, dict):
                        parsed_response = response_type(**response_body)
                    else:
                        raise ValueError(
                            f"could not parse response to pydantic model {response_type.__name__}"
                        )

                return parsed_response

        # exception handling
        except httpx.HTTPStatusError as exc:
            err_response_body = response.json()
            raise ArrestHTTPException(
                status_code=exc.response.status_code, data=err_response_body
            ) from exc

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

    def __validate_request(
        self, request_type: Type[BaseModel] | None, request_data: BaseModel | None
    ):
        if not request_data or (
            request_type and isinstance(request_data, request_type)
        ):
            return True
        return False
