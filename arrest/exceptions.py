from typing import Any


class BaseException(Exception):
    """base exception class"""


class ArrestError(BaseException):
    """used in error situations"""

    def __init__(self, *args: object) -> None:
        super().__init__(*args)


class ArrestHTTPException(ArrestError):
    def __init__(self, status_code: int, data: Any) -> None:
        self.status_code = status_code
        self.data = data
        super().__init__(str(data))


class RequestError(ArrestError):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class ResponseError(ArrestError):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class NotFoundException(ArrestError):
    def __init__(self, message: str):
        self.message = message


class HandlerNotFound(NotFoundException):
    def __init__(self, message: str):
        super().__init__(message)


class ConversionError(ArrestError):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)
