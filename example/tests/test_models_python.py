import uuid
from typing import Any, Dict, List

import pytest
from httpx import ASGITransport

from arrest import Resource, Service
from example.app.main import app

users = Resource(
    name="users",
    route="/users",
    handlers=[
        ("GET", "", None, dict),
        ("GET", "/all", None, List[Dict[str, Any]]),
        ("GET", "/{user_id}", None, Dict[str, Any]),
        ("PUT", "/{user_id}", dict, Dict[str, Any]),
        ("DELETE", "/{user_id}", None, bool),
        ("POST", "/", Dict[str, Any], dict),
        ("GET", "/{user_id}/tasks", None, list[dict]),
    ],
)

tasks = Resource(
    name="tasks",
    route="/tasks",
    handlers=[
        ("GET", "", None, dict),
        ("GET", "/all", None, List[dict]),
        ("GET", "/{task_id}", None, dict),
        ("PATCH", "/{task_id}", Dict[str, Any], dict),
        ("DELETE", "/{task_id}", None, bool),
        ("POST", "/", dict, Dict[str, Any]),
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

    assert isinstance(response[0], dict)


@pytest.mark.asyncio
async def test_get_random_user():
    response = await svc.users.get("")

    assert response
    assert isinstance(response, dict)


@pytest.mark.asyncio
async def test_get_user_by_id():
    user_id = uuid.UUID(int=1)
    response = await svc.users.get(f"/{user_id}")

    assert response
    assert isinstance(response, dict)

    assert response["id"] == str(user_id)


@pytest.mark.asyncio
async def test_create_user():
    data = {
        "name": "john doe",
        "email": "john_doe@email.com",
    }
    response = await svc.users.post("/", request=data)

    assert response
    assert isinstance(response, dict)

    assert response["name"] == "john doe"
    assert response["email"] == "john_doe@email.com"


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
    assert isinstance(response[0], dict)


@pytest.mark.asyncio
async def test_get_random_task():
    response = await svc.tasks.get("")

    assert response
    assert isinstance(response, dict)


@pytest.mark.asyncio
async def test_get_all_tasks():
    response = await svc.tasks.get("/all")

    assert response
    assert isinstance(response, list)

    assert isinstance(response[0], dict)


@pytest.mark.asyncio
async def test_get_task_by_id():
    task_id = uuid.UUID(int=102)
    response = await svc.tasks.get(f"/{task_id}")

    assert response
    assert isinstance(response, dict)

    assert response["id"] == str(task_id)


@pytest.mark.asyncio
async def test_create_task():
    data = {
        "user_id": uuid.UUID(int=1),
        "title": "title",
        "priority": "HIGH",
    }
    response = await svc.tasks.post("/", request=data)

    assert response
    assert isinstance(response, dict)

    assert response["user_id"] == str(uuid.UUID(int=1))
    assert response["title"] == "title"
    assert response["priority"] == "HIGH"


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
