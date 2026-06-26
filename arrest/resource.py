# pylint: disable=W0707
import functools
import inspect
import json
from functools import cached_property
from typing import Any, Mapping, Optional, TypeAlias, TypeVar, Union, cast
from urllib.parse import urljoin, urlparse

import httpx
from httpx import Headers, QueryParams
from pydantic import BaseModel, ValidationError
from typing_extensions import Unpack

from arrest._config import ArrestConfig, HttpxClientInputs
from arrest.converters import compile_path
from arrest.defaults import ROOT_RESOURCE
from arrest.exceptions import ArrestHTTPException, HandlerNotFound, ResponseError
from arrest.handler import HandlerKey, ResourceHandler
from arrest.http import Methods
from arrest.logging import logger
from arrest.params import Param, Params, ParamTypes
from arrest.types import ExceptionHandlers
from arrest.utils import (
    extract_model_field,
    extract_resource_and_suffix,
    is_rootmodel,
    join_url,
    jsonable_encoder,
    lookup_exception_handler,
    validate_model,
)
from arrest.utils import retry as arrest_retry

T = TypeVar("T")
ResourceHandlerType: TypeAlias = ResourceHandler | Mapping[str, Any] | tuple[Any, ...]


class Resource:
    """
    A python class used to define a RESTful resource.

    Usage:
        ```python
        >>> from arrest import Resource

        >>> user_resource = Resource(name="user", route="/users", handlers=[("GET", "/")])
        ```

    Handlers can be provided as a list of tuple, dictionary or instances of `ResourceHandler`

    If provided as a dict or `ResourceHandler`, the keys / fields have to be set according to
    the `ResourceHandler` definiion.

    If provided as a tuple, at minimum 2 entries `(method, route)` or a maximum of 5 entries
    (method, route, request, response, callback) can be defined.
    """

    def __init__(
        self,
        name: Optional[str] = None,
        *,
        route: Optional[str],
        response_model: Optional[T] = None,
        handlers: list[ResourceHandlerType] | None = None,
        client: Optional[httpx.AsyncClient] = None,
        # config: per-request defaults (merge through the chain)
        headers: Optional[dict[str, str]] = None,
        cookies: Optional[dict[str, Any]] = None,
        params: Optional[dict[str, Any]] = None,
        timeout: Optional[float] = None,
        max_retries: Optional[int] = None,
        auth: Any = None,
        follow_redirects: Optional[bool] = None,
        **client_kwargs: Unpack[HttpxClientInputs],
    ) -> None:
        """
        Parameters:
            name:
                Unique name of the resource
            route:
                Unique route to the resource
            response_model:
                Pydantic datamodel to wrap the json response
            handlers:
                List of handlers
            client:
                An httpx.AsyncClient instance
            max_retries:
                Maximum number of application-level retries managed
                by tenacity. If you want to to transport-level retry,
                check out [docs](whats-new.md#use-the-standard-retry-mechanism-from-httpx-transport)
            headers:
                Default request headers for this resource
            cookies:
                Default request cookies for this resource
            params:
                Default query params for this resource
            timeout:
                Default request timeout (seconds).
            auth:
                Default authentication for this resource.
            follow_redirects:
                Whether to follow redirects by default.
            client_kwargs:
                Transport-level httpx.AsyncClient parameters.
        """

        self._client: Optional[httpx.AsyncClient] = None
        self._transport_kwargs = client_kwargs

        self.base_url = "/"  # will be filled once bound to a service
        self.route = route or ""

        self.name = self.get_resource_name(name=name)
        self.response_model = response_model
        self.routes: dict[HandlerKey, ResourceHandler] = {}

        self.config = ArrestConfig(
            headers=headers or {},
            cookies=cookies or {},
            params=params or {},
            timeout=timeout,
            max_retries=max_retries,
            auth=auth,
            follow_redirects=follow_redirects,
        )

        self._exception_handlers: ExceptionHandlers = None

        # initialize default GET handler
        self._bind_handler(
            base_url=self.base_url,
            handler=ResourceHandler(
                method=Methods.GET,
                route=extract_resource_and_suffix(self.route)[1],
                request=None,
                response=self.response_model,
                callback=None,
            ),
        )

        self.initialize_handlers(handlers=handlers if handlers else [])
        if client:
            self._client = client

    @cached_property
    def httpx_args(self) -> dict:
        """Transport + httpx-compatible config, ready for ``httpx.AsyncClient(**...").

        Read-only.  Frozen on first access.  Use this in custom handlers.
        """
        return {**self._transport_kwargs, **self.config.httpx_args()}

    def get_resource_name(self, name: Optional[str]) -> str:
        derived_name = name if name else self.route.strip("/").split("/")[0]
        return derived_name if derived_name else ROOT_RESOURCE

    def handler(
        self,
        path: str,
    ) -> Any:
        """
        Decorator to bind a custom handler to the resource

        Args:
            path (str): path relative to the current resource

        Returns:
            Any
        """

        def wrapper(func):
            @functools.wraps(func)
            async def wrapped(*args, **kwargs):
                url = join_url(self.base_url, self.route, path)
                return await func(self, url, *args, **kwargs)

            if getattr(self, func.__name__, None) is None:
                setattr(self, func.__name__, wrapped)
            return wrapped

        return wrapper

    async def request(
        self,
        method: Methods,
        path: str,
        request: Union[BaseModel, Mapping[str, Any], None] = None,
        headers: Optional[Mapping[str, str]] = None,
        query: Optional[Mapping[str, str]] = None,
        cookies: Optional[dict[str, str]] = None,
        timeout: Optional[float] = None,
        follow_redirects: Optional[bool] = None,
        **kwargs,
    ) -> Any | None:
        """
        Makes an HTTP request against a handler route

        Usage:
            ```python
            >>> user_resource.user.request(method="GET")
            ```

        Parameters:
            method:
                The HTTP method for the request
            path:
                Path to a handler specified in the resource
            request:
                A pydantic object containing the necessary fields
                to make an http request to the handler url

                **Must match the corresponding `handler.request` pydantic model**
            headers:
                A multi-dict or `httpx.Headers` containing additional
                header key-value pairs
            query:
                A multi-dict or `httpx.QueryParams` containing additional
                query-param key-value pairs
            cookies:
                Additional cookie key-value pairs for this call.
            timeout:
                Override the default timeout for this call.
            follow_redirects:
                Override redirect-following for this call.
            **kwargs:
                Keyword-arguments matching the path params, if any

        Returns:
            Response:
                A JSON response in form of a list or dict
                `or`, Deserialized into the response pydantic model
                `or`, Return value of the callback fn
        """

        path_query_params, path = self._extract_query_params(path)

        if not (match := self.get_matching_handler(method=method, path=path, **kwargs)):
            logger.warning("no matching handler found for request")
            raise HandlerNotFound(message="no matching handler found for request")

        handler, url = match

        # Merge per-call config with resource config.
        # Config defaults go UNDER the model-extracted values.
        final_config = self.config.merge(
            ArrestConfig(
                headers=dict(headers or {}),
                cookies=cookies or {},
                timeout=timeout,
                follow_redirects=follow_redirects,
            )
        )

        # Pass config defaults as the base headers/query; extract_request_params
        # will |= the model-extracted values on top.
        params = self.extract_request_params(
            request_type=handler.request,
            request_data=request,
            headers={**final_config.headers, **(dict(headers or {}))},
            query={
                **(dict(query or {})),
                **path_query_params,
                **final_config.params,
            },
        )

        response_type = handler.response or self.response_model or None

        retry_count = final_config.max_retries

        fn_make_request = (
            arrest_retry(
                n_retries=retry_count, exceptions=(ArrestHTTPException, Exception)
            )(self.make_request)
            if retry_count
            else self.make_request
        )

        try:
            response = await fn_make_request(
                url=url,
                method=method,
                params=params,
                response_type=response_type,
                config=final_config,
            )

        # custom exception handling
        except Exception as exc:
            exc_handler = lookup_exception_handler(self.exception_handlers, exc)
            if not exc_handler:
                raise exc

            response = exc_handler(exc)

        if handler.callback:
            try:
                if inspect.iscoroutinefunction(handler.callback):
                    callback_response = await handler.callback(response)
                else:
                    callback_response = handler.callback(response)
            except Exception:
                logger.warning("something went wrong during callback", exc_info=True)
                raise
            return callback_response

        return response

    async def get(
        self,
        path: str,
        request: Optional[BaseModel] = None,
        headers: Optional[Mapping[str, str]] = None,
        query: Optional[Mapping[str, str]] = None,
        **kwargs,
    ):
        """
        Makes a `HTTP GET` request

        see [request][arrest.resource.Resource.request]
        """
        return await self.request(
            method=Methods.GET,
            path=path,
            request=request,
            headers=headers,
            query=query,
            **kwargs,
        )

    async def post(
        self,
        path: str,
        request: Optional[BaseModel] = None,
        headers: Optional[Mapping[str, str]] = None,
        query: Optional[Mapping[str, str]] = None,
        **kwargs,
    ):
        """
        Makes a `HTTP POST` request

        see [request][arrest.resource.Resource.request]
        """
        return await self.request(
            method=Methods.POST,
            path=path,
            request=request,
            headers=headers,
            query=query,
            **kwargs,
        )

    async def put(
        self,
        path: str,
        request: Optional[BaseModel] = None,
        headers: Optional[Mapping[str, str]] = None,
        query: Optional[Mapping[str, str]] = None,
        **kwargs,
    ):
        """
        Makes a `HTTP PUT` request

        see [request][arrest.resource.Resource.request]
        """
        return await self.request(
            method=Methods.PUT,
            path=path,
            request=request,
            headers=headers,
            query=query,
            **kwargs,
        )

    async def patch(
        self,
        path: str,
        request: Optional[BaseModel] = None,
        headers: Optional[Mapping[str, str]] = None,
        query: Optional[Mapping[str, str]] = None,
        **kwargs,
    ):
        """
        Makes a `HTTP PATCH` request

        see [request][arrest.resource.Resource.request]
        """
        return await self.request(
            method=Methods.PATCH,
            path=path,
            request=request,
            headers=headers,
            query=query,
            **kwargs,
        )

    async def delete(
        self,
        path: str,
        request: Optional[BaseModel] = None,
        headers: Optional[Mapping[str, str]] = None,
        query: Optional[Mapping[str, str]] = None,
        **kwargs,
    ):
        """
        Makes a `HTTP DELETE` request

        see [request][arrest.resource.Resource.request]
        """
        return await self.request(
            method=Methods.DELETE,
            path=path,
            request=request,
            headers=headers,
            query=query,
            **kwargs,
        )

    async def head(
        self,
        path: str,
        request: Optional[BaseModel] = None,
        headers: Optional[Mapping[str, str]] = None,
        query: Optional[Mapping[str, str]] = None,
        **kwargs,
    ):
        """
        Makes a `HTTP HEAD` request

        see [request][arrest.resource.Resource.request]
        """
        return await self.request(
            method=Methods.HEAD,
            path=path,
            request=request,
            headers=headers,
            query=query,
            **kwargs,
        )

    async def options(
        self,
        path: str,
        request: Optional[BaseModel] = None,
        headers: Optional[Mapping[str, str]] = None,
        query: Optional[Mapping[str, str]] = None,
        **kwargs,
    ):
        """
        Makes a `HTTP OPTIONS` request

        see [request][arrest.resource.Resource.request]
        """
        return await self.request(
            method=Methods.OPTIONS,
            path=path,
            request=request,
            headers=headers,
            query=query,
            **kwargs,
        )

    def extract_request_params(
        self,
        request_type: Any,
        request_data: Any,
        headers: dict[str, str] | None = None,
        query: dict[str, Any] | None = None,
    ) -> Params:
        """
        extracts `header`, `body` and `query` params from the pydantic request model

        Parameters:
            request_type:
                a python type for the request data
            request_data:
                instance of the above type containing the request data
            headers:
                optional dictionary containing additional header key-value pairs
            query:
                optional dictionary containing additional query key-value pairs
        Returns:
            a `Params` object containing `header`, `body`, `query` fields
        """

        header_params = headers or {}
        query_params: dict[str, Any] = query or {}
        body_params: dict[Any, Any] = {}

        if request_type:
            # perform type validation on `request_data`
            request_data = validate_model(type_=request_type, obj=request_data)

        if is_rootmodel(request_data):
            return Params(
                header=Headers(header_params),
                query=QueryParams(query_params),
                body=jsonable_encoder(request_data),
            )

        if isinstance(request_data, BaseModel):
            # extract pydantic fields into `Query`, `Body` and `Header`
            model_fields = request_data.__class__.model_fields

            for field_name, field in model_fields.items():
                field_info = field
                field_info = cast(Param, field_info)
                if not hasattr(field_info, "_param_type"):
                    body_params |= extract_model_field(request_data, field_name)
                elif field_info._param_type == ParamTypes.query:
                    query_params |= extract_model_field(request_data, field_name)
                elif field_info._param_type == ParamTypes.header:
                    header_params |= extract_model_field(request_data, field_name)
                elif field_info._param_type == ParamTypes.body:
                    body_params |= extract_model_field(request_data, field_name)

        else:
            body_params = request_data

        return Params(
            header=Headers(header_params),
            query=QueryParams(query_params),
            body=jsonable_encoder(body_params),
        )

    async def make_request(
        self,
        url: str,
        method: Methods,
        params: Params,
        response_type: Any,
        config: ArrestConfig | None = None,
    ) -> Any:
        """
        (private) prepares and makes a http request,
        parses the response and raises appropriate exceptions

        Parameters:
            url:
                the complete url of the endpoint
            method:
                one of the available http methods
            params:
                dict containing `header`, `query` and `body` params
            response_type:
                a python type to deserialize the json response to
            config:
                merged ArrestConfig for this request

        Returns:
            Any:
                the returned json object or a parsed instance of `response_type`
        """
        cfg = config or ArrestConfig()

        try:
            if self._client:
                response = await self.__make_request(
                    client=self._client,
                    url=url,
                    method=method,
                    params=params,
                    config=cfg,
                )
            else:
                async with httpx.AsyncClient(
                    base_url=self.base_url,
                    **self._transport_kwargs,
                ) as client:
                    response = await self.__make_request(
                        client=client,
                        url=url,
                        method=method,
                        params=params,
                        config=cfg,
                    )

            status_code = response.status_code
            logger.info(f"{method!s} {url} returned with status code {status_code!s}")
            response.raise_for_status()
            if not response.content:
                return None
            try:
                response_body = response.json()
            except json.JSONDecodeError:
                try:
                    response_body = response.read().decode("utf-8", errors="strict")
                except UnicodeDecodeError:
                    raise ResponseError("Could not parse HTTP response")

            parsed_response = response_body
            if response_type:
                parsed_response = validate_model(response_type, response_body)

            return parsed_response

        except httpx.HTTPStatusError as exc:
            try:
                err_response_body = exc.response.json()
            except json.JSONDecodeError:
                err_response_body = exc.response.read().decode("utf-8", errors="strict")
            raise ArrestHTTPException(
                status_code=exc.response.status_code, data=err_response_body
            ) from exc

        except httpx.TimeoutException:
            raise ArrestHTTPException(
                status_code=httpx.codes.REQUEST_TIMEOUT,
                data="request timed out",
            )

        except httpx.RequestError:
            raise ArrestHTTPException(
                status_code=httpx.codes.INTERNAL_SERVER_ERROR,
                data="error occured while making request",
            )

    async def __make_request(
        self,
        client: httpx.AsyncClient,
        url: str,
        method: Methods,
        params: Params,
        config: ArrestConfig,
    ) -> httpx.Response:
        """(private) makes the actual http request using httpx

        Args:
            client (httpx.AsyncClient)
            url (str)
            method (Methods)
            params (Params)
            config (ArrestConfig)

        Returns:
            httpx.Response
        """

        header_params, query_params, body_params = (
            params.header,
            params.query,
            params.body,
        )

        # Build final kwargs for httpx — config defaults go under model-extracted values
        request_kwargs: dict[str, Any] = dict(
            url=url,
            headers=Headers({**config.headers, **dict(header_params)}),
            params=query_params,
            cookies=config.cookies or None,
            timeout=config.timeout,
        )
        if config.follow_redirects is not None:
            request_kwargs["follow_redirects"] = config.follow_redirects
        if config.auth is not None:
            request_kwargs["auth"] = config.auth

        match method:
            case Methods.GET:
                response = await client.get(**request_kwargs)
            case Methods.POST:
                response = await client.post(**request_kwargs, json=body_params)
            case Methods.PUT:
                response = await client.put(**request_kwargs, json=body_params)
            case Methods.PATCH:
                response = await client.patch(**request_kwargs, json=body_params)
            case Methods.DELETE:
                response = await client.delete(**request_kwargs)
            case Methods.HEAD:
                response = await client.head(**request_kwargs)
            case Methods.OPTIONS:
                response = await client.options(**request_kwargs)

        return response

    def get_matching_handler(
        self, method: Methods, path: str, **kwargs
    ) -> tuple[ResourceHandler, str] | None:
        for handler in self.routes.values():
            parsed_path = handler.parse_path(method=method, path=path, **kwargs)
            if parsed_path is not None:
                url = join_url(self.route, parsed_path)
                return handler, url

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
        handler.path_regex, handler.path_format, handler.param_types = compile_path(
            handler.route
        )

        self.routes[HandlerKey(*(handler.method, handler.path_format))] = handler

    def _extract_query_params(self, url: str) -> tuple[QueryParams, str]:
        url_parsed = urlparse(url)
        url_without_query = urljoin(url, urlparse(url).path)

        return QueryParams(url_parsed.query), url_without_query

    def initialize_handlers(
        self,
        base_url: str | None = None,
        handlers: list[ResourceHandlerType] | None = None,
    ) -> None:
        """
        specifically used to inject `base_url` from a Service class to
        downstream Resources.
        Should not be used separately (unless you want to break things)
        """

        _handlers: list[ResourceHandlerType] = (
            list(self.routes.values()) if self.routes else []
        )
        if handlers:
            _handlers.extend(handlers)

        if not _handlers:
            return  # pragma: no cover

        for _handler in _handlers:
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
                elif isinstance(_handler, ResourceHandler):
                    self._bind_handler(base_url=base_url, handler=_handler)
                else:
                    raise ValueError("invalid handler type specified")
            except ValidationError:
                raise ValueError("cannot initialize handler signature")

    @property
    def exception_handlers(self):
        return self._exception_handlers

    @exception_handlers.setter
    def exception_handlers(self, exc_handlers: ExceptionHandlers):
        self._exception_handlers = exc_handlers
