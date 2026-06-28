import itertools
from typing import Any, Optional

import httpx
from typing_extensions import Unpack

from arrest._config import ArrestConfig, HttpxClientInputs
from arrest.resource import Resource
from arrest.types import ExceptionHandlers


class Service:
    def __init__(
        self,
        name: str,
        url: str,
        *,
        description: Optional[str] = None,
        resources: Optional[list[Resource]] = None,
        client: Optional[httpx.AsyncClient] = None,
        exception_handlers: ExceptionHandlers | None = None,
        # config: per-request defaults (merge through the chain)
        headers: Optional[dict[str, str]] = None,
        cookies: Optional[dict[str, Any]] = None,
        params: Optional[dict[str, Any]] = None,
        timeout: Optional[float] = None,
        max_retries: Optional[int] = None,
        auth: Any = None,
        follow_redirects: Optional[bool] = None,
        # ── transport: passed once to httpx.AsyncClient ─────────────────
        **client_kwargs: Unpack[HttpxClientInputs],
    ) -> None:
        """
        A python class to define a service.
        Contains a base url for the main HTTP service.
        Resources can be added to a service.

        Parameters:
            name:
                Name of the service
            url:
                Base url of the service
            resources:
                A list of resources provided by the service
            client:
                An httpx.AsyncClient instance
            max_retries:
                Maximum number of application-level retries managed
                by tenacity. If you want to to transport-level retry,
                check out [docs](whats-new.md#use-the-standard-retry-mechanism-from-httpx-transport)
            headers / cookies / params:
                Default request headers / cookies / query params for every resource.
                Merged additively; per-resource/handler/call values append.
            timeout:
                Default request timeout (seconds).
            auth:
                Default authentication.
            follow_redirects:
                Whether to follow redirects by default.
            client_kwargs:
                Transport-level httpx.AsyncClient parameters.
                [see more](api.md#httpx-client-arguments)
        """
        self.name = name
        self.url = url
        self.description = description
        self.resources: dict[str, Resource] = {}

        self.config = ArrestConfig(
            headers=headers or {},
            cookies=cookies or {},
            params=params or {},
            timeout=timeout,
            max_retries=max_retries,
            auth=auth,
            follow_redirects=follow_redirects,
        )

        self._exception_handlers = (
            {} if exception_handlers is None else exception_handlers
        )

        if resources:
            for resource in resources:
                self.add_resource(resource, client=client, **client_kwargs)

    def add_resource(
        self,
        resource: Resource,
        client: Optional[httpx.AsyncClient] = None,
        # ── config overrides ────────────────────────────────────────────
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
        Add a new resource to the service.  Config fields passed here
        override the Service-level defaults for this resource only.
        """
        resource.base_url = self.url
        resource.initialize_handlers(base_url=self.url)

        # Merge: service defaults → resource's own config → add_resource overrides
        resource.config = self.config.merge(resource.config).merge(
            ArrestConfig(
                headers=headers or {},
                cookies=cookies or {},
                params=params or {},
                timeout=timeout,
                max_retries=max_retries,
                auth=auth,
                follow_redirects=follow_redirects,
            )
        )

        if client and not resource._client:
            resource._client = client
        if client_kwargs:
            resource._transport_kwargs = {  # type: ignore[assignment]
                **resource._transport_kwargs,
                **client_kwargs,
            }

        resource.exception_handlers = self._exception_handlers

        self.resources[resource.name] = resource
        setattr(self, resource.name, resource)

    def __getattr__(self, key: str) -> Resource:  # pragma: no cover
        if hasattr(self, key):
            return getattr(self, key)
        return self.resources[key]

    def __dir__(self):  # pragma: no cover
        return list(itertools.chain(dir(super()), self.resources))

    def add_exception_handlers(self, exc_handlers: ExceptionHandlers):
        self._exception_handlers |= exc_handlers
