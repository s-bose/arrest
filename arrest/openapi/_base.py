from pathlib import Path
from functools import lru_cache, cached_property

from pydantic import BaseModel
from jinja2 import FileSystemLoader, Environment, Template
from arrest.openapi._config import TEMPLATE_DIR
from arrest._config import PYDANTIC_V2


@lru_cache()
def get_template(template_filepath: Path) -> Template:
    template_dir = Path(__file__).parents[0] / TEMPLATE_DIR
    loader = FileSystemLoader(str(template_dir / template_filepath.parent))
    environment = Environment(loader=loader)
    return environment.get_template(template_filepath.name)


class TemplateBase:
    def __init__(self, source: str, params: BaseModel, destination_path: Path | str) -> None:
        self.source = Path(source)
        self.params = params
        self.destination_path = destination_path

    @cached_property
    def template(self):
        return get_template(template_filepath=self.source)

    def render(self):
        kwargs: dict = self.params.model_dump() if PYDANTIC_V2 else self.params.dict()
        content = self.template.render(**kwargs)
        output_filename = f"{self.source.stem}.py"
        with open(Path(self.destination_path / output_filename), "w", encoding="utf-8") as file:
            file.write(content)
