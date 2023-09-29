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
from arrest.params import Query
from types import SimpleNamespace
from pprint import pprint

# class BaseRequest(BaseModel):
#     a: int
#     b: str
#     c: Optional[int] = Query(gt=100)


# req = BaseRequest(a=1, b="abc", c=200)
# print(req.model_fields)


class RequestBody(BaseModel):
    sort: bool = Query(default=True)
    limit: int = Query(default=100)
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
            (Methods.GET, "/"),
            (Methods.POST, "/{anything_id:int}", Optional[RequestBody]),
        ],
    ),
    Resource(
        "analytics",
        route="/analytics",
    ),
    Resource(route="/", handlers=[ResourceHandler(method=Methods.GET, route="/")]),
]

payments_service = Service(
    name="payments",
    url="https://httpbin.org",
    resources=resources,
)

# anything_id = 2

# # response = asyncio.run(
# #     payments_service["anything"].post(
# #         f"/{anything_id}",
# #         request=RequestBody(
# #             id=1, name="abc", payment_id="xyz", created_at=datetime.utcnow()
# #         ),
# #     )
# # )

# response = asyncio.run(
#     payments_service.resources["anything"].post(
#         f"/{anything_id}",
#         request=RequestBody(
#             id=1, name="abc", payment_id="xyz", created_at=datetime.utcnow()
#         ),
#     )
# )

# print(response)
#
pprint(payments_service.resources["anything"].routes)
