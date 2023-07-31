from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import asyncio
import json
from pprint import pprint
from arrest.service import Service
from arrest.resource import Resource, ResourceHandler
from arrest.http import Methods
from arrest.exceptions import ArrestHTTPException


# class BaseRequest(BaseModel):
#     a: int
#     b: str
#     c: Optional[int] = Query(gt=100)


# req = BaseRequest(a=1, b="abc", c=200)
# print(req.model_fields)


class RequestBody(BaseModel):
    id: int
    name: str
    payment_id: Optional[str]
    created_at: Optional[datetime]


class Test(BaseModel):
    pass


rq_handler = ResourceHandler(
    method=Methods.GET,
    route="/{payment_id:int}",
    request=RequestBody,
    response=None,
    kwargs={},
)

resources = [
    Resource(
        route="/anything/",
        handlers=[
            ResourceHandler(
                method=Methods.GET,
                route="/",
            ),
            ResourceHandler(
                method=Methods.POST,
                route="/{anything_id:int}",
                # request=Optional[RequestBody],
            ),
        ],
    ),
    Resource(
        "analytics",
        route="/analytics",
    ),
    Resource("", route="/", handlers=[ResourceHandler(method=Methods.GET, route="/")]),
]

payments_service = Service(
    name="payments",
    url="https://httpbin.org",
    resources=resources,
)

anything_id = 2

# response = asyncio.run(
#     payments_service["anything"].post(
#         f"/{anything_id}",
#         request=RequestBody(
#             id=1, name="abc", payment_id="xyz", created_at=datetime.utcnow()
#         ),
#     )
# )
response = asyncio.run(
    payments_service.post(
        f"/anything/{anything_id}",
        request=RequestBody(
            id=1, name="abc", payment_id="xyz", created_at=datetime.utcnow()
        ),
    )
)

print(response)
