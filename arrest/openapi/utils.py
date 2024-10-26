import re
from typing import Any

from pydantic.alias_generators import to_pascal

from arrest.openapi.spec import Reference


def get_ref_schema(reference: Reference | Any) -> str | None:
    if ref := getattr(reference, "ref", None):
        return ref.split("/")[-1]


def is_pascal(name: str) -> bool:
    return re.match(r"^[A-Z][A-Za-z]*$", name) is not None


def convert_to_pascal(name: str | None):
    if not name:
        return None

    if is_pascal(name):
        return name

    return to_pascal(name)
