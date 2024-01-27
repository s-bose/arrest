import re
from typing import Any

from arrest.openapi.spec import Reference


def get_ref_schema(reference: Reference | Any) -> str | None:
    if ref := getattr(reference, "ref", None):
        return ref.split("/")[-1]


def sanitize_name(name: str) -> str:
    name = name.lower().replace(" ", "_")
    return re.sub("[^A-Za-z0-9]+", "_", name)
