import pytest
from datetime import datetime
from contextlib import nullcontext as noraise
from pydantic import BaseModel, ValidationError

from arrest.resource import Resource, ResourceHandler, HandlerKey
from arrest.http import Methods


class XYZ:
    pass


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


@pytest.mark.parametrize(
    "handler_tuple, exception",
    [
        (
            (
                Methods.GET,
                "/abc",
                PaymentRequest,
                PaymentResponse,
                print,
                "helloworld",
            ),
            pytest.raises(ValueError),
        ),
        ((Methods.GET,), pytest.raises(ValueError)),
        ((Methods.GET, "/"), noraise()),
        (
            (
                Methods.PUT,
                "/{payment_id:int}",
                PaymentRequest,
            ),
            noraise(),
        ),
        (
            (
                Methods.PUT,
                "/{payment_id:int}",
                PaymentRequest,
                PaymentResponse,
                lambda response: print(response.dict()),
            ),
            noraise(),
        ),
    ],
)
def test_resource_handler_tuple(handler_tuple, exception):
    with exception:
        res = Resource(
            route="/payments",
            handlers=[handler_tuple],
        )

        _handler = list(res.routes.values())[0]
        if len(handler_tuple) == 2:
            assert _handler.method == handler_tuple[0]
            assert _handler.route == handler_tuple[1]

        if len(handler_tuple) == 3:
            assert _handler.request == handler_tuple[2]
        if len(handler_tuple) == 4:
            assert _handler.response == handler_tuple[3]
        if len(handler_tuple) == 5:
            assert _handler.callback == handler_tuple[4]


@pytest.mark.parametrize(
    "handler, exception",
    [
        (ResourceHandler(method=Methods.GET, route="/"), noraise()),
        (XYZ(), pytest.raises(ValueError)),
    ],
)
def test_resource_handler_pydantic(handler, exception):
    with exception:
        res = Resource(route="/payments", handlers=[handler])
        _handler = list(res.routes.values())[0]
        assert _handler == handler
