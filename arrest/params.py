from enum import Enum
from typing import Any

import httpx
from pydantic.fields import FieldInfo

try:  # pragma: no cover
    from pydantic_core import PydanticUndefined
except ImportError:
    from pydantic.fields import Undefined as PydanticUndefined
from typing_extensions import Unpack


class ParamTypes(Enum):
    query = "query"
    header = "header"
    body = "Body"


class Param(FieldInfo):
    _param_type: ParamTypes

    def __init__(self, default: Any = PydanticUndefined, **kwargs: Unpack[Any]) -> None:
        kwargs = dict(default=default, **kwargs)
        super().__init__(**kwargs)


class Query(Param):
    _param_type = ParamTypes.query

    def __init__(self, default: Any = PydanticUndefined, **kwargs: Unpack[Any]) -> None:
        super().__init__(default, **kwargs)


class Header(Param):
    _param_type = ParamTypes.header

    def __init__(self, default: Any = PydanticUndefined, **kwargs: Unpack[Any]) -> None:
        super().__init__(default, **kwargs)


class Body(Param):
    _param_type = ParamTypes.body

    def __init__(self, default: Any = PydanticUndefined, **kwargs: Unpack[Any]) -> None:
        super().__init__(default, **kwargs)


class Params:
    def __init__(self, *, header: httpx.Headers, query: httpx.QueryParams, body: Any) -> None:
        self.header = header
        self.query = query
        self.body = body
