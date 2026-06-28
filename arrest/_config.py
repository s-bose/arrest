import ssl
from dataclasses import dataclass, field, fields
from typing import Any, Callable, Mapping

from httpx import AsyncBaseTransport, AsyncClient, Limits, _types


@dataclass(frozen=True, kw_only=True)
class ArrestConfig:
    """Per-request defaults that merge through the hierarchy chain.

    Priority (highest to lowest):
        per-call kwargs  >  handler config  >  resource config  >  service config

    Dict fields (``headers``, ``cookies``, ``params``) merge additively.
    All other fields, including httpx client inputs and ``client``, are
    overridden by the highest-priority non-``None`` value.
    """

    headers: dict[str, str] = field(default_factory=dict)
    cookies: dict[str, Any] = field(default_factory=dict)
    params: dict[str, Any] = field(default_factory=dict)
    timeout: float | None = None
    auth: Any | None = None
    follow_redirects: bool | None = None
    raise_for_status: bool | None = None
    client: AsyncClient | None = None
    verify: ssl.SSLContext | bool | str | None = None
    cert: _types.CertTypes | None = None
    http2: bool | None = None
    proxy: _types.ProxyTypes | None = None
    mounts: Mapping[str, AsyncBaseTransport] | None = None
    limits: Limits | None = None
    transport: AsyncBaseTransport | None = None
    trust_env: bool | None = None
    event_hooks: Mapping[str, list[Callable[..., Any]]] | None = None
    default_encoding: str | Callable[[bytes], str] | None = None

    max_retries: int | None = field(default=None, metadata={"internal": True})

    def httpx_args(self) -> dict[str, Any]:
        """Return only fields valid as ``httpx.AsyncClient`` / request kwargs.

        Excludes arrest-internal fields (``max_retries``) and user-facing
        flags that are not httpx constructor args (``client``, ``raise_for_status``).
        """
        internal_fields = {
            f.name
            for f in fields(self)
            if f.metadata.get("internal") or f.name in {"client", "raise_for_status"}
        }
        return {
            f.name: getattr(self, f.name)
            for f in fields(self)
            if f.name not in internal_fields and getattr(self, f.name) is not None
        }

    def merge(self, overrides: "ArrestConfig | None") -> "ArrestConfig":
        """Return a new config with *overrides* layered on top of *self*."""
        if overrides is None:
            return self

        merged: dict[str, Any] = {}
        for config_field in fields(self):
            field_name = config_field.name
            self_value = getattr(self, field_name)
            override_value = getattr(overrides, field_name)

            if field_name in {"headers", "cookies", "params"}:
                merged[field_name] = self_value | override_value
            else:
                merged[field_name] = (
                    override_value if override_value is not None else self_value
                )

        return ArrestConfig(**merged)
