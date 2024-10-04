import uuid
from typing import List

import pytest
from httpx import ASGITransport

from arrest import Resource, Service
from example.app.main import app
from example.example_service.models import (
    Priority,
    Task,
    TaskCreate,
    TaskUpdate,
    UserCreate,
    Users,
    UserUpdate,
)

users = Resource(
    name="users",
    route="/users",
    handlers=[
        ("GET", "", None, Users),
        ("GET", "/all", None, List[Users]),
        ("GET", "/{user_id}", None, Users),
        ("PUT", "/{user_id}", UserUpdate, Users),
        ("DELETE", "/{user_id}", None, bool),
        ("POST", "/", UserCreate, Users),
        ("GET", "/{user_id}/tasks", None, List[Task]),
    ],
)

tasks = Resource(
    name="tasks",
    route="/tasks",
    handlers=[
        ("GET", "", None, Task),
        ("GET", "/all", None, List[Task]),
        ("GET", "/{task_id}", None, Task),
        ("PATCH", "/{task_id}", TaskUpdate, Task),
        ("DELETE", "/{task_id}", None, bool),
        ("POST", "/", TaskCreate, Task),
    ],
)

root = Resource(
    name="root",
    route="",
    handlers=[
        ("GET", "/", None, None),
    ],
)

svc = Service(
    name="svc without types",
    url="http://localhost:8080",
    resources=[root, tasks, users],
    transport=ASGITransport(app=app),
)


@pytest.mark.asyncio
async def test_get_all_users():
    response = await svc.users.get("/all")

    assert response
    assert isinstance(response, list)
    assert len(response) > 0

    assert isinstance(response[0], Users)


@pytest.mark.asyncio
async def test_get_random_user():
    response = await svc.users.get("")

    assert response
    assert isinstance(response, Users)


@pytest.mark.asyncio
async def test_get_user_by_id():
    user_id = uuid.UUID(int=1)
    response = await svc.users.get(f"/{user_id}")

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
    response = await svc.users.post("/", request=data)

    assert response
    assert isinstance(response, Users)

    assert response.name == "john doe"
    assert response.email == "john_doe@email.com"


@pytest.mark.asyncio
async def test_delete_user_by_id():
    user_id = uuid.UUID(int=2)
    response = await svc.users.delete(f"/{user_id}")

    assert response
    assert response is True


@pytest.mark.asyncio
async def test_get_user_tasks():
    user_id = uuid.UUID(int=1)
    response = await svc.users.get(f"/{user_id}/tasks")

    assert response
    assert isinstance(response, list)

    assert len(response) > 0
    assert isinstance(response[0], Task)


@pytest.mark.asyncio
async def test_get_random_task():
    response = await svc.tasks.get("")

    assert response
    assert isinstance(response, Task)


@pytest.mark.asyncio
async def test_get_all_tasks():
    response = await svc.tasks.get("/all")

    assert response
    assert isinstance(response, list)

    assert isinstance(response[0], Task)


@pytest.mark.asyncio
async def test_get_task_by_id():
    task_id = uuid.UUID(int=102)
    response = await svc.tasks.get(f"/{task_id}")

    assert response
    assert isinstance(response, Task)

    assert response.id == task_id


@pytest.mark.parametrize(
    "data",
    [
        {
            "user_id": uuid.UUID(int=1),
            "title": "title",
            "priority": "HIGH",
        },
        TaskCreate(
            user_id=uuid.UUID(int=1),
            title="title",
            priority="HIGH",
        ),
    ],
)
@pytest.mark.asyncio
async def test_create_task(data: dict | TaskCreate):
    response = await svc.tasks.post("/", request=data)

    assert response
    assert isinstance(response, Task)

    assert response.user_id == uuid.UUID(int=1)
    assert response.title == "title"
    assert response.priority == Priority.HIGH


@pytest.mark.parametrize("path_param_style", ["A", "B"])
@pytest.mark.asyncio
async def test_delete_task_by_id(path_param_style: str):
    if path_param_style == "A":
        task_id = uuid.UUID(int=102)
        response = await svc.tasks.delete(f"/{task_id}")

    else:
        task_id = uuid.UUID(int=102)
        response = await svc.tasks.delete("/", task_id=task_id)

    assert response is True
