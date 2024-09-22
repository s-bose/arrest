import uuid

import pytest

from example.example_service.models import Task, Users
from example.example_service.services import example_service


@pytest.mark.asyncio
async def test_get_all_users():
    response = await example_service.users.get("/all")

    assert response
    assert isinstance(response, list)
    assert len(response) > 0

    assert isinstance(response[0], Users)


@pytest.mark.asyncio
async def test_get_random_user():
    response = await example_service.users.get("")

    assert response
    assert isinstance(response, Users)


@pytest.mark.asyncio
async def test_get_user_by_id():
    user_id = uuid.UUID(int=1)
    response = await example_service.users.get(f"/{user_id}")

    assert response
    assert isinstance(response, Users)

    assert response.id == user_id


@pytest.mark.asyncio
async def test_get_user_tasks():
    user_id = uuid.UUID(int=1)
    response = await example_service.users.get(f"/{user_id}/tasks")

    assert response
    assert isinstance(response, list)

    assert len(response) > 0
    assert isinstance(response[0], Task)
