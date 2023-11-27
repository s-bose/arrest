from typing import Optional
from datetime import datetime
import httpx
import pytest
from respx.patterns import M
from pydantic import BaseModel

from arrest.resource import Resource
from arrest.http import Methods
from arrest.params import Query, Body, ParamTypes


@pytest.mark.asyncio
async def test_request_body_params(service, mock_httpx, mocker):
    patterns = [
        M(url__regex="/user/*", method__in=["POST"]),
    ]

    mock_httpx.route(*patterns, name="http_request").mock(
        return_value=httpx.Response(200, json={"status": "OK"})
    )

    class UserRequest(BaseModel):
        limit: int = Query(...)
        name: str = Body(...)
        email: str
        dob: Optional[datetime]

    service.add_resource(
        Resource(
            route="/user",
            handlers=[
                (Methods.POST, "/profile", UserRequest),
            ],
        )
    )

    extract_request_params = mocker.spy(service.user, "extract_request_params")
    await service.user.post(
        "/profile",
        request=UserRequest(limit=1, name="bob", email="abc@mail.com", dob=None),
    )

    params = extract_request_params.spy_return
    assert params[ParamTypes.body] == {
        "name": "bob",
        "email": "abc@mail.com",
        "dob": None,
    }

    assert params[ParamTypes.query] == {
        "limit": 1,
    }
