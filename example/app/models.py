import enum
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


# Users
class Priority(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class Users(BaseModel):
    id: UUID
    name: str
    email: str
    created_at: datetime


class UserCreate(BaseModel):
    name: str
    email: str


class UserUpdate(UserCreate):
    pass


# Tasks
class Task(BaseModel):
    id: UUID
    user_id: UUID
    title: str
    priority: Priority
    created_at: datetime


class TaskCreate(BaseModel):
    user_id: UUID
    title: str
    priority: Priority


class TaskUpdate(TaskCreate):
    pass
