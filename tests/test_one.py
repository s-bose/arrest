from pydantic import BaseModel
from typing import Optional
from arrest.service.service import Service
from arrest.resource.resource import Resource, ResourceHandler
from arrest.http import Methods
from arrest.params import Query, Path, Header

resources = [
    Resource(
        "payment",
        route="/",
    ),
    Resource(
        "analytics",
        route="/analytics",
    ),
]

payments_service = Service(
    name="payments",
    url="https://mybignewidea.com/internal/payments/api/v1",
    resources=resources,
)


# class BaseRequest(BaseModel):
#     a: int
#     b: str
#     c: Optional[int] = Query(gt=100)


# req = BaseRequest(a=1, b="abc", c=200)
# print(req.model_fields)


class RequestBody(BaseModel):
    id: int
    name: str
    abc: str
    payment_id: Optional[str]


rq_handler = ResourceHandler(
    method=Methods.GET,
    route="/{payment_id:int}",
    request=RequestBody,
    response=None,
    kwargs={},
)


print(rq_handler)
