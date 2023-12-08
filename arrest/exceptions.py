class BaseException(Exception):
    """base exception class"""


class ArrestError(BaseException):
    """used in error situations"""

    def __init__(self, *args: object) -> None:
        super().__init__(*args)


class ArrestHTTPException(ArrestError):
    def __init__(self, status_code: int, data: dict | str) -> None:
        self.status_code = status_code
        self.data = data


class NotFoundException(ArrestError):
    def __init__(self, message: str):
        self.message = message


class HandlerNotFound(NotFoundException):
    def __init__(self, message: str):
        super().__init__(message)


class ResourceNotFound(NotFoundException):
    def __init__(self, message: str):
        super().__init__(message)


class ConversionError(ArrestError):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)
