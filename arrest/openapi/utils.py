from typing import Any
import os
import importlib
from functools import lru_cache

from arrest.openapi.spec import Reference


def get_ref_schema(reference: Reference | Any) -> str | None:
    if ref := getattr(reference, "ref", None):
        return ref.split("/")[-1]


@lru_cache()
def inspect_module(module_path: str) -> Any:
    path, _ = os.path.splitext(module_path)
    filename = path.split("/")[-1]
    module = importlib.import_module(filename, path)
    return module
