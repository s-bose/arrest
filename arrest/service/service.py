from collections.abc import Iterable
from typing import Optional, NoReturn

from arrest.resource.resource import Resource


class Service:
    def __init__(
        self,
        name: str,
        url: str,
        resources: Optional[list[Resource]] = [],
    ) -> None:
        if url.endswith("/"):
            raise ValueError("url should not have a trailing `/`")
        self.name = name
        self.url = url
        self.resources: dict[str, Resource] = {}
        for resource in resources:
            self.add_resource(resource)

    def __getitem__(self, resource_name: str) -> Optional[Resource]:
        return self.resources.get(resource_name, None)

    def add_resource(self, resource: Resource) -> NoReturn:
        resource.base_url = self.url
        resource.add_handlers(resource.handlers)
        self.resources[resource.name] = resource
