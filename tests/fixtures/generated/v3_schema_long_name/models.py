# generated by datamodel-codegen:
#   filename:  <stdin>
#   timestamp: 2024-01-29T18:57:26+00:00

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class Status(Enum):
    placed = 'placed'
    approved = 'approved'
    delivered = 'delivered'


class Order(BaseModel):
    id: Optional[int] = Field(None, example=10)
    petId: Optional[int] = Field(None, example=198772)
    quantity: Optional[int] = Field(None, example=7)
    shipDate: Optional[datetime] = None
    status: Optional[Status] = Field(
        None, description='Order Status', example='approved'
    )
    complete: Optional[bool] = None


class Address(BaseModel):
    street: Optional[str] = Field(None, example='437 Lytton')
    city: Optional[str] = Field(None, example='Palo Alto')
    state: Optional[str] = Field(None, example='CA')
    zip: Optional[str] = Field(None, example='94301')


class Category(BaseModel):
    id: Optional[int] = Field(None, example=1)
    name: Optional[str] = Field(None, example='Dogs')


class User(BaseModel):
    id: Optional[int] = Field(None, example=10)
    username: Optional[str] = Field(None, example='theUser')
    firstName: Optional[str] = Field(None, example='John')
    lastName: Optional[str] = Field(None, example='James')
    email: Optional[str] = Field(None, example='john@email.com')
    password: Optional[str] = Field(None, example='12345')
    phone: Optional[str] = Field(None, example='12345')
    userStatus: Optional[int] = Field(None, description='User Status', example=1)


class Tag(BaseModel):
    id: Optional[int] = None
    name: Optional[str] = None


class Status1(Enum):
    available = 'available'
    pending = 'pending'
    sold = 'sold'


class PetWithVeryLongNameSnakeCased(BaseModel):
    id: Optional[int] = Field(None, example=10)
    name: str = Field(..., example='doggie')
    category: Optional[Category] = None
    photoUrls: List[str]
    tags: Optional[List[Tag]] = None
    status: Optional[Status1] = Field(None, description='pet status in the store')


class ApiResponse(BaseModel):
    code: Optional[int] = None
    type: Optional[str] = None
    message: Optional[str] = None


class Customer(BaseModel):
    id: Optional[int] = Field(None, example=100000)
    username: Optional[str] = Field(None, example='fehguy')
    address: Optional[List[Address]] = None
