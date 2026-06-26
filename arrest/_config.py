from typing import Any, Callable, Mapping, Optional, TypedDict, Union
import ssl
from httpx import AsyncBaseTransport, Limits, _types

VerifyType = Union[bool, str, ssl.SSLContext, None]


class HttpxClientInputs(TypedDict, total=False):
    """
    a typed dict to check for all the necessary fields
    for building an `httpx.AsyncClient` instance
    """

    auth: Optional[_types.AuthTypes]
    params: Optional[_types.QueryParamTypes]
    headers: Optional[_types.HeaderTypes]
    cookies: Optional[_types.CookieTypes]
    verify: Optional[VerifyType]
    cert: Optional[_types.CertTypes]
    http2: Optional[bool]
    proxies: Optional[_types.ProxyTypes]
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
