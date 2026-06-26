import ssl
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Optional, TypedDict, Union

from httpx import AsyncBaseTransport, Limits, _types

VerifyType = Union[bool, str, ssl.SSLContext, None]


class HttpxClientInputs(TypedDict, total=False):
    """Transport-level fields passed to ``httpx.AsyncClient`` at creation time.

    These do **not** merge through the Service → Resource → handler chain.
    For per-request defaults (headers, cookies, timeout, etc.) see :class:`ArrestConfig`.
    """

    verify: Optional[VerifyType]
    cert: Optional[_types.CertTypes]
    http2: Optional[bool]
    proxies: Optional[_types.ProxyTypes]
    mounts: Optional[Mapping[str, AsyncBaseTransport]]
    limits: Optional[Limits]
    transport: Optional[AsyncBaseTransport]
    trust_env: Optional[bool]
    event_hooks: Optional[Mapping[str, list[Callable[..., Any]]]]
    default_encoding: Union[str, Callable[[bytes], str]]
    app: Callable[..., Any]


@dataclass
class ArrestConfig:
    """Per-request defaults that merge through the hierarchy chain.

    Priority (highest to lowest):
        per-call kwargs  >  handler config  >  resource config  >  service config

    Dict fields (``headers``, ``cookies``, ``params``) merge additively.
    Scalar fields (``timeout``, ``retry``, ``auth``, ``follow_redirects``) are
    overridden by the highest-priority non-``None`` value.
    """

    headers: dict[str, str] = field(default_factory=dict)
    cookies: dict[str, Any] = field(default_factory=dict)
    params: dict[str, Any] = field(default_factory=dict)
    timeout: float | None = None
    retry: int | None = None
    auth: Any | None = None  # arrest.auth types or httpx auth
    follow_redirects: bool | None = None

    def merge(self, overrides: "ArrestConfig | None") -> "ArrestConfig":
        """Return a new config with *overrides* layered on top of *self*."""
        if overrides is None:
            return self
        return ArrestConfig(
            headers=self.headers | overrides.headers,
            cookies=self.cookies | overrides.cookies,
            params=self.params | overrides.params,
            timeout=overrides.timeout
            if overrides.timeout is not None
            else self.timeout,
            retry=overrides.retry if overrides.retry is not None else self.retry,
            auth=overrides.auth if overrides.auth is not None else self.auth,
            follow_redirects=(
                overrides.follow_redirects
                if overrides.follow_redirects is not None
                else self.follow_redirects
            ),
        )
