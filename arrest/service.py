from typing import Optional, NoReturn
from functools import partial

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

    def __getitem__(self, resource_name: str) -> Optional[Resource]:
        return self.resources.get(resource_name, None)

    def add_resource(self, resource: Resource) -> NoReturn:
        resource.base_url = self.url
        resource.add_handlers(handlers=resource.handlers)
        self.resources[resource.name] = resource

    async def request(self, path: str, method: Methods, **kwargs):
        parts = path.strip("/").split("/")
        resource, suffix = parts[0], "/".join(parts[1:])
        if resource not in self.resources:
            raise NotFoundException(message=f"resource {resource} not found")
        return await self.resources[resource].request(
            url=suffix, method=method, **kwargs
        )
