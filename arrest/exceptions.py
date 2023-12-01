class BaseException(Exception):
    """base exception class"""


class ArrestError(BaseException):
    """used in error situations"""


class ArrestHTTPException(ArrestError):
    def __init__(self, status_code: int, data: dict | str) -> None:
        self.status_code = status_code
        self.data = data


class NotFoundException(ArrestError):
    def __init__(self, message: str):
        self.message = message


class HandlerNotFound(ArrestError):
    pass
