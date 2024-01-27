from typing import Any

import pytest

from arrest.openapi.spec import Reference
from arrest.openapi.utils import get_ref_schema, sanitize_name


@pytest.mark.parametrize(
    "ref, expected_name",
    [
        (Reference(ref="#/components/schemas/Pet"), "Pet"),
        (Reference(ref="#/components/schemas/UserResponse"), "UserResponse"),
        (Reference(ref="#/components/requestBodies/Pet"), "Pet"),
        ({"xyz": "abc"}, None),
    ],
)
def test_get_ref_schema(ref: Any, expected_name: str):
    assert get_ref_schema(ref) == expected_name


@pytest.mark.parametrize(
    "name, sanitized", [("Swagger Petstore - OpenAPI 3.0", "swagger_petstore_openapi_3_0")]
)
def test_sanitize_name(name: str, sanitized: str):
    assert sanitize_name(name) == sanitized
