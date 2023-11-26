import enum


class StrEnum(str, enum.Enum):
    def __repr__(self) -> str:
        return self.value

    def __str__(self) -> str:
        return self.__repr__()


class Methods(StrEnum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"


class ContentType(StrEnum):
    APPLICATION_JSON = "application/json"
