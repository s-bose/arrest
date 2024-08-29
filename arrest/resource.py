# pylint: disable=W0707
import functools
import inspect
import json
from typing import Any, List, Mapping, Optional, Tuple, Type, Union, cast

import httpx
from httpx import Headers, QueryParams
from pydantic import BaseModel, ValidationError
from pydantic.fields import FieldInfo
from typing_extensions import Unpack

from arrest._config import PYDANTIC_V2, HttpxClientInputs
from arrest.converters import compile_path
from arrest.defaults import DEFAULT_TIMEOUT, ROOT_RESOURCE
from arrest.exceptions import ArrestHTTPException, HandlerNotFound
from arrest.handler import HandlerKey, ResourceHandler
from arrest.http import Methods
from arrest.logging import logger
from arrest.params import Param, Params, ParamTypes
from arrest.types import ExceptionHandlers
from arrest.utils import (
    extract_model_field,
    join_url,
    jsonable_encoder,
    lookup_exception_handler,
    retry,
    validate_model,
)


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
        response_model: Optional[Type[BaseModel]] = None,
        handlers: Union[
            List[ResourceHandler],
            List[Mapping[str, Any]],
            List[Tuple[Any, ...]],
        ] = None,
        client: Optional[httpx.AsyncClient] = None,
        retry: Optional[int] = None,
        **kwargs: Unpack[HttpxClientInputs],
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
            retry:
                Optional argument to specify the number of retries
            kwargs:
                Additional httpx.AsyncClient parameters, [see more](api.md/#httpx-client-arguments)
        """

        self._client: Optional[httpx.AsyncClient] = None
        self._httpx_args: Optional[HttpxClientInputs] = None

        self.base_url = "/"  # will be filled once bound to a service
        self.route = route
        self.retry = retry

        self.name = self.get_resource_name(name=name)
        self.response_model = response_model
        self.routes: dict[HandlerKey, ResourceHandler] = {}

        self._exception_handlers: ExceptionHandlers = None

        self.initialize_handlers(handlers=handlers)
        self.initialize_httpx(client=client, **kwargs)

    def get_resource_name(self, name: Optional[str]) -> str:
        derived_name = name if name else self.route.strip("/").split("/")[0]
        return derived_name if derived_name else ROOT_RESOURCE

    def handler(
        self,
        path: str,
    ) -> Any:
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
            **kwargs:
                Keyword-arguments matching the path params, if any

        Returns:
            Response:
                A JSON response in form of a list or dict
                `or`, Deserialized into the response pydantic model
                `or`, Return value of the callback fn
        """

        params: dict = {}

        if not (match := self.get_matching_handler(method=method, path=path, **kwargs)):
            logger.warning("no matching handler found for request")
            raise HandlerNotFound(message="no matching handler found for request")

        handler, url = match

        params = self.extract_request_params(
            request_type=handler.request,
            request_data=request,
            headers=headers,
            query=query,
            **kwargs,
        )

        response_type = handler.response or self.response_model or None

        fn_make_request = (
            retry(n_retries=self.retry, exceptions=(ArrestHTTPException, Exception))(self.make_request)
            if self.retry
            else self.make_request
        )

        try:
            response = await fn_make_request(
                url=url, method=method, params=params, response_type=response_type
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
        Makes a `HTTP DELETE` reque        # exception handling
        except Exception as exc:
            exc
            exc_handler = lookup_exception_handler(self.exception_handlers, exc)
            if not exc_handler:
                raise exc

            response = exc_handler(exc)st

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
        request_type: Type[BaseModel] | None,
        request_data: BaseModel | Mapping[str, Any] | None,
        headers: Mapping[str, str] | None = None,
        query: Mapping[str, Any] | None = None,
    ) -> Params:
        """
        extracts `header`, `body` and `query` params from the pydantic request model

        Parameters:
            request_type:
                a pydantic class for holding the request data
            request_data:
                instance of the above containing the data
            kwargs:
                optional keyword-arguments containing query parameters
        Returns:
            a `Params` object containing `header`, `body`, `query` fields
        """

        header_params = headers or {}
        query_params = query or {}
        body_params = {}

        if request_type:
            # perform type validation on `request_data`
            request_data = validate_model(type_=request_type, obj=request_data)

        if isinstance(request_data, BaseModel):
            # extract pydantic fields into `Query`, `Body` and `Header`
            model_fields: dict = request_data.model_fields if PYDANTIC_V2 else request_data.__fields__

            for field_name, field in model_fields.items():
                field_info = field if PYDANTIC_V2 else field.field_info
                field_info = cast(Param, field_info)
                if not hasattr(field_info, "_param_type") and isinstance(field_info, FieldInfo):
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
        response_type: Optional[Type[BaseModel]],
    ) -> Any:
        """
        (private) prepares and makes a http request,
        parses the response and raises appropriate exceptions

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

        try:
            if self._client:
                response = await self.__make_request(
                    client=self._client, url=url, method=method, params=params
                )
            else:
                async with httpx.AsyncClient(base_url=self.base_url, **self._httpx_args) as client:
                    response = await self.__make_request(client=client, url=url, method=method, params=params)

            status_code = response.status_code
            logger.info(f"{method!s} {url} returned with status code {status_code!s}")
            response.raise_for_status()
            response_body = response.json()

            # parse response to pydantic model
            parsed_response = response_body
            if response_type:
                response_type
                if isinstance(response_body, list):
                    parsed_response = [response_type(**item) for item in response_body]
                elif isinstance(response_body, dict):
                    parsed_response = response_type(**response_body)
                else:
                    raise ValueError(f"could not parse response to pydantic model {response_type.__name__}")

            return parsed_response

        except json.JSONDecodeError:
            # response content-type is not json
            return response.read().decode("utf-8", errors="strict")

        except httpx.HTTPStatusError as exc:
            try:
                err_response_body = exc.response.json()
            except json.JSONDecodeError:
                err_response_body = exc.response.read().decode("utf-8", errors="strict")
            raise ArrestHTTPException(status_code=exc.response.status_code, data=err_response_body) from exc

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
        self, client: httpx.AsyncClient, url: str, method: Methods, params: Params
    ) -> httpx.Response:
        """(private) makes the actual http request using httpx

        Args:
            client (httpx.AsyncClient)
            url (str)
            method (Methods)
            params (Params)

        Returns:
            httpx.Response
        """

        header_params, query_params, body_params = (
            params.header,
            params.query,
            params.body,
        )
        match method:
            case Methods.GET:
                response = await client.get(url=url, params=query_params, headers=header_params)
            case Methods.POST:
                response = await client.post(
                    url=url,
                    params=query_params,
                    headers=header_params,
                    json=body_params,
                )
            case Methods.PUT:
                response = await client.put(
                    url=url,
                    params=query_params,
                    headers=header_params,
                    json=body_params,
                )
            case Methods.PATCH:
                response = await client.patch(
                    url=url,
                    params=query_params,
                    headers=header_params,
                    json=body_params,
                )
            case Methods.DELETE:
                response = await client.delete(
                    url=url,
                    params=query_params,
                    headers=header_params,
                )
            case Methods.HEAD:
                response = await client.head(url=url, params=query_params, headers=header_params)

            case Methods.OPTIONS:
                response = await client.options(url=url, params=query_params, headers=header_params)

        return response

    def get_matching_handler(
        self, method: Methods, path: str, **kwargs
    ) -> tuple[ResourceHandler, str] | None:
        for handler in self.routes.values():
            parsed_path = handler.parse_path(method=method, path=path, **kwargs)
            if parsed_path is not None:
                url = join_url(self.route, parsed_path)
                return handler, url

    def _bind_handler(self, base_url: str | None = None, *, handler: ResourceHandler) -> None:
        """
        compose a fully-qualified url by joining base service url, resource url
        and handler url,
        and map that to the handler object.
        Note: If there are duplicate handlers or any combination resulting in
        duplicate fq-url, the later will take precendence.
        """

        base_url = base_url or self.base_url
        handler.path_regex, handler.path_format, handler.param_types = compile_path(handler.route)

        self.routes[HandlerKey(*(handler.method, handler.path_format))] = handler

    def initialize_handlers(
        self,
        base_url: str | None = None,
        handlers: list[ResourceHandler] | list[Mapping[str, Any]] | list[tuple[Any, ...]] = None,
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
                    self._bind_handler(base_url=base_url, handler=ResourceHandler(**_handler))
                elif isinstance(_handler, tuple):
                    if len(_handler) < 2:
                        raise ValueError("Too few arguments to unpack. Expected atleast 2")
                    if len(_handler) > 5:
                        raise ValueError(f"Too many arguments to unpack. Expected 5, got {len(_handler)}")

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

    def initialize_httpx(
        self, client: Optional[httpx.AsyncClient], **kwargs: Unpack[HttpxClientInputs]
    ) -> None:
        if client:
            self._client = client
        elif self._httpx_args:
            # already initialized
            self._httpx_args |= kwargs
        else:
            timeout = kwargs.get("timeout")
            if not timeout:
                kwargs["timeout"] = httpx.Timeout(timeout=DEFAULT_TIMEOUT, connect=DEFAULT_TIMEOUT)

            if isinstance(timeout, int):
                kwargs["timeout"] = httpx.Timeout(timeout=timeout, connect=timeout)

            self._httpx_args = HttpxClientInputs(**kwargs)

    @property
    def exception_handlers(self):
        return self._exception_handlers

    @exception_handlers.setter
    def exception_handlers(self, exc_handlers: ExceptionHandlers):
        self._exception_handlers = exc_handlers
