from datetime import datetime
from uuid import uuid4

import httpx
import pytest
from pydantic import BaseModel

from arrest.http import Methods
from arrest.resource import Resource


class XYZ:
    pass


class UserResponse(BaseModel):
    user_id: str
    name: str
    email: str
    role: str
    created_at: datetime
    updated_at: datetime


@pytest.mark.asyncio
async def test_response_type(service, mock_httpx):
    service.add_resource(
        Resource(route="/user", handlers=[(Methods.GET, "/", None, UserResponse)])
    )

    mock_response = dict(
        user_id=str(uuid4()),
        name="abc",
        email="abc@email.com",
        role="admin",
        created_at=str(datetime.now()),
        updated_at=str(datetime.now()),
    )

    mock_httpx.get(url__regex="/user/*", name="http_request").mock(
        return_value=httpx.Response(200, json=mock_response)
    )

    response = await service.user.get("/")
    assert isinstance(response.data, UserResponse)
    assert response.data == UserResponse(**mock_response)


@pytest.mark.asyncio
async def test_list_response_type(service, mock_httpx):
    service.add_resource(
        Resource(route="/user", handlers=[(Methods.GET, "/", None, list[UserResponse])])
    )

    res_1 = dict(
        user_id=str(uuid4()),
        name="abc",
        email="abc@email.com",
        role="admin",
        created_at=str(datetime.now()),
        updated_at=str(datetime.now()),
    )

    res_2 = dict(
        user_id=str(uuid4()),
        name="def",
        email="def@email.com",
        role="user",
        created_at=str(datetime.now()),
        updated_at=str(datetime.now()),
    )

    mock_httpx.get(url__regex="/user/*", name="http_request").mock(
        return_value=httpx.Response(200, json=[res_1, res_2])
    )

    response = await service.user.get("/")
    assert isinstance(response.data, list)
    assert response.data[0] == UserResponse(**res_1)
    assert response.data[1] == UserResponse(**res_2)


@pytest.mark.asyncio
async def test_response_type_invalid_type(service, mock_httpx):
    service.add_resource(
        Resource(route="/user", handlers=[(Methods.GET, "/", None, UserResponse)])
    )
    mock_httpx.get(url__regex="/user/*", name="http_request").mock(
        return_value=httpx.Response(200, json=123.45)
    )

    with pytest.raises(ValueError):
        await service.user.get("/")


@pytest.mark.asyncio
async def test_no_response_type(service, mock_httpx):
    mock_response = dict(
        user_id=str(uuid4()),
        name="abc",
        email="abc@email.com",
        role="admin",
        created_at=str(datetime.now()),
        updated_at=str(datetime.now()),
    )

    service.add_resource(Resource(route="/user", handlers=[(Methods.GET, "/")]))

    mock_httpx.get(url__regex="/user/*", name="http_request").mock(
        return_value=httpx.Response(200, json=mock_response)
    )

    response = await service.user.get("/")
    assert response.data == mock_response


@pytest.mark.asyncio
async def test_empty_response_returns_none(service, mock_httpx):
    mock_httpx.get(url__regex="/user/*", name="http_request").mock(
        return_value=httpx.Response(204)
    )

    service.add_resource(Resource(route="/user", handlers=[(Methods.GET, "/")]))

    response = await service.user.get("/")
    assert response.data is None


@pytest.mark.asyncio
async def test_response_undecodable_body(service, mock_httpx):
    """Non-JSON body with charset mismatch → ResponseError."""
    from arrest.exceptions import ResponseError

    mock_httpx.get(url__regex="/user/*", name="http_request").mock(
        return_value=httpx.Response(
            200,
            content=b"\xff\xfe",
            headers={"Content-Type": "application/json; charset=iso-8859-1"},
        )
    )

    service.add_resource(Resource(route="/user", handlers=[(Methods.GET, "/")]))

    with pytest.raises(ResponseError):
        await service.user.get("/")


@pytest.mark.parametrize(
    "status_code, success, redirect, client_err, server_err",
    [
        (200, True, False, False, False),
        (301, False, True, False, False),
        (404, False, False, True, False),
        (500, False, False, False, True),
    ],
)
def test_response_status_properties(
    status_code, success, redirect, client_err, server_err
):
    from arrest.response import Response

    resp = Response(
        data=None,
        status_code=status_code,
        url=httpx.URL("http://x"),
        elapsed=None,
        raw=httpx.Response(status_code),
        request=None,
    )
    assert resp.is_success == success
    assert resp.is_redirect == redirect
    assert resp.is_client_error == client_err
    assert resp.is_server_error == server_err
