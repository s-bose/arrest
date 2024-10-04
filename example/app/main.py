from typing import Callable

from fastapi import FastAPI, Request

from example.app.data import tasks, users
from example.app.routes.tasks import task_routes
from example.app.routes.users import user_routes

app = FastAPI(title="Example FastAPI REST application", routes=[*user_routes, *task_routes])


@app.middleware("http")
async def add_store_middleware(request: Request, call_next: Callable):
    request.state.store = {"users": users, "tasks": tasks}
    response = await call_next(request)
    return response


@app.get("/")
async def health():
    return {"status": "service up and running"}
