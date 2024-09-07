import enum
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel


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


class Task(BaseModel):
    id: UUID
    user_id: UUID
    title: str
    priority: Priority
    created_at: datetime
