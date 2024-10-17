from typing import Any, Callable, Mapping, TypeAlias, TypeVar

ET = TypeVar("ET", bound=Exception)
ExceptionHandler: TypeAlias = Callable[[ET], Any]
ExceptionHandlers: TypeAlias = Mapping[ET, ExceptionHandler]
