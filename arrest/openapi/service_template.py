from pathlib import Path
from typing import ClassVar, Optional

from pydantic import BaseModel

from arrest.openapi._base import TemplateBase


class ServiceSchema(BaseModel):
    service_id: str
    name: str
    url: str
    description: Optional[str] = None
    resources: list[str]


class ServiceParams(BaseModel):
    resource_imports: set[str]
    services: list[ServiceSchema]


class ServiceTemplate(TemplateBase):
    TEMPLATE_FILEPATH: ClassVar[str] = "services.jinja2"

    def __init__(self, services: list[ServiceSchema], destination_path: Path | str) -> None:
        resource_imports = set()
        for service in services:
            resource_imports.update(service.resources)

        super().__init__(
            source=self.TEMPLATE_FILEPATH,
            params=ServiceParams(resource_imports=resource_imports, services=services),
            destination_path=destination_path,
        )
