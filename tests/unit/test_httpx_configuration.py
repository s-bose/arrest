import httpx
import pytest
import respx

from arrest import Resource, Service


@pytest.mark.parametrize(
    "svc_config, res_config",
    [
        ({}, {"headers": {"abc": "123"}, "cookies": {"x-cookie": 60}}),
        ({"headers": {"abc": "123"}, "cookies": {"x-cookie": 60}}, {}),
        ({"headers": {"abc": "123"}}, {"cookies": {"x-cookie": 60}}),
    ],
)
def test_config_headers_cookies(svc_config: dict, res_config: dict):
    from arrest._config import ArrestConfig

    svc = Service(
        name="test",
        url="http://example.com",
        config=ArrestConfig(**svc_config),
    )
    svc.add_resource(
        Resource(name="abc", route="/abc", config=ArrestConfig(**res_config))
    )

    assert svc.abc.config.headers == {"abc": "123"}
    assert svc.abc.config.cookies == {"x-cookie": 60}


@pytest.mark.asyncio
async def test_custom_httpx_client():
    from arrest._config import ArrestConfig

    router = respx.Router()
    router.get("http://example.com/abc/").mock(
        return_value=httpx.Response(status_code=200, json={"status": "OK"})
    )

    mock_transport = httpx.MockTransport(router.async_handler)
    client = httpx.AsyncClient(transport=mock_transport, base_url="http://example.com")
    resource = Resource(
        route="/abc",
        handlers=[("GET", "/")],
        config=ArrestConfig(client=client),
    )
    svc = Service(name="test", url="http://example.com")
    svc.add_resource(resource)

    assert svc.abc.config.client is client

    resp = await svc.abc.get("/")
    assert resp
    await client.aclose()


@pytest.mark.asyncio
async def test_service_config_client_is_used_for_requests():
    from arrest._config import ArrestConfig

    router = respx.Router()
    router.get("http://example.com/abc/").mock(
        return_value=httpx.Response(status_code=200, json={"status": "OK"})
    )

    client = httpx.AsyncClient(
        transport=httpx.MockTransport(router.async_handler),
        base_url="http://example.com",
    )
    service = Service(
        name="test",
        url="http://example.com",
        config=ArrestConfig(client=client),
    )
    service.add_resource(Resource(route="/abc", handlers=[("GET", "/")]))

    resp = await service.abc.get("/")

    assert resp
    await client.aclose()


@pytest.mark.asyncio
async def test_resource_client_passed_in_init():
    """Resource with explicit config.client sets it on the merged config."""
    from arrest._config import ArrestConfig

    client = httpx.AsyncClient()
    resource = Resource(
        route="/abc",
        handlers=[("GET", "/")],
        config=ArrestConfig(client=client),
    )
    assert resource.config.client is client
    await client.aclose()


@pytest.mark.asyncio
async def test_config_follow_redirects_and_auth():
    """Config with follow_redirects and auth sets request kwargs."""
    from arrest._config import ArrestConfig

    url = "https://api.example.com"
    with respx.mock(base_url=url) as mock:
        svc = Service(
            name="test",
            url=url,
            config=ArrestConfig(follow_redirects=False, auth=("user", "pass")),
        )
        mock.get(url="/items/").mock(return_value=httpx.Response(200, json={}))
        svc.add_resource(Resource(route="/items", handlers=[("GET", "/")]))
        await svc.items.get("/")
        assert mock.calls[0].request.extensions.get("follow_redirects") is None


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


@pytest.mark.asyncio
async def test_arrest_config_merge_additional_fields():
    """merge() preserves and overrides the httpx/client fields too."""
    from arrest._config import ArrestConfig

    client = httpx.AsyncClient()
    transport = httpx.MockTransport(lambda request: httpx.Response(200))
    cfg = ArrestConfig(
        verify=False,
        http2=False,
        proxy="http://proxy.example.com",
        mounts={"https://": transport},
        limits=httpx.Limits(max_connections=10),
        transport=transport,
        trust_env=False,
        event_hooks={"request": []},
        default_encoding="utf-8",
        client=client,
    )
    overrides = ArrestConfig(
        verify=True,
        http2=True,
        trust_env=True,
        default_encoding="latin-1",
    )

    merged = cfg.merge(overrides)

    assert merged.verify is True
    assert merged.http2 is True
    assert merged.proxy == "http://proxy.example.com"
    assert merged.mounts == {"https://": transport}
    assert merged.limits == httpx.Limits(max_connections=10)
    assert merged.transport is transport
    assert merged.trust_env is True
    assert merged.event_hooks == {"request": []}
    assert merged.default_encoding == "latin-1"
    assert merged.client is client

    await client.aclose()


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
    assert "client" not in result
    assert "auth" not in result


@pytest.mark.parametrize(
    "svc_client, res_client, expected",
    [
        pytest.param(
            httpx.AsyncClient(),
            None,
            "svc",
            id="service-only",
        ),
        pytest.param(
            None,
            httpx.AsyncClient(),
            "res",
            id="resource-only",
        ),
        pytest.param(
            httpx.AsyncClient(),
            httpx.AsyncClient(),
            "res",
            id="resource-overrides-service",
        ),
        pytest.param(
            None,
            None,
            None,
            id="no-client",
        ),
    ],
)
def test_client_instance_identity(svc_client, res_client, expected):
    """Client instances pass through the config merge chain as the same object."""
    from arrest._config import ArrestConfig

    clients = {"svc": svc_client, "res": res_client}

    svc = Service(
        name="test",
        url="http://example.com",
        config=ArrestConfig(client=svc_client) if svc_client else None,
    )
    resource = Resource(
        route="/items",
        handlers=[("GET", "/")],
        config=ArrestConfig(client=res_client) if res_client else None,
    )
    svc.add_resource(resource)

    merged_config = svc.items.config
    merged_client = merged_config.client if merged_config else None

    if expected is None:
        assert merged_client is None
    else:
        expected_client = clients[expected]
        assert merged_client is expected_client
        assert merged_client is expected_client  # same object, not a copy
