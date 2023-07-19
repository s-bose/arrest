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
        self.name = name
        self.url = url
        self.resources = []
        for resource in resources:
            self.add_resource(resource)

    def __dir__(self) -> Iterable[str]:
        return super().__dir__() + [res.name for res in self.resources]

    def add_resource(self, resource: Resource) -> NoReturn:
        setattr(self, resource.name, resource)
        resource.base_url = self.url
        self.resources.append(resource)
