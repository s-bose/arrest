import re
from typing import Mapping, ClassVar, TypeVar, Generic

# Match parameters in URL paths, eg. '{param}', and '{param:int}'
PARAM_REGEX = re.compile("{([a-zA-Z_][a-zA-Z0-9_]*)(:[a-zA-Z_][a-zA-Z0-9_]*)?}")

T = TypeVar("T")


class BaseConverter(Generic[T]):
    regex: ClassVar[str] = ""

    def convert(self, value: str) -> T:
        raise NotImplementedError

    def to_string(self, value: T) -> str:
        raise NotImplementedError


class StringConverter(BaseConverter[str]):
    regex = "[^/]+"

    def convert(self, value: str) -> str:
        return value

    def to_string(self, value: str) -> str:
        value = str(value)
        if "/" in value:
            raise ValueError("Cannot contain / in param")

        if not value:
            raise ValueError("Must not be empty")
        return value


class IntegerConvertor(BaseConverter[int]):
    regex = "[0-9]+"

    def convert(self, value: str) -> int:
        return int(value)

    def to_string(self, value: int) -> str:
        value = int(value)
        assert value >= 0, "Negative integers are not supported"
        return str(value)


CONVERTER_REGEX: Mapping[str, str] = {
    "str": "[^/]+",
    "int": "[0-9]+",
    "float": r"[0-9]+(\.[0-9]+)?",
}
