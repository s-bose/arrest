from arrest import GET, POST, PUT, DELETE, PATCH, H, Resource
from arrest.ai.meta import ToolMeta

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
        H(
            GET,
            "",
            None,
            Users,
            tool_meta=ToolMeta(
                name="get_random_user", description="Get one random user."
            ),
        ),
        H(
            GET,
            "/{user_id}",
            None,
            Users,
            tool_meta=ToolMeta(
                name="get_user_by_id", description="Get a single user by their id."
            ),
        ),
        H(
            PUT,
            "/{user_id}",
            UserUpdate,
            Users,
            tool_meta=ToolMeta(
                name="update_user", description="Update a user's name and/or email."
            ),
        ),
        H(
            DELETE,
            "/{user_id}",
            None,
            None,
            tool_meta=ToolMeta(name="delete_user", description="Delete a user by id."),
        ),
        H(
            GET,
            "/all",
            None,
            None,
            tool_meta=ToolMeta(name="list_users", description="List every user."),
        ),
        H(
            POST,
            "/",
            UserCreate,
            Users,
            tool_meta=ToolMeta(name="create_user", description="Create a new user."),
        ),
        H(
            GET,
            "/{user_id}/tasks",
            None,
            None,
            tool_meta=ToolMeta(
                name="get_tasks_for_user",
                description="List every task belonging to a given user.",
            ),
        ),
    ],
)

tasks = Resource(
    name="tasks",
    route="/tasks",
    handlers=[
        H(
            GET,
            "",
            None,
            Task,
            tool_meta=ToolMeta(
                name="get_random_task", description="Get one random task."
            ),
        ),
        H(
            GET,
            "/all",
            None,
            None,
            tool_meta=ToolMeta(name="list_tasks", description="List every task."),
        ),
        H(
            GET,
            "/{task_id}",
            None,
            Task,
            tool_meta=ToolMeta(
                name="get_task_by_id", description="Get a single task by its id."
            ),
        ),
        H(
            PATCH,
            "/{task_id}",
            TaskUpdate,
            Task,
            tool_meta=ToolMeta(
                name="update_task",
                description="Update a task's title, priority, and/or owner.",
            ),
        ),
        H(
            DELETE,
            "/{task_id}",
            None,
            None,
            tool_meta=ToolMeta(name="delete_task", description="Delete a task by id."),
        ),
        H(
            POST,
            "/",
            TaskCreate,
            Task,
            tool_meta=ToolMeta(
                name="create_task", description="Create a new task for a user."
            ),
        ),
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
