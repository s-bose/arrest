from typing import Any, Callable

ExceptionHandler = Callable[[Exception], Any]
ExceptionHandlers = dict[type[Exception], ExceptionHandler]
