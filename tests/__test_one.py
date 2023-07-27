from pydantic import BaseModel
from typing import Optional
import asyncio
from arrest.service.service import Service
from arrest.resource.resource import Resource, ResourceHandler
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
    abc: str
    payment_id: Optional[str]


rq_handler = ResourceHandler(
    method=Methods.GET,
    route="/{payment_id:int}",
    request=RequestBody,
    response=None,
    kwargs={},
)

resources = [
    Resource(
        "anything",
        route="/anything/",
        handlers=[
            ResourceHandler(
                method=Methods.GET,
                route="/",
            ),
            ResourceHandler(
                method=Methods.GET,
                route="/{payment_id:int}",
                # request=RequestBody | None,
                # request=Optional[RequestBody],
            ),
        ],
    ),
    Resource(
        "analytics",
        route="/analytics",
    ),
]

payments_service = Service(
    name="payments",
    url="https://httpbin.org",
    resources=resources,
)

payment_id = 2
try:
    response = asyncio.run(payments_service["anything"].get(f"/{payment_id}"))
except ArrestHTTPException as exc:
    match exc.status_code:
        case 401:
            # do something with  exc.data
        case 404:
            # break
        case 500:
            break
        case _:
            # do nothing

print(json.dumps(response))
