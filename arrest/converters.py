"""
https://github.com/encode/starlette/blob/master/starlette/routing.py
"""

import math
import re
import uuid
from typing import Any, ClassVar, Generic, Mapping, Pattern, TypeVar
from uuid import UUID

from arrest.exceptions import ConversionError

T = TypeVar("T")

# Match parameters in URL paths, eg. '{param}', and '{param:int}'
PARAM_REGEX = re.compile("{([a-zA-Z_][a-zA-Z0-9_]*)(:[a-zA-Z_][a-zA-Z0-9_]*)?}")


class Converter(Generic[T]):
    regex: ClassVar[str] = ""

    def to_str(self, value: T) -> str:
        raise NotImplementedError()


class IntegerConverter(Converter[int]):
    regex = "[0-9]+"

    def to_str(self, value: Any | int) -> str:
        value = int(value)

        assert value >= 0, "Negative integers are not supported"
        return str(value)


class FloatConverter(Converter[float]):
    regex = r"[0-9]+(\.[0-9]+)?"

    def to_str(self, value: Any | float) -> str:
        value = float(value)

        assert value >= 0.0, "Negative floats are not supported"
        assert not math.isnan(value), "NaN values are not supported"
        assert not math.isinf(value), "Infinite values are not supported"
        return ("%0.20f" % value).rstrip("0").rstrip(".")


class StrConverter(Converter[str]):
    regex = "[^/]+"

    def to_str(self, value: Any | str) -> str:
        value = str(value)

        assert "/" not in value, "May not contain path separators"
        assert value, "Must not be empty"
        return value


class UUIDConverter(Converter[uuid.UUID]):
    regex = "[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"

    def to_str(self, value: Any | UUID) -> str:
        value = UUID(str(value))
        return str(value)


CONVERTER_REGEX: Mapping[str, Converter[Any]] = {
    "str": StrConverter(),
    "int": IntegerConverter(),
    "float": FloatConverter(),
    "uuid": UUIDConverter(),
}


def compile_path(path: str) -> tuple[Pattern[str], str, dict[str, type]]:
    """
    Given a path string, like: "/{username:str}",


    Returns
    -------

    regex : "/(?P<username>[^/]+)"
    format : "/{username}"
    param_types : dict[username: Converter[str]()]
    """
    path_regex = "^"
    path_format = ""

    idx = 0
    parsed_path_params: dict[str, type] = {}

    for match in PARAM_REGEX.finditer(path):
        param_name, converter_type = match.groups("str")
        converter_type = converter_type.lstrip(":").casefold()

        assert (
            converter_type in CONVERTER_REGEX
        ), f"Invalid converter specified, available converters {CONVERTER_REGEX.keys()}"

        converter = CONVERTER_REGEX[converter_type]

        path_regex += re.escape(path[idx : match.start()])
        path_regex += f"(?P<{param_name}>{converter.regex})"

        path_format += path[idx : match.start()]
        path_format += "{%s}" % param_name

        if param_name in parsed_path_params:
            raise ValueError(f"Duplicate param {param_name} at path {path}")
        parsed_path_params[param_name] = converter

        idx = match.end()

    path_regex += re.escape(path[idx:]) + "$"
    path_format += path[idx:]

    pattern = re.compile(path_regex)
    return pattern, path_format, parsed_path_params


def replace_params(
    path: str,
    path_params: dict[str, Any],
    param_types: dict[str, Converter[Any]] | None,
) -> tuple[str, dict[str, str]]:
    for key, value in list(path_params.items()):
        try:
            if "{" + key + "}" in path:
                if not param_types:
                    strval = str(value)
                else:
                    strval = param_types[key].to_str(value)
                path = path.replace("{" + key + "}", strval)
                path_params.pop(key)
        except (TypeError, ValueError) as exc:
            raise ConversionError(*exc.args) from exc

    return path, path_params


def get_converter(key: str) -> Converter[Any]:
    return CONVERTER_REGEX[key]


def add_converter(converter: Converter[Any], key: str) -> None:
    CONVERTER_REGEX[key] = converter
