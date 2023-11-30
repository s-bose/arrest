class BaseException(Exception):
    """base exception class"""


class ArrestError(BaseException):
    """used in error situations"""


class ArrestHTTPException(BaseException):
    def __init__(self, status_code: int, data: dict | str) -> None:
        self.status_code = status_code
        self.data = data


class NotFoundException(BaseException):
    def __init__(self, message: str):
        self.message = message


class HandlerNotFound(NotFoundException):
    pass
