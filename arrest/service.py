import itertools
from functools import partial
from typing import Any, Optional

import httpx
from typing_extensions import Unpack

from arrest._config import ArrestConfig, HttpxClientInputs
from arrest.defaults import ROOT_RESOURCE
from arrest.exceptions import ResourceNotFound
from arrest.http import Methods
from arrest.resource import Resource
from arrest.types import ExceptionHandlers
from arrest.utils import extract_resource_and_suffix


class Service:
    def __init__(
        self,
        name: str,
        url: str,
        description: Optional[str] = None,
        resources: Optional[list[Resource]] = [],
        client: Optional[httpx.AsyncClient] = None,
        exception_handlers: ExceptionHandlers = None,
        retry: Optional[int] = None,
        config: Optional[ArrestConfig] = None,
        **kwargs: Unpack[HttpxClientInputs],
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
            retry:
                Optional argument to specify the number of retries across all resources
            kwargs:
                Additional httpx.AsyncClient parameters. [see more](api.md/#httpx-client-arguments)
        """
        self.name = name
        self.url = url
        self.description = description
        self.resources: dict[str, Resource] = {}

        self._exception_handlers: ExceptionHandlers = {} if exception_handlers is None else exception_handlers

        for resource in resources:
            self.add_resource(resource, client=client, retry=retry, **kwargs)

        self.get = partial(self.request, method=Methods.GET)
        self.post = partial(self.request, method=Methods.POST)
        self.put = partial(self.request, method=Methods.PUT)
        self.patch = partial(self.request, method=Methods.PATCH)
        self.delete = partial(self.request, method=Methods.DELETE)
        self.head = partial(self.request, method=Methods.HEAD)
        self.options = partial(self.request, method=Methods.OPTIONS)

    def add_resource(
        self,
        resource: Resource,
        client: Optional[httpx.AsyncClient] = None,
        retry: Optional[int] = None,
        **kwargs: Unpack[HttpxClientInputs],
    ) -> None:
        """
        Add a new resource to the service

        Parameters:
            resource:
                The new resource instance
        """
        resource.base_url = self.url
        resource.initialize_handlers(base_url=self.url)
        resource.initialize_httpx(client=client, **kwargs)
        resource.exception_handlers = self._exception_handlers
        resource.retry = retry

        self.resources[resource.name] = resource
        setattr(self, resource.name, resource)

    async def request(self, path: str, method: Methods, **kwargs):
        """
        Helper function to make a request directly
        from the service level

        Note:
            If you provide `path` as an empty string or `/`, this would
            try to find a root resource definition, if any


        Parameters:
            path:
                Requested path needs to have the following syntax:
                `/{resource_route}/{handler_route}`
            method:
                Requested HTTP Method
        """

        resource, suffix = extract_resource_and_suffix(path=path)
        if len(resource) == 0:
            resource = ROOT_RESOURCE
        if resource not in self.resources:
            raise ResourceNotFound(message=f"resource {resource} not found")
        return await self.resources[resource].request(path=suffix, method=method, **kwargs)

    def __getattr__(self, key: str) -> Resource | Any:  # pragma: no cover
        if hasattr(self, key):
            return getattr(self, key)
        return self.resources[key]

    def __dir__(self):  # pragma: no cover
        return list(itertools.chain(dir(super()), self.resources))

    def add_exception_handlers(self, exc_handlers: ExceptionHandlers):
        self._exception_handlers |= exc_handlers
