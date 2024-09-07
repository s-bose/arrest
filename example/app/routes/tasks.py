from fastapi import APIRouter
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException

from app.data import users, tasks

tasks_router = APIRouter(prefix="/tasks")
