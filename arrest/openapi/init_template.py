from pathlib import Path
from typing import ClassVar

from arrest.openapi._base import TemplateBase


class InitTemplate(TemplateBase):
    TEMPLATE_FILEPATH: ClassVar[str] = "__init__.jinja2"

    def __init__(self, *, destination_path: Path | str) -> None:
        super().__init__(source=self.TEMPLATE_FILEPATH, destination_path=destination_path)
