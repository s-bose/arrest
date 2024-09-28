import uuid

import pytest

from example.example_service.models import Task, UserCreate, Users
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


@pytest.mark.parametrize(
    "data",
    [
        {"name": "john doe", "email": "john_doe@email.com"},
        UserCreate(name="john doe", email="john_doe@email.com"),
    ],
)
@pytest.mark.asyncio
async def test_create_user(data: dict | UserCreate):
    response = await example_service.users.post("/", request=data)

    assert response
    assert isinstance(response, Users)

    assert response.name == "john doe"
    assert response.email == "john_doe@email.com"


@pytest.mark.asyncio
async def test_delete_user_by_id():
    user_id = uuid.UUID(int=2)
    response = await example_service.users.delete(f"/{user_id}")

    assert response
    assert response is True


@pytest.mark.asyncio
async def test_get_user_tasks():
    user_id = uuid.UUID(int=1)
    response = await example_service.users.get(f"/{user_id}/tasks")

    assert response
    assert isinstance(response, list)

    assert len(response) > 0
    assert isinstance(response[0], Task)


@pytest.mark.asyncio
async def test_get_random_task():
    response = await example_service.tasks.get("")

    assert response
    assert isinstance(response, Task)


@pytest.mark.asyncio
async def test_get_all_tasks():
    response = await example_service.tasks.get("/all")

    assert response
    assert isinstance(response, list)

    assert isinstance(response[0], Task)


@pytest.mark.asyncio
async def test_get_task_by_id():
    task_id = uuid.UUID(int=102)
    response = await example_service.tasks.get(f"/{task_id}")

    assert response
    assert isinstance(response, Task)

    assert response.id == task_id


@pytest.mark.parametrize("path_param_style", ["A", "B"])
@pytest.mark.asyncio
async def test_delete_task_by_id(path_param_style: str):
    if path_param_style == "A":
        task_id = uuid.UUID(int=102)
        response = await example_service.tasks.delete(f"/{task_id}")

    else:
        task_id = uuid.UUID(int=103)
        response = await example_service.tasks.delete("/", task_id=task_id)

    assert response is True
