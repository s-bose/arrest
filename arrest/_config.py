from typing import Any, Callable, Mapping, Optional, TypedDict, Union

from httpx import AsyncBaseTransport, Limits, _types
from pydantic.version import VERSION as PYDANTIC_VERSION

PYDANTIC_V2 = PYDANTIC_VERSION.startswith("2")


class HttpxClientInputs(TypedDict, total=False):
    """
    a typed dict to check for all the necessary fields
    for building an `httpx.AsyncClient` instance
    """

    auth: Optional[_types.AuthTypes]
    params: Optional[_types.QueryParamTypes]
    headers: Optional[_types.HeaderTypes]
    cookies: Optional[_types.CookieTypes]
    verify: Optional[_types.VerifyTypes]
    cert: Optional[_types.CertTypes]
    http2: Optional[bool]
    proxies: Optional[_types.ProxiesTypes]
    mounts: Optional[Mapping[str, AsyncBaseTransport]]
    timeout: Optional[_types.TimeoutTypes]
    follow_redirects: Optional[bool]
    limits: Optional[Limits]
    max_redirects: Optional[int]
    event_hooks: Optional[Mapping[str, list[Callable[..., Any]]]]
    transport: Optional[AsyncBaseTransport]
    trust_env: Optional[bool]
    default_encoding: Union[str, Callable[[bytes], str]]
    app: Callable[..., Any]


class ArrestConfig(TypedDict, total=False):
    """
    a typed dict storing the global configs for the service and resources
    """

    convert_headers_to_kebab_case: Optional[bool] = False
    use_default_resource_handler: Optional[bool] = True
    parse_non_json_responses: Optional[bool] = False
