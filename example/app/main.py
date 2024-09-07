from app.routes.tasks import task_routes
from app.routes.users import user_routes
from fastapi import FastAPI

app = FastAPI(title="Example FastAPI REST application", routes=[*user_routes, *task_routes])


@app.get("/")
async def health():
    return {"status": "service up and running"}
