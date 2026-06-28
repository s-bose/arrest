from enum import Enum
from typing import Any

import httpx
from pydantic.fields import FieldInfo


class ParamTypes(Enum):
    query = "query"
    header = "header"
    body = "Body"
    form = "form"
    file = "file"


class _Param(FieldInfo):  # type: ignore[misc]
    _param_type: ParamTypes

    def __init__(self, default: Any = None, **kwargs: Any) -> None:
        kwargs = dict(default=default, **kwargs)
        super().__init__(**kwargs)


class _Query(_Param):
    _param_type = ParamTypes.query

    def __init__(self, default: Any = None, **kwargs: Any) -> None:
        super().__init__(default, **kwargs)


class _Header(_Param):
    _param_type = ParamTypes.header

    def __init__(self, default: Any = None, **kwargs: Any) -> None:
        super().__init__(default, **kwargs)


class _Body(_Param):
    _param_type = ParamTypes.body

    def __init__(self, default: Any = None, **kwargs: Any) -> None:
        super().__init__(default, **kwargs)


class _Form(_Param):
    _param_type = ParamTypes.form

    def __init__(self, default: Any = None, **kwargs: Any) -> None:
        super().__init__(default, **kwargs)


class _File(_Param):
    _param_type = ParamTypes.file

    def __init__(self, default: Any = None, **kwargs: Any) -> None:
        super().__init__(default, **kwargs)


class RequestArgs:
    def __init__(
        self,
        *,
        header: httpx.Headers,
        query: httpx.QueryParams,
        body: Any,
        files: Any | None = None,
        content_type: str | None = None,
    ) -> None:
        self.header = header
        self.query = query
        self.body = body
        self.files = files
        self.content_type = content_type


# Public API


def Param(default: Any = None, **kwargs: Any) -> Any:
    return _Param(default, **kwargs)


def Query(default: Any = None, **kwargs: Any) -> Any:
    return _Query(default, **kwargs)


def Header(default: Any = None, **kwargs: Any) -> Any:
    return _Header(default, **kwargs)


def Body(default: Any = None, **kwargs: Any) -> Any:
    return _Body(default, **kwargs)


def Form(default: Any = None, **kwargs: Any) -> Any:
    return _Form(default, **kwargs)


def File(default: Any = None, **kwargs: Any) -> Any:
    return _File(default, **kwargs)
