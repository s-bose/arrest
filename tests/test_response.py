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
    assert isinstance(response, UserResponse)
    assert response == UserResponse(**mock_response)


@pytest.mark.asyncio
async def test_list_response_type(service, mock_httpx):
    service.add_resource(
        Resource(route="/user", handlers=[(Methods.GET, "/", None, UserResponse)])
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
    assert isinstance(response, list)
    assert response[0] == UserResponse(**res_1)
    assert response[1] == UserResponse(**res_2)


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
    assert response == mock_response
