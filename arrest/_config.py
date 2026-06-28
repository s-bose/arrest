import ssl
from dataclasses import asdict, dataclass, field, fields
from typing import Any, Callable, Mapping, TypedDict

from httpx import AsyncBaseTransport, Limits, _types


class HttpxClientInputs(TypedDict, total=False):
    """Transport-level fields passed to ``httpx.AsyncClient`` at creation time.

    These do **not** merge through the Service → Resource → handler chain.
    For per-request defaults (headers, cookies, timeout, etc.) see :class:`ArrestConfig`.
    """

    verify: ssl.SSLContext | bool | str
    cert: _types.CertTypes | None
    http2: bool
    proxy: _types.ProxyTypes | None
    mounts: Mapping[str, AsyncBaseTransport] | None
    limits: Limits
    transport: AsyncBaseTransport | None
    trust_env: bool
    event_hooks: Mapping[str, list[Callable[..., Any]]] | None
    default_encoding: str | Callable[[bytes], str]


@dataclass
class ArrestConfig:
    """Per-request defaults that merge through the hierarchy chain.

    Priority (highest to lowest):
        per-call kwargs  >  handler config  >  resource config  >  service config

    Dict fields (``headers``, ``cookies``, ``params``) merge additively.
    Scalar fields (``timeout``, ``max_retries``, ``auth``, ``follow_redirects``)
    are overridden by the highest-priority non-``None`` value.
    """

    headers: dict[str, str] = field(default_factory=dict)
    cookies: dict[str, Any] = field(default_factory=dict)
    params: dict[str, Any] = field(default_factory=dict)
    timeout: float | None = None
    auth: Any | None = None
    follow_redirects: bool | None = None
    max_retries: int | None = field(default=None, metadata={"internal": True})
    raise_for_status: bool | None = field(default=None)

    def httpx_args(self) -> dict[str, Any]:
        """Return only fields valid as ``httpx.AsyncClient`` / request kwargs.

        Excludes arrest-internal fields (``max_retries``).
        """
        internal_fields = {f.name for f in fields(self) if f.metadata.get("internal")}
        return {
            k: v
            for k, v in asdict(self).items()
            if k not in internal_fields and v is not None
        }

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
            max_retries=(
                overrides.max_retries
                if overrides.max_retries is not None
                else self.max_retries
            ),
            auth=overrides.auth if overrides.auth is not None else self.auth,
            follow_redirects=(
                overrides.follow_redirects
                if overrides.follow_redirects is not None
                else self.follow_redirects
            ),
            raise_for_status=(
                overrides.raise_for_status
                if overrides.raise_for_status is not None
                else self.raise_for_status
            ),
        )
