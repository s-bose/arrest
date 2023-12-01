# pylint: disable=W0707
import inspect
import json
from typing import Any, Mapping, Type, cast

import httpx
from pydantic import BaseModel, ValidationError
from pydantic.fields import FieldInfo
from pydantic.version import VERSION as PYDANTIC_VERSION

from arrest.converters import compile_path, replace_params
from arrest.defaults import HEADER_DEFAULTS, TIMEOUT_DEFAULT
from arrest.exceptions import ArrestError, ArrestHTTPException, HandlerNotFound
from arrest.handler import HandlerKey, ResourceHandler
from arrest.http import Methods
from arrest.logging import logger
from arrest.params import Param, ParamTypes
from arrest.utils import join_url, process_body, process_header, process_query


class Resource:
    """
    A python class used to define a RESTful resource.

    Usage:

    ```python
    >>> from arrest import Resource

    >>> user_resource = Resource(name="user", route="/users", handlers=[("GET", "/")])
    ```

    **Parameters:**

    * **name** - *(optional)* A unique name for the resource. If not present, will be picked
    from `route`
    * **route** - A unique route for the resource. Must begin with a slash.
    * **headers** - *(optional)* A dictionary of header values to be used for all handlers
    under this resource. Defaults to `{"Content-Type": "application/json}`.
    * **timeout** - *(optional)* Timeout (in seconds) for all HTTP requests from this resource.
    Defaults to 60.
    * **response_model** - *(optional)* Pydantic response model to parse all responses under
    the resource.
    * **handlers** - *(optional)* - a list of handlers for the resource.

    Handlers can be provided as a list of tuple, dictionary or instances of `ResourceHandler`

    If provided as a dict or `ResourceHandler`, the keys / fields have to be set according to
    the `ResourceHandler` definiion.

    If provided as a tuple, at minimum 2 entries `(method, route)` or a maximum of 5 entries
    (method, route, request, response, callback) can be defined.
    """

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
        | list[tuple[Any, ...]] = None,
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

        self.routes: dict[HandlerKey, ResourceHandler] = {}

        self.initialize_handlers(handlers=handlers)

    def initialize_handlers(
        self,
        base_url: str | None = None,
        handlers: list[ResourceHandler]
        | list[Mapping[str, Any]]
        | list[tuple[Any, ...]] = None,
    ) -> None:
        """
        specifically used to inject `base_url` from a Service class to
        downstream Resources.
        Should not be used separately (unless you want to break things)
        """
        if self.routes:
            handlers = list(self.routes.values())

        if not handlers:
            return

        for _handler in handlers:
            try:
                if isinstance(_handler, dict):
                    self._bind_handler(
                        base_url=base_url, handler=ResourceHandler(**_handler)
                    )
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
                        base_url=base_url,
                        handler=ResourceHandler(
                            method=method,
                            route=route,
                            request=len(rest) >= 1 and rest[0] or None,
                            response=len(rest) >= 2 and rest[1] or None,
                            callback=len(rest) >= 3 and rest[2] or None,
                        ),
                    )
                elif isinstance(_handler, BaseModel):
                    self._bind_handler(base_url=base_url, handler=_handler)
                else:
                    raise ValueError("invalid handler type specified")
            except ValidationError:
                raise ValueError("cannot initialize handler signature")

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
        url_regex, handler_url, handler_path_params = compile_path(handler.url)

        handler.url_regex = url_regex
        handler.path_params = handler_path_params
        handler.url = handler_url

        self.routes[HandlerKey(*(handler.method, handler.route))] = handler

    async def request(
        self,
        method: Methods,
        url: str,
        request: BaseModel | None = None,
        **kwargs,
    ) -> Any | None:
        """
        Makes an HTTP request against a handler route

        Usage:

        ```python
        >>> user_resource.user.request(method="GET")
        ```

        **Parameters:**

        request : BaseModel
            pydantic object containing the necessary fields to make an http
            request to the handler url

            must match the corresponding handler.request pydantic model

        **kwargs : dict
            keyword-args matching the path params, if any
        """
        params: dict = {}

        if not (
            match := self.get_matching_handler(method=method, url=url, **kwargs)
        ):
            logger.warning("no matching handler found for request")
            raise HandlerNotFound("no matching handler found for request")

        handler, url = match

        params = self.extract_request_params(
            request_type=handler.request, request_data=request
        )

        response_type = handler.response or self.response_model or None

        response = await self.__make_request(
            url=url, method=method, params=params, response_type=response_type
        )

        if handler.callback:
            try:
                if inspect.iscoroutinefunction(handler.callback):
                    callback_response = await handler.callback(response)
                else:
                    callback_response = handler.callback(response)
            except Exception as exc:
                logger.warning("something went wrong during callback", exc_info=True)
                raise ArrestError(str(exc)) from exc
            return callback_response

        return response

    async def get(
        self,
        url: str,
        request: BaseModel | None = None,
        **kwargs,
    ):
        """
        Makes a `HTTP GET` request

        see `request()`
        """
        return await self.request(
            method=Methods.GET, url=url, request=request, **kwargs
        )

    async def post(
        self,
        url: str,
        request: BaseModel | None = None,
        **kwargs,
    ):
        """
        Makes a `HTTP POST` request

        see `request()`
        """
        return await self.request(
            method=Methods.POST, url=url, request=request, **kwargs
        )

    async def put(
        self,
        url: str,
        request: BaseModel | None = None,
        **kwargs,
    ):
        """
        Makes a `HTTP PUT` request

        see `request()`
        """
        return await self.request(
            method=Methods.PUT, url=url, request=request, **kwargs
        )

    async def patch(
        self,
        url: str,
        request: BaseModel | None = None,
        **kwargs,
    ):
        """
        Makes a `HTTP PATCH` request

        see `request()`
        """
        return await self.request(
            method=Methods.PATCH, url=url, request=request, **kwargs
        )

    async def delete(
        self,
        url: str,
        request: BaseModel | None = None,
        **kwargs,
    ):
        """
        Makes a `HTTP GET` request

        see `request()`
        """
        return await self.request(
            method=Methods.DELETE, url=url, request=request, **kwargs
        )

    async def head(
        self,
        url: str,
        request: BaseModel | None = None,
        **kwargs,
    ):
        """
        Makes a `HTTP HEAD` request

        see `request()`
        """
        return await self.request(
            method=Methods.HEAD, url=url, request=request, **kwargs
        )

    async def options(
        self,
        url: str,
        request: BaseModel | None = None,
        **kwargs,
    ):
        """
        Makes a `HTTP OPTIONS` request

        see `request()`
        """
        return await self.request(
            method=Methods.OPTIONS, url=url, request=request, **kwargs
        )

    def extract_request_params(
        self,
        request_type: Type[BaseModel] | None,
        request_data: BaseModel | None,
    ) -> dict[ParamTypes, dict]:
        """
        extracts `header`, `body` and `query` params from the pydantic request model

        Parameters
        ----------

        request_type : Type[BaseModel] | None
            a pydantic class for holding the request data

        request_data : BaseModel | None
            instance of the above containing the data

        Returns
        -------

        dict[ParamTypes, dict]
            a dictionary containing `header`, `body`, `query` params in separate dicts
        """

        # apply type validation if Request Type present in handler definition
        if not self.__validate_request(request_type, request_data):
            raise ValueError(
                f"type of {type(request_data).__name__} does not match provided type {request_type.__name__}"
            )
        headers, query_params, body_params = dict(self.headers), {}, {}

        if request_data:
            # extract pydantic fields into `Query`, `Body` and `Header`
            model_fields: dict = (
                request_data.__fields__
                if PYDANTIC_VERSION.startswith("2.")
                else request_data.model_fields
            )

            for field, field_info in model_fields.items():
                field_info = cast(Param, field_info)
                if not hasattr(field_info, "_param_type") and isinstance(
                    field_info, FieldInfo
                ):
                    body_params |= process_body(request_data, field, body_params)
                elif field_info._param_type == ParamTypes.query:
                    query_params |= process_query(request_data, field, query_params)
                elif field_info._param_type == ParamTypes.header:
                    headers |= process_header(request_data, field, headers)
                elif field_info._param_type == ParamTypes.body:
                    body_params |= process_body(request_data, field, body_params)

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
        response_type: Type[BaseModel] | None,
    ) -> Any:
        """
        (private) makes the actual http call using httpx

        Parameters
        ----------

        url : str
            the complete url of the endpoint
        method : Methods
            one of the available http methods
        params : dict
            dict containing `header`, `query` and `body` params
        response_type : Optional[Type[BaseModel]]
            optional response_type to deserialize the json response to

        Returns
        -------

        Any
            a json object or a parsed pydantic object
        """
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

                    case Methods.OPTIONS:
                        response = await client.options(url=url, params=query_params)

                status_code = response.status_code
                logger.debug(
                    f"{method!s} {url} returned with status code {status_code!s}"
                )
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
            err_response_body = exc.response.json()
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
        self,
        request_type: Type[BaseModel] | None,
        request_data: BaseModel | None,
    ):
        if not request_data or (
            request_type and isinstance(request_data, request_type)
        ):
            return True
        return False

    def get_matching_handler(
        self, method: Methods, url: str, **kwargs
    ) -> tuple[ResourceHandler, str] | None:
        for key, handler in self.routes.items():
            if method != key.method:
                continue

            req_url = join_url(self.base_url, self.route, url)
            if seen_params := handler.extract_params(req_url):
                for k, v in seen_params.items():
                    if v is not None:
                        kwargs[k] = v

            if kwargs:
                handler_url, remaining_params = replace_params(
                    handler.url, kwargs, handler.path_params
                )
                if remaining_params:
                    continue
                req_url = handler_url

            if handler.url_regex.fullmatch(req_url):
                return handler, req_url
