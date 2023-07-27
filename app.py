from fastapi import FastAPI
from fastapi.responses import JSONResponse


app = FastAPI()


@app.get("/")
async def main():
    return "hello world"


@app.get("/{abc}")
async def run_abc(abc: str):
    if abc != "abc":
        return JSONResponse(status_code=400, content="invalid abc")
        # raise HTTPException(400, {"msg": "invalid abc"})

    return abc
