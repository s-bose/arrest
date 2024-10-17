from typing import Any

from arrest.openapi.spec import Reference


def get_ref_schema(reference: Reference | Any) -> str | None:
    if ref := getattr(reference, "ref", None):
        return ref.split("/")[-1]
