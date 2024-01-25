from pathlib import Path
from arrest.common import StrEnum

TEMPLATE_DIR = "templates"


class Format(StrEnum):
    json = "json"
    yaml = "yaml"
