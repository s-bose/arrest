from enum import Enum
from typing import Any
from typing_extensions import Unpack
from pydantic.fields import _FieldInfoInputs, FieldInfo
from pydantic_core import PydanticUndefined


class ParamTypes(Enum):
    query = "query"
    header = "header"
    body = "Body"


class Param(FieldInfo):
    _param_type: ParamTypes

    def __init__(
        self, default: Any = PydanticUndefined, **kwargs: Unpack[_FieldInfoInputs]
    ) -> None:
        kwargs = dict(default=default, **kwargs)
        super().__init__(**kwargs)


class Query(Param):
    _param_type = ParamTypes.query


class Header(Param):
    _param_type = ParamTypes.header


class Body(Param):
    _param_type = ParamTypes.body
