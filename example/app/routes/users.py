import random
from datetime import datetime
from uuid import UUID, uuid4

from fastapi.exceptions import HTTPException
from fastapi.requests import Request
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute

from example.app.models import Task, UserCreate, Users, UserUpdate


class __UserRoutes:
    @staticmethod
    async def get_random_user(request: Request) -> Users:
        users: list[Users] = request.state.store.get("users")

        rand_index = random.randint(0, len(users) - 1)
        return Users(**users[rand_index])

    @staticmethod
    async def get_all(request: Request) -> list[Users]:
        users: list[Users] = request.state.store.get("users")

        return [Users(**user) for user in users]

    @staticmethod
    async def get_by_id(user_id: UUID, request: Request) -> Users:
        users: list[Users] = request.state.store.get("users")

        user = next((user for user in users if user["id"] == user_id), None)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        return user

    @staticmethod
    async def create(user: UserCreate, request: Request) -> Users:
        users: list[Users] = request.state.store.get("users")

        new_user = Users(
            **user.model_dump(),
            id=uuid4(),
            created_at=datetime.now(),
        )

        users.append(new_user.model_dump())
        return new_user

    @staticmethod
    async def update(user_id: UUID, user: UserUpdate, request: Request) -> Users:
        users: list[Users] = request.state.store.get("users")

        for i, u in enumerate(users):
            if u["id"] == user_id:
                user_updated = Users(**{**users[i], **user.model_dump(), "created_at": datetime.now()})
                users[i] = user_updated.model_dump()
                return user_updated

        raise HTTPException(status_code=404, detail="User not found")

    @staticmethod
    async def delete(user_id: UUID, request: Request) -> bool:
        users: list[Users] = request.state.store.get("users")

        if user_id not in [u["id"] for u in users]:
            raise HTTPException(status_code=404, detail="User not found")

        users = [u for u in users if u["id"] != user_id]

        return True

    @staticmethod
    async def get_tasks_for_user(user_id: UUID, request: Request) -> list[Task]:
        users: list[Users] = request.state.store.get("users")
        tasks: list[Task] = request.state.store.get("tasks")

        user = next((u for u in users if u["id"] == user_id), None)

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        return [Task(**t) for t in tasks if t["user_id"] == user_id]


user_routes = [
    APIRoute(
        path="/users",
        endpoint=__UserRoutes.get_random_user,
        methods=["GET"],
        response_class=JSONResponse,
        response_model=Users,
        status_code=200,
    ),
    APIRoute(
        path="/users/{user_id:uuid}",
        endpoint=__UserRoutes.get_by_id,
        methods=["GET"],
        response_class=JSONResponse,
        response_model=Users,
        status_code=200,
    ),
    APIRoute(
        path="/users/all",
        endpoint=__UserRoutes.get_all,
        methods=["GET"],
        response_class=JSONResponse,
        response_model=list[Users],
        status_code=200,
    ),
    APIRoute(
        path="/users/",
        endpoint=__UserRoutes.create,
        methods=["POST"],
        response_class=JSONResponse,
        response_model=Users,
        status_code=200,
    ),
    APIRoute(
        path="/users/{user_id:uuid}",
        endpoint=__UserRoutes.update,
        methods=["PUT"],
        response_class=JSONResponse,
        response_model=Users,
        status_code=200,
    ),
    APIRoute(
        path="/users/{user_id:uuid}",
        endpoint=__UserRoutes.delete,
        methods=["DELETE"],
        status_code=200,
    ),
    APIRoute(
        path="/users/{user_id:uuid}/tasks",
        endpoint=__UserRoutes.get_tasks_for_user,
        methods=["GET"],
        response_class=JSONResponse,
        response_model=list[Task],
        status_code=200,
    ),
]
