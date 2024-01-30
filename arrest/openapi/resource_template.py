from pathlib import Path
from typing import ClassVar, Optional

from pydantic import BaseModel

from arrest.openapi._base import TemplateBase


class HandlerSchema(BaseModel):
    route: str
    method: str
    request: Optional[str] = None
    response: Optional[str] = None


class ResourceSchema(BaseModel):
    name: str
    route: str
    handlers: list[HandlerSchema]


class ResourceParams(BaseModel):
    schema_module: str
    schema_imports: set[str]
    resources: list[ResourceSchema]


class ResourceTemplate(TemplateBase):
    TEMPLATE_FILEPATH: ClassVar[str] = "resources.jinja2"

    def __init__(
        self, schema_module: str, resources: list[ResourceSchema], destination_path: Path | str
    ) -> None:
        schema_imports = set()
        for resource in resources:
            for handler in resource.handlers:
                schema_imports.update((handler.request, handler.response))

        schema_imports = {imp for imp in schema_imports if imp is not None}

        super().__init__(
            source=self.TEMPLATE_FILEPATH,
            params=ResourceParams(
                schema_module=schema_module, schema_imports=schema_imports, resources=resources
            ),
            destination_path=destination_path,
        )
