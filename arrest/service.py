import itertools
from functools import partial
from typing import Any, Optional

from arrest.exceptions import ResourceNotFound
from arrest.http import Methods
from arrest.resource import Resource


class Service:
    def __init__(
        self,
        name: str,
        url: str,
        resources: Optional[list[Resource]] = [],
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
        """

        self.name = name
        self.url = url
        self.resources: dict[str, Resource] = {}
        for resource in resources:
            self.add_resource(resource)

        self.get = partial(self.request, method=Methods.GET)
        self.post = partial(self.request, method=Methods.POST)
        self.put = partial(self.request, method=Methods.PUT)
        self.patch = partial(self.request, method=Methods.PATCH)
        self.delete = partial(self.request, method=Methods.DELETE)

    def add_resource(self, resource: Resource) -> None:
        """
        Add a new resource to the service

        Parameters:
            resource:
                The new resource instance
        """
        resource.base_url = self.url
        resource.initialize_handlers(base_url=self.url)
        self.resources[resource.name] = resource
        setattr(self, resource.name, resource)

    async def request(self, path: str, method: Methods, **kwargs):
        """
        Helper function to make a request directly
        from the service level

        Parameters:
            path:
                Requested path needs to have the following syntax:
                `/{resource_route}/{handler_route}`
            method:
                Requested HTTP Method
        """
        parts = path.strip("/").split("/")
        resource, suffix = parts[0], "/".join(parts[1:])

        if resource not in self.resources:
            raise ResourceNotFound(message=f"resource {resource} not found")
        return await self.resources[resource].request(path=f"/{suffix}", method=method, **kwargs)

    def __getattr__(self, key: str) -> Resource | Any:  # pragma: no cover
        if hasattr(self, key):
            return getattr(self, key)
        return self.resources[key]

    def __dir__(self):  # pragma: no cover
        return list(itertools.chain(dir(super()), self.resources))
