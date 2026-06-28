import itertools
from typing import Optional


from arrest._config import ArrestConfig
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
        exception_handlers: ExceptionHandlers | None = None,
        config: Optional[ArrestConfig] = None,
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
            exception_handlers:
                A dictionary of exception handlers for the service
            config:
                A dictionary of configuration options for the service

        """
        self.name = name
        self.url = url
        self.description = description
        self.resources: dict[str, Resource] = {}

        self.config = config

        self._exception_handlers = (
            {} if exception_handlers is None else exception_handlers
        )

        if resources:
            for resource in resources:
                self.add_resource(resource)

    def add_resource(
        self,
        resource: Resource,
    ) -> None:
        """
        Add a new resource to the service.  Config fields passed here
        override the Service-level defaults for this resource only.
        """
        resource.base_url = self.url
        resource.initialize_handlers(base_url=self.url)

        # Merge: service defaults → resource's own config → add_resource overrides
        resource.config = (
            self.config.merge(resource.config) if self.config else resource.config
        )

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
