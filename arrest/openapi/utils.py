from typing import Any

from openapi_pydantic import Reference


def get_ref_schema(reference: Reference | Any) -> str | None:
    if isinstance(reference, Reference):
        return reference.ref.split("/")[-1]
