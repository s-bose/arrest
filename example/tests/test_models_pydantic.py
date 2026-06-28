import uuid
from typing import List, Optional

import pytest
from httpx import ASGITransport
from pydantic import BaseModel

from arrest import Resource, Service
from arrest.params import Body, Header, Query
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


class CustomRequest(BaseModel):
    foo: str = Body(...)
    bar: str = Body(...)
    x_api_key: str = Header(..., serialization_alias="x-api-key")
    x_secret: str = Header(..., serialization_alias="x-secret")
    limit: Optional[int] = Query(10)
    user_id: Optional[str] = Query(None)


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

custom = Resource(
    name="custom", route="/custom", handlers=[("POST", "", CustomRequest, dict)]
)

svc = Service(
    name="svc without types",
    url="http://localhost:8080",
    resources=[root, tasks, users, custom],
    transport=ASGITransport(app=app),
)


@pytest.mark.asyncio
async def test_get_all_users():
    response = await svc.users.get("/all")

    assert response
    assert isinstance(response.data, list)
    assert len(response.data) > 0

    assert isinstance(response.data[0], Users)


@pytest.mark.asyncio
async def test_get_random_user():
    response = await svc.users.get("")

    assert response
    assert isinstance(response.data, Users)


@pytest.mark.asyncio
async def test_get_user_by_id():
    user_id = uuid.UUID(int=1)
    response = await svc.users.get(f"/{user_id}")

    assert response
    assert isinstance(response.data, Users)

    assert response.data.id == user_id


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
    assert isinstance(response.data, Users)

    assert response.data.name == "john doe"
    assert response.data.email == "john_doe@email.com"


@pytest.mark.asyncio
async def test_delete_user_by_id():
    user_id = uuid.UUID(int=2)
    response = await svc.users.delete(f"/{user_id}")

    assert response
    assert response.data is True


@pytest.mark.asyncio
async def test_get_user_tasks():
    user_id = uuid.UUID(int=1)
    response = await svc.users.get(f"/{user_id}/tasks")

    assert response
    assert isinstance(response.data, list)

    assert len(response.data) > 0
    assert isinstance(response.data[0], Task)


@pytest.mark.asyncio
async def test_get_random_task():
    response = await svc.tasks.get("")

    assert response
    assert isinstance(response.data, Task)


@pytest.mark.asyncio
async def test_get_all_tasks():
    response = await svc.tasks.get("/all")

    assert response
    assert isinstance(response.data, list)

    assert isinstance(response.data[0], Task)


@pytest.mark.asyncio
async def test_get_all_tasks_limit():
    response = await svc.tasks.get("/all?limit=1")

    assert response
    assert isinstance(response.data, list)

    assert len(response.data) == 1

    response = await svc.tasks.get("/all", query={"limit": 2})
    assert len(response.data) == 2

    class UserQueryRequest(BaseModel):
        limit: int = Query(1)

    response = await svc.tasks.get("/all", request=UserQueryRequest(limit=3))

    assert len(response.data) == 3


@pytest.mark.asyncio
async def test_get_task_by_id():
    task_id = uuid.UUID(int=102)
    response = await svc.tasks.get(f"/{task_id}")

    assert response
    assert isinstance(response.data, Task)

    assert response.data.id == task_id


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
    assert isinstance(response.data, Task)

    assert response.data.user_id == uuid.UUID(int=1)
    assert response.data.title == "title"
    assert response.data.priority == Priority.HIGH


@pytest.mark.parametrize("path_param_style", ["A", "B"])
@pytest.mark.asyncio
async def test_delete_task_by_id(path_param_style: str):
    if path_param_style == "A":
        task_id = uuid.UUID(int=102)
        response = await svc.tasks.delete(f"/{task_id}")

    else:
        task_id = uuid.UUID(int=102)
        response = await svc.tasks.delete("/", task_id=task_id)

    assert response.data is True


@pytest.mark.parametrize(
    "req, expect_404",
    [
        (
            CustomRequest(
                foo="Body -> Foo",
                bar="Body -> Bar",
                x_api_key="Header -> X-Api-Key",
                x_secret="Header -> X-Secret",
                limit=10,
                user_id="ca21e0ee-0747-440d-a98f-d306058438ac",
            ),
            True,
        ),
        (
            CustomRequest(
                foo="Body -> Foo",
                bar="Body -> Bar",
                x_api_key="Header -> X-Api-Key",
                x_secret="Header -> X-Secret",
                limit=10,
                user_id=str(uuid.UUID(int=2)),
            ),
            False,
        ),
    ],
)
@pytest.mark.asyncio
async def test_custom_request_with_header_query_body(
    req: CustomRequest, expect_404: bool
):
    response = await svc.custom.post("", request=req)
    assert isinstance(response.data, dict)

    if expect_404:
        assert response.status_code == 404
    else:
        assert response.data == {
            "body": {
                "foo": "Body -> Foo",
                "bar": "Body -> Bar",
            },
            "query": {"limit": 10},
            "headers": {
                "x-api-key": "Header -> X-Api-Key",
                "x-secret": "Header -> X-Secret",
            },
        }
