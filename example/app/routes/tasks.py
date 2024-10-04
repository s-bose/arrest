import random
from datetime import datetime
from uuid import UUID, uuid4

from fastapi.exceptions import HTTPException
from fastapi.requests import Request
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute

from example.app.models import Task, TaskCreate, TaskUpdate


class __TaskRoutes:
    @staticmethod
    async def get_random_task(request: Request) -> Task:
        tasks: list[Task] = request.state.store.get("tasks")

        rand_index = random.randint(0, len(tasks) - 1)
        return Task(**tasks[rand_index])

    @staticmethod
    async def get_all_tasks(request: Request) -> list[Task]:
        tasks: list[Task] = request.state.store.get("tasks")

        return tasks

    @staticmethod
    async def get_task_by_id(task_id: UUID, request: Request) -> Task:
        tasks: list[Task] = request.state.store.get("tasks")

        task = next((t for t in tasks if t["id"] == task_id), None)
        return Task(**task)

    @staticmethod
    async def create_task(new_task: TaskCreate, request: Request) -> Task:
        tasks: list[Task] = request.state.store.get("tasks")

        t = Task(
            id=uuid4(),
            user_id=new_task.user_id,
            title=new_task.title,
            priority=new_task.priority,
            created_at=datetime.now(),
        )
        tasks.append(t.model_dump())

        return t

    @staticmethod
    async def update_task(task_id: UUID, task: TaskUpdate, request: Request) -> Task:
        tasks: list[Task] = request.state.store.get("tasks")

        for i, task in enumerate(tasks):
            if task["id"] == task_id:
                task_updated = Task(**{**task["id"], **task.model_dump(), "created_at": datetime.now()})
                tasks[i] = task_updated.model_dump()
                return task_updated

        raise HTTPException(status_code=404, detail="Task not found")

    @staticmethod
    async def delete_task(task_id: UUID, request: Request) -> bool:
        tasks: list[Task] = request.state.store.get("tasks")

        if task_id not in [t["id"] for t in tasks]:
            raise HTTPException(status_code=404, detail="Task not found")

        tasks = [t for t in tasks if t["id"] != task_id]
        return True


task_routes = [
    APIRoute(
        path="/tasks",
        endpoint=__TaskRoutes.get_random_task,
        methods=["GET"],
        response_class=JSONResponse,
        response_model=Task,
        status_code=200,
    ),
    APIRoute(
        path="/tasks/all",
        endpoint=__TaskRoutes.get_all_tasks,
        methods=["GET"],
        response_class=JSONResponse,
        response_model=list[Task],
        status_code=200,
    ),
    APIRoute(
        path="/tasks/{task_id:uuid}",
        endpoint=__TaskRoutes.get_task_by_id,
        methods=["GET"],
        response_class=JSONResponse,
        response_model=Task,
        status_code=200,
    ),
    APIRoute(
        path="/tasks/",
        endpoint=__TaskRoutes.create_task,
        methods=["POST"],
        response_class=JSONResponse,
        response_model=Task,
        status_code=200,
    ),
    APIRoute(
        path="/tasks/{task_id:uuid}",
        endpoint=__TaskRoutes.update_task,
        methods=["PATCH"],
        response_class=JSONResponse,
        response_model=Task,
        status_code=200,
    ),
    APIRoute(
        path="/tasks/{task_id:uuid}",
        endpoint=__TaskRoutes.delete_task,
        methods=["DELETE"],
        response_class=JSONResponse,
        status_code=200,
    ),
]
