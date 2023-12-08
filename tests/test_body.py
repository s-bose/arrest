import httpx
import pytest
from pydantic import BaseModel
from respx.patterns import M

from arrest.http import Methods
from arrest.resource import Resource


class UserRequest(BaseModel):
    a: int
    b: str
    c: str


@pytest.mark.parametrize(
    "request_body, parsed_body",
    [
        (
            {"name": "username", "email": "user@email.com"},
            {"name": "username", "email": "user@email.com"},
        ),
        (
            [
                {"id": 0, "name": "username", "email": "user@email.com"},
                {"id": 1, "name": "username", "email": "user@email.com"},
                {"id": 2, "name": "username", "email": "user@email.com"},
            ],
            [
                {"id": 0, "name": "username", "email": "user@email.com"},
                {"id": 1, "name": "username", "email": "user@email.com"},
                {"id": 2, "name": "username", "email": "user@email.com"},
            ],
        ),
        (UserRequest(a=1, b="2", c="3"), {"a": 1, "b": "2", "c": "3"}),
    ],
)
@pytest.mark.asyncio
async def test_body(service, mock_httpx, mocker, request_body, parsed_body):
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
    await service.user.get("/profile", request=request_body)

    params = extract_request_params.spy_return
    assert params.body == parsed_body
