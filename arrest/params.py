from enum import Enum
from typing import Any, Callable, Optional
from typing_extensions import Unpack
from pydantic.fields import _FieldInfoInputs, FieldInfo


class ParamTypes(Enum):
    query = "query"
    header = "header"
    path = "path"


class Param(FieldInfo):
    _param_type: ParamTypes
    # def __init__(
    #     self,
    #     annotation: type[Any] | None,
    #     default: Any,
    #     default_factory: Callable[[], Any] | None = None,
    #     alias: Optional[str] = None,
    #     alias_priority: int | None = None,
    #     validation_alias: str | None = None,
    #     serialization_alias: str | None
    #     title: str | None
    #     description: str | None
    #     examples: list[Any] | None
    #     exclude: bool | None
    #     include: bool | None
    #     discriminator: str | None
    #     json_schema_extra: dict[str, Any] | None
    #     frozen: bool | None
    #     validate_default: bool | None
    #     repr: bool
    #     init_var: bool | None
    #     kw_only: bool | None
    # ) -> None:
    #     super().__init__(**kwargs)

    def __init__(self, **kwargs: Unpack[_FieldInfoInputs]) -> None:
        super().__init__(**kwargs)


class Query(Param):
    _param_type = ParamTypes.query


class Path(Param):
    _param_type = ParamTypes.path


class Header(Param):
    _param_type = ParamTypes.header
