"""
https://github.com/encode/starlette/blob/master/starlette/routing.py
"""

import re
import uuid
import enum
from typing import Mapping, Pattern

# Match parameters in URL paths, eg. '{param}', and '{param:int}'
PARAM_REGEX = re.compile("{([a-zA-Z_][a-zA-Z0-9_]*)(:[a-zA-Z_][a-zA-Z0-9_]*)?}")


class PythonTypes(str, enum.Enum):
    str = "str"
    int = "int"
    float = "float"
    uuid = "uuid"


TYPES: Mapping[PythonTypes, type] = {
    PythonTypes.str: str,
    PythonTypes.int: int,
    PythonTypes.float: float,
    PythonTypes.uuid: uuid.UUID,
}


CONVERTER_REGEX: Mapping[PythonTypes, str] = {
    PythonTypes.str: "[^/]+",
    PythonTypes.int: "[0-9]+",
    PythonTypes.float: r"[0-9]+(\.[0-9]+)?",
    PythonTypes.uuid: "[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
}


def compile_path(path: str) -> tuple[Pattern[str], str, dict[str, type]]:
    """
    Given a path string, like: "/{username:str}",


    Returns
    -------

    regex : "/(?P<username>[^/]+)"
    format : "/{username}"
    path_params : dict[username: type<str>]
    """
    path_regex = "^"
    path_format = ""

    idx = 0
    parsed_path_params: dict[str, type] = {}

    for match in PARAM_REGEX.finditer(path):
        param_name, converter_type = match.groups("str")
        converter_type = converter_type.lstrip(":")

        assert (
            converter_type in CONVERTER_REGEX
        ), f"Invalid converter specified, available converters {CONVERTER_REGEX.keys()}"

        converter_regex = CONVERTER_REGEX[converter_type]

        path_regex += re.escape(path[idx : match.start()])
        path_regex += f"(?P<{param_name}>{converter_regex})"

        path_format += path[idx : match.start()]
        path_format += "{%s}" % param_name

        if param_name in parsed_path_params:
            raise ValueError(f"Duplicate param {param_name} at path {path}")
        parsed_path_params[param_name] = TYPES[converter_type]

        idx = match.end()

    path_regex += re.escape(path[idx:]) + "$"
    path_format += path[idx:]

    pattern = re.compile(path_regex)
    return pattern, path_format, parsed_path_params
