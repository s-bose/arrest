import uuid

import pytest
from httpx import ASGITransport

from arrest import Resource, Service
from example.app.main import app

users = Resource(
    name="users",
    route="/users",
    handlers=[
        ("GET", ""),
        ("GET", "/all"),
        ("GET", "/{user_id}"),
        ("PUT", "/{user_id}"),
        ("DELETE", "/{user_id}"),
        ("POST", "/"),
        ("GET", "/{user_id}/tasks"),
    ],
)


tasks = Resource(
    name="tasks",
    route="/tasks",
    handlers=[
        ("GET", ""),
        ("GET", "/all"),
        ("GET", "/{task_id}"),
        ("PATCH", "/{task_id}"),
        ("DELETE", "/{task_id}"),
        ("POST", "/"),
    ],
)


root = Resource(name="root", route="", handlers=[("GET", "/")])

svc = Service(
    name="svc without types",
    url="http://web",
    resources=[root, tasks, users],
    transport=ASGITransport(app=app),
)


@pytest.mark.asyncio
async def test_get_random_user():
    response = await svc.users.get("")

    assert response.data
    assert isinstance(response.data, dict)


@pytest.mark.asyncio
async def test_get_all_users():
    response = await svc.users.get("/all")

    assert response.data
    assert isinstance(response.data, list)

    assert isinstance(response.data[0], dict)


@pytest.mark.asyncio
async def test_create_user():
    request = {"name": "john doe", "email": "john_doe@email.com"}

    response = await svc.users.post("/", request=request)

    assert response.data
    assert isinstance(response.data, dict)
    assert response.data["name"] == "john doe"
    assert response.data["email"] == "john_doe@email.com"


@pytest.mark.asyncio
async def test_delete_user_by_id():
    user_id = uuid.UUID(int=3)
    response = await svc.users.delete(f"/{user_id}")

    assert response.data is True


@pytest.mark.asyncio
async def test_get_random_task():
    response = await svc.tasks.get("")

    assert response.data
    assert isinstance(response.data, dict)


@pytest.mark.asyncio
async def test_create_task():
    request = {
        "user_id": str(uuid.UUID(int=1)),
        "title": "New Task",
        "priority": "HIGH",
    }

    response = await svc.tasks.post("/", request=request)

    assert response.data
    assert isinstance(response.data, dict)
    assert response.data["title"] == "New Task"
    assert response.data["priority"] == "HIGH"


@pytest.mark.asyncio
async def test_delete_task_by_id():
    task_id = uuid.UUID(int=101)
    response = await svc.tasks.delete(f"/{task_id}")

    assert response.data is True
