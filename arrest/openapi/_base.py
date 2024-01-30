from functools import cached_property, lru_cache
from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader, Template
from pydantic import BaseModel

from arrest._config import PYDANTIC_V2
from arrest.openapi._config import TEMPLATE_DIR


@lru_cache()
def get_template(template_filepath: Path) -> Template:
    template_dir = Path(__file__).parents[0] / TEMPLATE_DIR
    loader = FileSystemLoader(str(template_dir / template_filepath.parent))
    environment = Environment(loader=loader)
    return environment.get_template(template_filepath.name)


class TemplateBase:
    def __init__(
        self, *, source: str, params: Optional[BaseModel] = None, destination_path: Path | str
    ) -> None:
        self.source = Path(source)
        self.params = params
        self.destination_path = destination_path

    @cached_property
    def template(self):
        return get_template(template_filepath=self.source)

    def render(self) -> str:
        if self.params:
            kwargs: dict = self.params.model_dump() if PYDANTIC_V2 else self.params.dict()
            return self.template.render(**kwargs)
        else:
            return self.template.render()

    def render_and_save(self) -> None:
        content = self.render()
        output_filename = f"{self.source.stem}.py"
        with open(Path(self.destination_path / output_filename), "w", encoding="utf-8") as file:
            file.write(content)
