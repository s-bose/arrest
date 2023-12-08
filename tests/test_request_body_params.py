from datetime import datetime
from typing import Optional

import httpx
import pytest
from pydantic import BaseModel
from respx.patterns import M

from arrest.http import Methods
from arrest.params import Body, Query
from arrest.resource import Resource


class UserRequest(BaseModel):
    limit: int = Query(...)
    name: str = Body(...)
    email: str
    dob: Optional[datetime]


@pytest.mark.parametrize(
    "request_body, pydantic_version",
    [
        (
            UserRequest(limit=1, name="bob", email="abc@mail.com", dob=None),
            "1.",
        ),
        (
            UserRequest(limit=1, name="bob", email="abc@mail.com", dob=None),
            "2.",
        ),
        (
            {"limit": 1, "name": "bob", "email": "abc@mail.com", "dob": None},
            "1.",
        ),
        (
            {"limit": 1, "name": "bob", "email": "abc@mail.com", "dob": None},
            "2.",
        ),
    ],
)
@pytest.mark.asyncio
async def test_request_body_params(service, mock_httpx, mocker, request_body, pydantic_version):
    patterns = [
        M(url__regex="/user/*", method__in=["POST"]),
    ]

    mock_httpx.route(*patterns, name="http_request").mock(
        return_value=httpx.Response(200, json={"status": "OK"})
    )

    mocker.patch("arrest.utils.PYDANTIC_VERSION", new=pydantic_version, autospec=False)

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
        request=request_body,
    )

    params = extract_request_params.spy_return
    assert params.body == {
        "name": "bob",
        "email": "abc@mail.com",
        "dob": None,
    }
