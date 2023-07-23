### rough idea

#! playground DO NOT use
from datetime import datetime
from pydantic import BaseModel
from typing import Optional
from arrest_alt import Service, Resource, Query
from arrest_alt.exceptions import ArrestHttpException


class PaymentGetRequest(BaseModel):
    sort: bool = Query(..., default=True)
    limit: int = Query(..., default=100)
    user_id: Optional[str] = Query(...)


class PaymentPostRequest(BaseModel):
    name: str
    value: int
    from_: str
    to_: str
    invoice_no: str
    owner_id: str
    currency: str
    total_amount: float


class PaymentResponse(BaseModel):
    id: str
    name: str
    value: int
    from_: str
    to_: str
    invoice_no: str
    owner_id: str
    created_at: datetime
    updated_at: datetime
    currency: str
    total_amount: float


class AnalyticsRequest(BaseModel):
    pass


class AnalyticsResponse(BaseModel):
    pass


# payments_service = Service(
#     name="payments",
#     url="https://mybignewidea.com/internal/payments/api/v1",
#     resources=[
#         Resource("/payment")
#         .get("/", req=PaymentGetRequest, res=PaymentResponse)
#         .get("/{payment_id?:int}", res=PaymentResponse)
#         .exception(["400", "401", "402", "403", "404", "422", "500"]),
#         Resource("/analytics")
#         .get("/")
#         .post("/", req=AnalyticsRequest, res=AnalyticsResponse),
#     ],
# )


# alternate impl
from arrest_alt.http import Http

# define resources
payment_resource = Resource("payment", route="/payment", response_model=PaymentResponse)
payment_resource.add_handler(
    Http.GET,
    "/",
    req=PaymentGetRequest,
    res=PaymentResponse,
)
payment_resource.add_handler(
    Http.POST,
    "/",
    req=PaymentPostRequest,
    res=PaymentResponse,
)


analytics_resource = Resource(
    "analytics", route="/analytics", response_model=AnalyticsResponse
)
analytics_resource.add_handler(Http.GET, "/")
analytics_resource.add_handler(Http.POST, "/", req=AnalyticsRequest)


# define service
payments_service = Service(
    name="payments",
    url="https://mybignewidea.com/internal/payments/api/v1",
    resources=[payment_resource, analytics_resource],
)


# import requests
# payment_id = get_payment_id_from_db()

# response = requests.get("https://mybignewidea.com/internal/payments/api/v1/payment")

# BE

from microservices import payments_service

payment_exp = payments_service.exception

payment_request = PaymentPostRequest(
    name="xyz",
    value=123,
    from_="abc@gmail.com",
    to_="dummy@mail.com",
    owner_id=123,
    currency="USD",
    total_amount=123.5
)



# try:
#     payment_response: PaymentResponse = payments_service.analytics.post("/", request=payment_request)
# except ArrestHttpException as exc:
#     match exc.status_code:
#         case payment_exp[0]: # 400
#             # do something with the error message
#             exc.body()
#         case default:
#             print(exc.body())

try:
    payment_response: PaymentResponse = payments_service.analytics.post(f"/{payment_id}", request=payment_request)
except ArrestHttpException as exc:
    match exc.status_code:
        case payment_exp[0]: # 400
            # do something with the error message
            exc.body()
        case default:
            print(exc.body())
