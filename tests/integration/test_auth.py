import base64

import httpx
import pytest
import respx

from arrest import Resource, Service
from arrest._config import ArrestConfig


@pytest.mark.asyncio
async def test_basic_auth_tuple():
    """Auth as a (username, password) tuple sets Authorization header."""
    url = "http://api.example.com"
    with respx.mock(base_url=url) as mock:
        mock.get(url="/items/").mock(
            return_value=httpx.Response(200, json={"ok": True})
        )

        svc = Service(
            name="test",
            url=url,
            config=ArrestConfig(auth=("alice", "s3cret")),
        )
        svc.add_resource(
            Resource(route="/items", handlers=[("GET", "/")]),
        )

        resp = await svc.items.get("/")
        assert resp.is_success

        req = mock.calls[0].request
        assert req.headers["authorization"].startswith("Basic ")


@pytest.mark.asyncio
async def test_basic_auth_httpx_class():
    """Auth as httpx.BasicAuth sets Authorization header."""
    url = "http://api.example.com"
    with respx.mock(base_url=url) as mock:
        mock.get(url="/items/").mock(
            return_value=httpx.Response(200, json={"ok": True})
        )

        svc = Service(
            name="test",
            url=url,
            config=ArrestConfig(auth=httpx.BasicAuth("alice", "s3cret")),
        )
        svc.add_resource(
            Resource(route="/items", handlers=[("GET", "/")]),
        )

        resp = await svc.items.get("/")
        assert resp.is_success

        req = mock.calls[0].request
        assert req.headers["authorization"].startswith("Basic ")


@pytest.mark.asyncio
async def test_auth_at_resource_level():
    """Auth set on Resource overrides Service-level auth."""
    url = "http://api.example.com"
    with respx.mock(base_url=url) as mock:
        mock.get(url="/items/").mock(
            return_value=httpx.Response(200, json={"ok": True})
        )

        svc = Service(
            name="test",
            url=url,
            config=ArrestConfig(auth=("svc-user", "svc-pass")),
        )
        svc.add_resource(
            Resource(
                route="/items",
                handlers=[("GET", "/")],
                config=ArrestConfig(auth=("res-user", "res-pass")),
            ),
        )

        resp = await svc.items.get("/")
        assert resp.is_success

        req = mock.calls[0].request
        expected = base64.b64encode(b"res-user:res-pass").decode()
        assert req.headers["authorization"] == f"Basic {expected}"


@pytest.mark.asyncio
async def test_no_auth_when_not_set():
    """No Authorization header when auth is not configured."""
    url = "http://api.example.com"
    with respx.mock(base_url=url) as mock:
        mock.get(url="/items/").mock(
            return_value=httpx.Response(200, json={"ok": True})
        )

        svc = Service(name="test", url=url)
        svc.add_resource(
            Resource(route="/items", handlers=[("GET", "/")]),
        )

        resp = await svc.items.get("/")
        assert resp.is_success

        req = mock.calls[0].request
        assert "authorization" not in req.headers


@pytest.mark.asyncio
async def test_auth_resource_level_flows_to_request():
    """Resource-level auth is sent on the HTTP request."""
    url = "http://api.example.com"
    with respx.mock(base_url=url) as mock:
        mock.post(url="/items/").mock(
            return_value=httpx.Response(200, json={"ok": True})
        )

        svc = Service(name="test", url=url)
        svc.add_resource(
            Resource(
                route="/items",
                handlers=[("POST", "/")],
                config=ArrestConfig(auth=("alice", "s3cret")),
            ),
        )

        resp = await svc.items.post("/")
        assert resp.is_success

        req = mock.calls[0].request
        assert req.headers["authorization"].startswith("Basic ")


@pytest.mark.asyncio
async def test_bearer_token_auth():
    """Custom Bearer token auth"""

    url = "http://api.example.com"
    VALID_TOKEN = "tok-12345"

    class BearerAuth(httpx.Auth):
        def __init__(self, token: str):
            self.token = token

        def auth_flow(self, request):
            request.headers["Authorization"] = f"Bearer {self.token}"
            yield request

    with respx.mock(base_url=url) as mock:

        def auth_side_effect(request: httpx.Request) -> httpx.Response:
            auth_header = request.headers.get("Authorization", "")
            if auth_header == f"Bearer {VALID_TOKEN}":
                return httpx.Response(200, json={"data": "secret"})
            return httpx.Response(401, json={"detail": "Invalid token"})

        mock.get(url="/items/").mock(side_effect=auth_side_effect)

        svc = Service(
            name="test",
            url=url,
            config=ArrestConfig(auth=BearerAuth(VALID_TOKEN)),
        )
        svc.add_resource(
            Resource(route="/items", handlers=[("GET", "/")]),
        )

        # Happy path — correct token
        resp = await svc.items.get("/")
        assert resp.is_success
        assert resp.data == {"data": "secret"}

        # Bad path — switch to wrong token
        svc_bad = Service(
            name="test-bad",
            url=url,
            config=ArrestConfig(auth=BearerAuth("wrong-token")),
        )
        svc_bad.add_resource(
            Resource(route="/items", handlers=[("GET", "/")]),
        )

        resp = await svc_bad.items.get("/")
        assert resp.is_client_error
        assert resp.status_code == 401
        assert resp.data == {"detail": "Invalid token"}
