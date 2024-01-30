from unittest.mock import MagicMock

import pytest

from arrest.openapi.parser import OpenAPIGenerator
from arrest.openapi.spec import (
    Info,
    MediaType,
    OpenAPI,
    Operation,
    PathItem,
    Reference,
    RequestBody,
    Response,
    Server,
)


@pytest.mark.parametrize(
    "servers, service_ids, urls",
    [
        (
            [
                {
                    "url": "http://example.com",
                }
            ],
            {"api"},
            {"http://example.com"},
        ),
        (
            [
                {
                    "url": "http://example.com/user/{username}/auth/{authId}/permission/{permissionId}",
                    "variables": {
                        "username": {"default": "bob"},
                        "authId": {"enum": ["ABC123", "XYZ123"], "default": "ABC123"},
                        "permissionId": {"enum": ["ADMIN", "USER"], "default": "ADMIN"},
                    },
                }
            ],
            {"api", "api_1", "api_2", "api_3"},
            {
                "http://example.com/user/bob/auth/ABC123/permission/ADMIN",
                "http://example.com/user/bob/auth/ABC123/permission/USER",
                "http://example.com/user/bob/auth/XYZ123/permission/ADMIN",
                "http://example.com/user/bob/auth/XYZ123/permission/USER",
            },
        ),
    ],
)
def test_generate_services(servers, service_ids, urls):
    generator = OpenAPIGenerator(url=MagicMock(), output_path=MagicMock())

    openapi = OpenAPI(
        info=Info(title="api", version="0.1"),
        servers=[Server(**server) for server in servers],
        paths={"/user": PathItem(get=Operation())},
    )

    gen_services = list(generator._build_arrest_service(openapi, resources=[]))
    assert len(gen_services) == len(service_ids)

    gen_service_ids = set([svc.service_id for svc in gen_services])
    gen_urls = set([svc.url for svc in gen_services])

    assert gen_service_ids == service_ids
    assert gen_urls == urls

    for service in gen_services:
        assert service.name == "api"
        assert service.resources == []


@pytest.mark.parametrize(
    "responses, request_body, parsed_request, parsed_response",
    [
        ({"200": Reference(ref="#/components/schemas/User")}, None, None, "User"),
        (
            {
                "200": Response(
                    content={"application/json": MediaType(schema=Reference(ref="#/components/schemas/User"))}
                )
            },
            None,
            None,
            "User",
        ),
        (
            {
                "200": Response(
                    content={
                        "application/json": MediaType(
                            schema={"type": "array", "items": {"$ref": "#/components/schemas/Pet"}}
                        )
                    }
                )
            },
            None,
            None,
            None,
        ),
        ({"400": Reference(ref="#/components/schemas/User")}, None, None, None),
        (
            {
                "200": Response(
                    content={
                        "application/xml": MediaType(
                            schema={"type": "array", "items": {"$ref": "#/components/schemas/Pet"}}
                        )
                    }
                )
            },
            None,
            None,
            None,
        ),
        (
            None,
            Reference(ref="#/components/schemas/User"),
            "User",
            None,
        ),
        (
            None,
            RequestBody(
                content={"application/json": MediaType(schema=Reference(ref="#/components/schemas/User"))}
            ),
            "User",
            None,
        ),
        (
            None,
            RequestBody(
                content={"application/json": MediaType(schema=Reference(ref="#/components/schemas/User"))}
            ),
            "User",
            None,
        ),
        (
            None,
            RequestBody(
                content={
                    "application/json": MediaType(
                        schema={"type": "array", "items": {"$ref": "#/components/schemas/Pet"}}
                    )
                }
            ),
            None,
            None,
        ),
        (
            {"200": Reference(ref="#/components/schemas/UserResponse")},
            Reference(ref="#/components/schemas/UserRequest"),
            "UserRequest",
            "UserResponse",
        ),
    ],
)
def test_generate_resources(responses, request_body, parsed_request, parsed_response):
    generator = OpenAPIGenerator(url=MagicMock(), output_path=MagicMock())

    openapi = OpenAPI(
        info=Info(title="api", version="0.1"),
        paths={"/user/items": PathItem(get=Operation(responses=responses, requestBody=request_body))},
    )

    resources = list(generator._build_arrest_resources(openapi=openapi))
    assert len(resources) == 1

    assert len(resources[0].handlers) == 1
    handler = resources[0].handlers[0]

    assert handler.method == "GET"
    assert handler.route == "/items"
    assert handler.request == parsed_request
    assert handler.response == parsed_response
