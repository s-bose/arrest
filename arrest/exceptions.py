class BaseException(Exception):
    """base exception class"""


class MethodNotAllowed(Exception):
    pass


class ArrestHTTPException(Exception):
    def __init__(self, status_code: int, data: dict | str) -> None:
        self.status_code = status_code
        self.data = data
