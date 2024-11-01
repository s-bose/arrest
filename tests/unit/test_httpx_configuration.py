import httpx
import pytest
import respx

from arrest import Resource, Service


@pytest.mark.parametrize(
    "service_args, resource_args",
    [
        ({}, {"headers": {"abc": "123"}, "cookies": {"x-cookie": 60}}),
        ({"headers": {"abc": "123"}, "cookies": {"x-cookie": 60}}, {}),
        ({"headers": {"abc": "123"}}, {"cookies": {"x-cookie": 60}}),
    ],
)
def test_httpx_client_kwargs(service: Service, service_args: dict, resource_args: dict):
    service.add_resource(Resource(name="abc", route="/abc", **resource_args), **service_args)

    assert service.abc._httpx_args["headers"] == {"abc": "123"}
    assert service.abc._httpx_args["cookies"] == {"x-cookie": 60}


@pytest.mark.asyncio
async def test_custom_httpx_client(service: Service):
    router = respx.Router()
    router.get("http://example.com/abc/").mock(
        return_value=httpx.Response(status_code=200, json={"status": "OK"})
    )

    mock_transport = httpx.MockTransport(router.async_handler)
    client = httpx.AsyncClient(transport=mock_transport, base_url="http://example.com")
    resource = Resource(route="/abc", handlers=[("GET", "/")])
    service.add_resource(resource, client=client)

    assert resource._client

    resp = await service.abc.get("/")
    assert resp
    await client.aclose()
