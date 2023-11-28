import pytest
import httpx

from arrest.service import Service
from arrest.resource import Resource


def test_service_add_resource():
    user_resource = Resource(
        name="user",
        route="/users",
        handlers=[("GET", "/"), ("POST", "/"), ("GET", "/{user_id:uuid}")],
    )
    service = Service(
        name="myservice", url="http://www.example.com", resources=[user_resource]
    )

    service.add_resource(
        Resource(
            route="/organizations",
            handlers=[("GET", "/"), ("GET", "/{org_uuid:uuid}")],
        )
    )

    assert "user" in service.resources
    assert "organizations" in service.resources


@pytest.mark.asyncio
async def test_make_request_from_service(service, mock_httpx):
    service.add_resource(Resource(route="/user", handlers=[("GET", "/posts")]))
    mock_httpx.get(url__regex="/user/*", name="http_request").mock(
        return_value=httpx.Response(200, json={"status": "OK"})
    )

    response = await service.request("/user/posts", method="GET")
    resource_response = await service.user.get("/posts")
    assert response == resource_response == {"status": "OK"}
