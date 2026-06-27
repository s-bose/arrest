import json
import typing
from dataclasses import dataclass
from datetime import datetime

import httpx
import pytest
from pydantic import BaseModel, RootModel
from pydantic import ValidationError as PydanticValidationError
from respx.patterns import M

from arrest.http import Methods
from arrest.params import Body
from arrest.resource import Resource


class UserRequest(BaseModel):
    id: int
    name: str = Body(...)  # type: ignore
    email: str
    dob: typing.Optional[datetime] = None


@dataclass
class UserRequestDC:
    id: int
    name: str
    email: str
    dob: typing.Optional[datetime] = None


class UserRequestRoot(RootModel):
    root: list[UserRequest]


@pytest.mark.parametrize(
    "request_body, request_type, parsed_body, exception",
    [
        # pydantic models
        (
            {"id": 0, "name": "username", "email": "user@email.com"},
            UserRequest,
            {"id": 0, "name": "username", "email": "user@email.com", "dob": None},
            None,
        ),
        (
            UserRequest(id=123, name="username", email="user@email.com"),
            UserRequest,
            {"id": 123, "name": "username", "email": "user@email.com", "dob": None},
            None,
        ),
        (
            {"id": 0, "name": "username", "foo": "bar"},
            UserRequest,
            None,
            PydanticValidationError,
        ),
        # dataclasses
        (
            {"id": 0, "name": "username", "email": "user@email.com"},
            UserRequestDC,
            {"id": 0, "name": "username", "email": "user@email.com", "dob": None},
            None,
        ),
        (
            UserRequestDC(id=123, name="username", email="user@email.com"),
            UserRequestDC,
            {"id": 123, "name": "username", "email": "user@email.com", "dob": None},
            None,
        ),
        (
            {"id": 0, "name": "username", "foo": "bar"},
            UserRequestDC,
            None,
            PydanticValidationError,
        ),
        # list types
        (
            [{"id": 0, "name": "username", "email": "user@email.com"}],
            list[UserRequest],
            [{"id": 0, "name": "username", "email": "user@email.com", "dob": None}],
            None,
        ),
        (
            [
                {"id": 0, "name": "username1", "email": "user1@email.com"},
                {"id": 1, "name": "username2", "email": "user2@email.com"},
            ],
            list[UserRequest],
            [
                {"id": 0, "name": "username1", "email": "user1@email.com", "dob": None},
                {"id": 1, "name": "username2", "email": "user2@email.com", "dob": None},
            ],
            None,
        ),
        (
            [UserRequest(id=123, name="username", email="user@email.com")],
            list[UserRequest],
            [{"id": 123, "name": "username", "email": "user@email.com", "dob": None}],
            None,
        ),
        (
            [{"id": 0, "name": "username", "foo": "bar"}],
            list[UserRequest],
            None,
            PydanticValidationError,
        ),
        (
            [{"id": 0, "name": "username", "email": "user@email.com"}],
            list[UserRequestDC],
            [{"id": 0, "name": "username", "email": "user@email.com", "dob": None}],
            None,
        ),
        (
            [UserRequestDC(id=123, name="username", email="user@email.com")],
            list[UserRequestDC],
            [{"id": 123, "name": "username", "email": "user@email.com", "dob": None}],
            None,
        ),
        (
            [{"id": 0, "name": "username", "foo": "bar"}],
            list[UserRequestDC],
            None,
            PydanticValidationError,
        ),
        # pydantic root models
        (
            [{"id": 0, "name": "username", "email": "user@email.com"}],
            UserRequestRoot,
            [{"id": 0, "name": "username", "email": "user@email.com", "dob": None}],
            None,
        ),
        (
            UserRequestRoot(
                root=[{"id": 0, "name": "username", "email": "user@email.com"}]  # type: ignore
            ),
            UserRequestRoot,
            [{"id": 0, "name": "username", "email": "user@email.com", "dob": None}],
            None,
        ),
    ],
)
@pytest.mark.asyncio
async def test_body_request_json(
    service,
    mock_httpx,
    request_body: BaseModel | list | dict,
    request_type: typing.Any,
    parsed_body: dict | list | None,
    exception: Exception | None,
):
    patterns = [
        M(url__regex="/user/*", method__in=["POST"]),
    ]

    service.add_resource(
        Resource(
            route="/user",
            handlers=[
                (
                    Methods.POST,
                    "/profile",
                    request_type,
                ),
            ],
        )
    )

    if exception:
        with pytest.raises(exception):
            await service.user.post("/profile", request=request_body)
    else:
        mock_httpx.route(*patterns, name="http_request").mock(
            return_value=httpx.Response(200, json={"status": "OK"})
        )
        await service.user.post("/profile", request=request_body)

        request: httpx.Request = mock_httpx["http_request"].calls[0].request
        request_body = json.loads(request.content)
        assert parsed_body == request_body
