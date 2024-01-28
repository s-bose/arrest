import pytest
from unittest.mock import MagicMock
from arrest.openapi.parser import OpenAPIGenerator
from arrest.openapi.service_template import ServiceSchema
from arrest.openapi.spec import OpenAPI, Info, PathItem, Operation, Server, Reference


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
    generator = OpenAPIGenerator(openapi_path=MagicMock(), output_path=MagicMock())

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


def test_generate_resources():
    generator = OpenAPIGenerator(openapi_path=MagicMock(), output_path=MagicMock())

    openapi = OpenAPI(
        info=Info(title="api", version="0.1"),
        paths={
            "/user": PathItem(get=Operation(responses={"200": Reference(ref="#/components/schemas/User")}))
        },
    )

    resources = list(generator._build_arrest_resources(openapi=openapi))
    assert len(resources) == 1
