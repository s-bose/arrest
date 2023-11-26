from typing import Optional
from datetime import datetime
import httpx
import respx
import pytest
from respx.patterns import M
from pydantic import BaseModel
from pydantic import ValidationError

from arrest.resource import Resource
from arrest.http import Methods
from arrest.params import Query, Header, Body, ParamTypes
from tests import TEST_DEFAULT_SERVICE_URL


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
        x_max_age: int = Header(...)
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
            x_max_age=20,
            x_user_agent="mozila",
        ),
    )
    handler, _ = get_matching_handler.spy_return
    assert handler.route == "/profile"
    params = extract_request_params.spy_return
    assert params[ParamTypes.query] == {"limit": 1}
    assert params[ParamTypes.header] == {
        "x-max-age": "20",
        "x-user-agent": "mozila",
        "Content-Type": "application/json",
    }
    assert params[ParamTypes.body] == {
        "name": "bob",
        "email": "bob@mail.com",
        "password": "xyz",
    }
