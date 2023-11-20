import enum


class Methods(str, enum.Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"

    def __str__(self):
        return self.value

    def __repr__(self) -> str:
        return self.__str__()


class ContentType(str, enum.Enum):
    APPLICATION_JSON = "application/json"
