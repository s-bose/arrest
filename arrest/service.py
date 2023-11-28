from typing import Optional, NoReturn, Any
from functools import partial
import itertools

from arrest.http import Methods
from arrest.resource import Resource
from arrest.exceptions import NotFoundException


class Service:
    def __init__(
        self,
        name: str,
        url: str,
        resources: Optional[list[Resource]] = [],
    ) -> None:
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
        resource.base_url = self.url
        resource.initialize_handlers(base_url=self.url)
        self.resources[resource.name] = resource
        setattr(self, resource.name, resource)

    async def request(self, path: str, method: Methods, **kwargs):
        parts = path.strip("/").split("/")
        resource, suffix = parts[0], "/".join(parts[1:])

        if resource not in self.resources:
            raise NotFoundException(message=f"resource {resource} not found")
        return await self.resources[resource].request(
            url=f"/{suffix}", method=method, **kwargs
        )

    def __getattr__(self, key: str) -> Resource | Any:  # pragma: no cover
        if hasattr(self, key):
            return getattr(self, key)
        return self.resources[key]

    def __dir__(self):  # pragma: no cover
        return list(itertools.chain(dir(super()), self.resources))
