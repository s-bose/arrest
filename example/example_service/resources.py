from arrest import Resource

from .models import (
    BodyPostCustomRequestWithQueryHeaderBodyCustomPost,
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
        ("GET", "/{user_id}", None, Users),
        ("PUT", "/{user_id}", UserUpdate, Users),
        ("DELETE", "/{user_id}", None, None),
        ("GET", "/all", None, None),
        ("POST", "/", UserCreate, Users),
        ("GET", "/{user_id}/tasks", None, None),
    ],
)

tasks = Resource(
    name="tasks",
    route="/tasks",
    handlers=[
        ("GET", "", None, Task),
        ("GET", "/all", None, None),
        ("GET", "/{task_id}", None, Task),
        ("PATCH", "/{task_id}", TaskUpdate, Task),
        ("DELETE", "/{task_id}", None, None),
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
    name="custom",
    route="/custom",
    handlers=[
        ("POST", "", BodyPostCustomRequestWithQueryHeaderBodyCustomPost, None),
    ],
)
