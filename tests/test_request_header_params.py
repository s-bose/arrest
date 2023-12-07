import httpx
import pytest
from pydantic import BaseModel
from respx.patterns import M

from arrest.http import Methods
from arrest.params import Body, Header, Query
from arrest.resource import Resource


@pytest.mark.asyncio
async def test_request_header_params(service, mock_httpx, mocker):
    patterns = [
        M(url__regex="/user/*", method__in=["POST"]),
    ]

    mock_httpx.route(*patterns, name="http_request").mock(
        return_value=httpx.Response(200, json={"status": "OK"})
    )

    class UserRequest(BaseModel):
        limit: int = Query()
        x_max_age: str = Header(...)
        x_user_agent: str = Header(...)
        name: str = Body(...)
        email: str
        password: str

    service.add_resource(
        Resource(
            route="/user",
            handlers=[
                (Methods.POST, "/profile", UserRequest),
            ],
        )
    )

    get_matching_handler = mocker.spy(service.user, "get_matching_handler")
    extract_request_params = mocker.spy(service.user, "extract_request_params")
    await service.user.post(
        "/profile",
        request=UserRequest(
            limit=1,
            name="bob",
            email="bob@mail.com",
            password="xyz",
            x_max_age="20",
            x_user_agent="mozila",
        ),
    )
    handler, _ = get_matching_handler.spy_return
    assert handler.route == "/profile"
    params = extract_request_params.spy_return
    assert params.query == httpx.QueryParams({"limit": 1})
    assert params.header == httpx.Headers(
        {
            "x_max_age": "20",
            "x_user_agent": "mozila",
            "Content-Type": "application/json",
        }
    )
    assert params.body == {
        "name": "bob",
        "email": "bob@mail.com",
        "password": "xyz",
    }
