import pytest

from fastapi import FastAPI
from fastapi.testclient import TestClient


async def get_root():
    return {"msg": "hello world"}


@pytest.fixture()
def client():
    app = FastAPI()
    app.add_api_route("/", endpoint=get_root, methods=["GET"])
    return TestClient(app)
