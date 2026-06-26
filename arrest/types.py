from typing import Any, Callable, Mapping, Optional

ExceptionHandler = Callable[[Exception], Any]
ExceptionHandlers = Optional[Mapping[type[Exception], ExceptionHandler]]
