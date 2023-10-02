from fastapi import FastAPI

app = FastAPI()


@app.get("/")
def get_main():
    return {"status": "OK"}
