from fastapi import FastAPI
from app.routes.users import user_routes


app = FastAPI(title="Example FastAPI REST application", routes=[*user_routes])


@app.get("/")
async def health():
    return {"status": "service up and running"}
