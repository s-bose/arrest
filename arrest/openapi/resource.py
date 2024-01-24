from pathlib import Path
from pydantic import BaseModel

from arrest.resource import Resource
from arrest.openapi._base import TemplateBase


class Params(BaseModel):
    schema: str
    schema_imports: list[str]
    resources: list[Resource]


TEMPLATE_FILEPATH = "resources.jinja2"


class ResourceTemplate(TemplateBase):
    def __init__(self, params: Params, destination_path: Path | str) -> None:
        super().__init__(TEMPLATE_FILEPATH, params, destination_path)

    def render(self):
        self.params.resources
