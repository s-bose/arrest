from typing import Callable, Optional
from uuid import UUID

from fastapi import Body, FastAPI, Header, Query, Request
from fastapi.exceptions import HTTPException

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


@app.post("/custom")
async def post_custom_request_with_query_header_body(
    request: Request,
    foo: str = Body(...),
    bar: str = Body(...),
    x_api_key: str = Header(...),
    x_secret: str = Header(...),
    limit: Optional[int] = Query(10),
    user_id: Optional[str] = Query(None),
):
    if user_id is not None:
        users_store = request.state.store["users"]
        user = next((u for u in users_store if u["id"] == UUID(user_id)), None)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

    return {
        "body": {"foo": foo, "bar": bar},
        "query": {"limit": limit},
        "headers": {"x-api-key": x_api_key, "x-secret": x_secret},
    }
