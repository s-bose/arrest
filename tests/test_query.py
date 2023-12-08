import httpx
import pytest
from pydantic import BaseModel
from respx.patterns import M

from arrest.http import Methods
from arrest.params import Query
from arrest.resource import Resource


@pytest.mark.asyncio
async def test_query_params(service, mock_httpx, mocker):
    patterns = [
        M(url__regex="/user/*", method__in=["GET"]),
    ]

    mock_httpx.route(*patterns, name="http_request").mock(
        return_value=httpx.Response(200, json={"status": "OK"})
    )

    service.add_resource(
        Resource(
            route="/user",
            handlers=[
                (Methods.GET, "/profile"),
            ],
        )
    )

    extract_request_params = mocker.spy(service.user, "extract_request_params")
    await service.user.get("/profile", query={"limit": 2, "value": "xyz"})

    params = extract_request_params.spy_return
    assert params.query == httpx.QueryParams({"limit": 2, "value": "xyz"})


@pytest.mark.asyncio
async def test_query_params_in_request(service, mock_httpx, mocker):
    patterns = [
        M(url__regex="/user/*", method__in=["GET"]),
    ]

    mock_httpx.route(*patterns, name="http_request").mock(
        return_value=httpx.Response(200, json={"status": "OK"})
    )

    class UserRequest(BaseModel):
        limit: int = Query(...)
        name: str
        email: str
        password: str

    service.add_resource(
        Resource(
            route="/user",
            handlers=[
                (Methods.GET, "/profile"),
            ],
        )
    )

    extract_request_params = mocker.spy(service.user, "extract_request_params")
    await service.user.get(
        "/profile",
        request=UserRequest(limit=2, name="abc", email="abc@email.com", password="123"),
        query={"value": "xyz"},
    )

    params = extract_request_params.spy_return
    assert params.query == httpx.QueryParams({"limit": 2, "value": "xyz"})
