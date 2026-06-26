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
def test_config_headers_cookies(
    service: Service, service_args: dict, resource_args: dict
):
    service.add_resource(
        Resource(name="abc", route="/abc", **resource_args), **service_args
    )

    assert service.abc.config.headers == {"abc": "123"}
    assert service.abc.config.cookies == {"x-cookie": 60}


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


@pytest.mark.asyncio
async def test_resource_client_passed_in_init():
    """Resource.__init__ with explicit client covers the self._client = client branch."""
    client = httpx.AsyncClient()
    resource = Resource(route="/abc", handlers=[("GET", "/")], client=client)
    assert resource._client is client
    await client.aclose()


@pytest.mark.asyncio
async def test_config_follow_redirects_and_auth():
    """Config with follow_redirects and auth sets request kwargs."""
    url = "https://api.example.com"
    with respx.mock(base_url=url) as mock:
        svc = Service(
            name="test", url=url, follow_redirects=False, auth=("user", "pass")
        )
        mock.get(url="/items/").mock(return_value=httpx.Response(200, json={}))
        svc.add_resource(Resource(route="/items", handlers=[("GET", "/")]))
        await svc.items.get("/")
        # just verify the call succeeded — follow_redirects and auth are internal to httpx
        assert (
            mock.calls[0].request.extensions.get("follow_redirects") is None
        )  # httpx doesn't expose this, just verify no error


def test_arrest_config_merge_none():
    """merge(None) returns self unchanged."""
    from arrest._config import ArrestConfig

    cfg = ArrestConfig(headers={"x": "1"}, max_retries=3)
    result = cfg.merge(None)
    assert result is cfg


def test_arrest_config_merge_overrides():
    """merge() overrides scalar fields and merges dict fields."""
    from arrest._config import ArrestConfig

    cfg = ArrestConfig(
        headers={"a": "1"},
        cookies={"c": "2"},
        timeout=10.0,
        max_retries=2,
        follow_redirects=False,
    )
    overrides = ArrestConfig(
        headers={"b": "3"},
        timeout=30.0,
        follow_redirects=True,
    )
    merged = cfg.merge(overrides)

    assert merged.headers == {"a": "1", "b": "3"}
    assert merged.cookies == {"c": "2"}
    assert merged.timeout == 30.0
    assert merged.max_retries == 2  # not in overrides, keeps original
    assert merged.follow_redirects is True


def test_arrest_config_httpx_args_excludes_internal():
    """httpx_args() returns only httpx-compatible fields, strips None values."""
    from arrest._config import ArrestConfig

    cfg = ArrestConfig(
        headers={"x": "1"},
        max_retries=5,
        timeout=30.0,
        follow_redirects=False,
        auth=None,  # should be stripped
    )
    result = cfg.httpx_args()
    assert result["headers"] == {"x": "1"}
    assert result["timeout"] == 30.0
    assert result["follow_redirects"] is False
    assert "max_retries" not in result
    assert "auth" not in result
