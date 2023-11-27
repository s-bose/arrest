import pytest
from datetime import datetime
from pydantic import BaseModel, ValidationError

from arrest.resource import Resource, ResourceHandler
from arrest.http import Methods


class PaymentRequest(BaseModel):
    user_id: int
    name: str
    amount: float
    currency: str
    date: datetime


class PaymentResponse(BaseModel):
    id: str
    user_id: int
    name: str
    amount: float
    currency: str
    date: datetime
    status: str
    created_at: datetime
    updated_at: datetime


def test_resource_handlers_tuple():
    with pytest.raises(ValueError):
        payment_resource = Resource(
            route="/payments",
            handlers=[
                (Methods.GET, "/"),
                (Methods.GET, "/{payment_id:int}"),
                (Methods.POST, "/", PaymentRequest),
                (
                    Methods.PUT,
                    "/{payment_id:int}",
                    PaymentRequest,
                    PaymentResponse,
                    lambda response: print(response.dict()),
                ),
                (
                    Methods.GET,
                    "/abc",
                    PaymentRequest,
                    PaymentResponse,
                    lambda x: print(x),
                    "helloworld",
                ),
                (Methods.GET,),
            ],
        )

        assert set(payment_resource.routes.keys()) == set(
            [
                (Methods.GET, "/"),
                (Methods.GET, "/{payment_id:int}"),
                (Methods.POST, "/"),
                (Methods.PUT, "/{payment_id:int}"),
            ]
        )


def test_resource_handlers_dict():
    with pytest.raises(ValueError):
        payment_resource = Resource(
            route="/payments",
            handlers=[
                {"method": Methods.GET, "route": "/"},
                {"method": Methods.GET, "route": 123},
                {"method": Methods.GET, "route": "/{payment_id:int}"},
                {"method": Methods.POST, "route": "/", "request": PaymentRequest},
                {
                    "method": Methods.PUT,
                    "route": "/{payment_id:int}",
                    "request": PaymentRequest,
                    "response": PaymentResponse,
                    "callback": lambda response: print(response.dict()),
                },
            ],
        )

        assert set(payment_resource.routes.keys()) == set(
            [
                (Methods.GET, "/"),
                (Methods.GET, "/{payment_id:int}"),
                (Methods.POST, "/"),
                (Methods.PUT, "/{payment_id:int}"),
            ]
        )


def test_resource_handler_pydantic():
    with pytest.raises(ValidationError):
        Resource(
            route="/payments",
            handlers=[
                ResourceHandler(method=Methods.GET, route="/"),
                ResourceHandler(route="/"),
            ],
        )
