from enum import Enum
from pydantic.fields import FieldInfo

class ParamTypes(Enum):
    query = "query"
    header = "header"
    path = "path"

class Param(FieldInfo):
