import json
from pathlib import Path

from arrest.openapi.spec import OpenAPI

FIXTURE_PATH = "tests/fixtures"

# TODO - find a better way to test the correctness of the schema


def test_validate_openapi_v3():
    with open(Path(FIXTURE_PATH) / "openapi_petstore.json", "r") as file:
        data = json.load(file)

    openapi = OpenAPI(**data)
    assert openapi

    assert len(openapi.servers) == 1
    server = openapi.servers[0]
    assert server.url == "/api/v3"
    assert set(openapi.paths.keys()) == {
        "/pet",
        "/pet/findByStatus",
        "/pet/findByTags",
        "/pet/{petId}",
        "/pet/{petId}/uploadImage",
        "/store/inventory",
        "/store/order",
        "/store/order/{orderId}",
        "/user",
        "/user/createWithList",
        "/user/login",
        "/user/logout",
        "/user/{username}",
    }


def test_validate_openapi_v3_1():
    with open(Path(FIXTURE_PATH) / "openapi_petstore_3.1.json", "r") as file:
        data = json.load(file)

    openapi = OpenAPI(**data)
    assert openapi

    assert len(openapi.servers) == 1
    server = openapi.servers[0]
    assert server.url == "http://petstore.swagger.io/v1"
    assert set(openapi.paths.keys()) == {
        "/pets",
        "/pets/{petId}",
    }
