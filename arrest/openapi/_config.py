from pathlib import Path
from arrest.common import StrEnum

TEMPLATE_DIR = Path("openapi/templates")


class Format(StrEnum):
    json = "json"
    yaml = "yaml"
