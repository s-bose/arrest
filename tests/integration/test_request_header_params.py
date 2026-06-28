import httpx
import pytest
import respx
from pydantic import BaseModel, ConfigDict
from respx.patterns import M

from arrest._config import ArrestConfig
from arrest.http import Methods
from arrest.params import Body, Header
from arrest.resource import Resource
from arrest.service import Service


@pytest.mark.parametrize(
    "resource_header, kwarg_header, expected_result",
    [
        (
            {"x-resource-header": "123"},
            None,
            {
                "x-max-age": "20",
                "x-user-agent": "mozila",
                "x-resource-header": "123",
            },
        ),
        (
            None,
            {"x-kwarg-header": "abc"},
            {
                "x-max-age": "20",
                "x-user-agent": "mozila",
                "x-kwarg-header": "abc",
            },
        ),
        (
            {"x-resource-header": "123"},
            {"x-kwarg-header": "abc"},
            {
                "x-max-age": "20",
                "x-user-agent": "mozila",
                "x-kwarg-header": "abc",
                "x-resource-header": "123",
            },
        ),
    ],
)
@pytest.mark.asyncio
async def test_request_header_params(
    service, mock_httpx, resource_header, kwarg_header, expected_result
):
    patterns = [
        M(url__regex="/user/*", method__in=["POST"]),
    ]

    mock_httpx.route(*patterns, name="http_request").mock(
        return_value=httpx.Response(200, json={"status": "OK"})
    )

    class UserRequest(BaseModel):
        model_config = ConfigDict(populate_by_name=True)
        x_max_age: str = Header(serialization_alias="x-max-age")  # type: ignore
        x_user_agent: str = Header(serialization_alias="x-user-agent")  # type: ignore

        name: str = Body(...)
        email: str
        password: str

    service.add_resource(
        Resource(
            route="/user",
            handlers=[
                (Methods.POST, "/profile", UserRequest),
            ],
            config=ArrestConfig(headers=resource_header) if resource_header else None,
        )
    )
    await service.user.post(
        "/profile",
        request=UserRequest(
            name="bob",
            email="bob@mail.com",
            password="xyz",
            x_max_age="20",
            x_user_agent="mozila",
        ),
        headers=kwarg_header,
    )

    req: httpx.Request = mock_httpx["http_request"].calls[0].request
    headers = req.headers

    for key, value in expected_result.items():
        assert key in headers
        assert headers[key] == value


@pytest.mark.asyncio
async def test_request_header_params_arguments(service, mock_httpx):
    mock_httpx.route(
        url__regex="/user/*", name="http_request", method__in=["GET", "POST"]
    ).mock(return_value=httpx.Response(200, json={"status": "OK"}))

    service.add_resource(
        Resource(
            route="/user",
            handlers=[
                (Methods.GET, "/profile"),
            ],
        )
    )

    await service.user.get("/profile", headers={"x-header": "123"})
    request: httpx.Request = mock_httpx["http_request"].calls[0].request

    request_headers = httpx.Headers(request.headers)
    assert request_headers["x-header"] == "123"


@pytest.mark.asyncio
async def test_header_params_in_both_request_model_and_arguments(service, mock_httpx):
    patterns = [
        M(url__regex="/user/*", method__in=["GET"]),
    ]

    mock_httpx.route(*patterns, name="http_request").mock(
        return_value=httpx.Response(200, json={"status": "OK"})
    )

    class UserRequest(BaseModel):
        model_config = ConfigDict(populate_by_name=True)
        x_user_agent: str = Header(serialization_alias="x-user-agent")  # type: ignore

        name: str
        email: str
        password: str

    service.add_resource(
        Resource(
            route="/user",
            handlers=[
                (Methods.GET, "/profile", UserRequest),
            ],
        )
    )

    await service.user.get(
        "/profile",
        request=UserRequest(
            x_user_agent="mozila", name="abc", email="abc@email.com", password="123"
        ),
        headers={"x-header": "123"},
    )

    request: httpx.Request = mock_httpx["http_request"].calls[0].request

    request_headers = httpx.Headers(request.headers)
    assert request_headers["x-header"] == "123"
    assert request_headers["x-user-agent"] == "mozila"


@pytest.mark.asyncio
async def test_config_headers_merged_when_not_in_model(service, mock_httpx):
    """Config-level headers that don't overlap with model headers get added."""
    service.add_resource(
        Resource(
            route="/user",
            handlers=[(Methods.GET, "/", None, None)],
            config=ArrestConfig(headers={"x-default": "config-val"}),
        )
    )
    mock_httpx.get(url__regex="/user/*", name="http_request").mock(
        return_value=httpx.Response(200, json={"status": "OK"})
    )
    await service.user.get("/", headers={"x-call": "call-val"})

    request = mock_httpx["http_request"].calls[0].request
    assert request.headers["x-default"] == "config-val"
    assert request.headers["x-call"] == "call-val"


@pytest.mark.asyncio
async def test_three_level_merge_via_request():
    """Service → resource → per-call: per-call wins, dicts merge additively."""

    url = "http://api.example.com"
    with respx.mock(base_url=url) as mock:
        mock.get(url="/items/").mock(
            return_value=httpx.Response(200, json={"ok": True})
        )

        svc = Service(
            name="test",
            url=url,
            config=ArrestConfig(
                headers={"svc": "1", "shared": "svc"},
                timeout=10.0,
            ),
        )
        svc.add_resource(
            Resource(
                route="/items",
                handlers=[("GET", "/")],
                config=ArrestConfig(
                    headers={"res": "2", "shared": "res"},
                    timeout=20.0,
                ),
            )
        )

        resp = await svc.items.request(
            method=Methods.GET,
            path="/",
            headers={"call": "3", "shared": "call"},
            timeout=30.0,
        )

        assert resp.is_success

        req = mock.calls[0].request
        assert req.headers["svc"] == "1"
        assert req.headers["res"] == "2"
        assert req.headers["call"] == "3"
        assert req.headers["shared"] == "call"
