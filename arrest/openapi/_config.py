# pragma: no cover

from arrest.common import StrEnum

TEMPLATE_DIR = "templates"


class Format(StrEnum):
    json = "json"
    yaml = "yaml"
    yml = "yml"
