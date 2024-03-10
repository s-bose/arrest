import httpx
import pytest

from arrest.resource import Resource
from arrest.service import Service
from tests import TEST_DEFAULT_SERVICE_URL


def test_service_add_resource():
    user_resource = Resource(
        name="user",
        route="/users",
        handlers=[("GET", "/"), ("POST", "/"), ("GET", "/{user_id:uuid}")],
    )
    service = Service(name="myservice", url="http://www.example.com", resources=[user_resource])

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


@pytest.mark.asyncio
async def test_make_request_to_root_resource(mock_httpx, mocker):
    root_resource = Resource(route="", handlers=[("GET", ""), ("GET", "/")])
    user_resource = Resource(route="/users", handlers=[("GET", "")])

    service = Service(
        name="myservice",
        url=TEST_DEFAULT_SERVICE_URL,
        resources=[root_resource, user_resource],
    )

    mock_httpx.get(url__regex=".*", name="http_request").mock(
        return_value=httpx.Response(200, json={"status": "OK"})
    )

    root__get = mocker.spy(root_resource, "request")
    user__get = mocker.spy(user_resource, "request")

    resp1 = await service.get("")

    assert root__get.call_count == 1

    resp2 = await service.get("/users")

    assert user__get.call_count == 1

    resp3 = await service.get("/")

    assert root__get.call_count == 2

    resp4 = await service.root.get("")

    assert root__get.call_count == 3

    assert resp1 == resp2 == resp3 == resp4 == {"status": "OK"}
