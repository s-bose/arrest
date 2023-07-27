from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from arrest.service.service import Service
from arrest.resource.resource import Resource

# payment_resource = Resource("payment", route="/payment", response_model=PaymentResponse)
# payment_resource.add_handler(
#     Http.GET,
#     "/",
#     sort=Query(bool),
#     limit=Query(int, default=100, gt=0),
#     user_id=Query(Optional[str]),
#     response=PaymentResponse,
# )
# payment_resource.add_handler(
#     Http.GET,
#     "/{payment_id?:int}",
#     request=PaymentGetRequest,
#     response=PaymentResponse,
# )
# resources = [
#     Resource(
#         "payment",
#         route="/",
#     ),
#     Resource(
#         "analytics",
#         route="/analytics",
#     ),
# ]

# payments_service = Service(
#     name="payments",
#     url="https://mybignewidea.com/internal/payments/api/v1",
#     resources=resources,
# )

app = FastAPI()


@app.get("/")
async def main():
    return "hello world"


@app.get("/{abc}")
async def run_abc(abc: str):
    if abc != "abc":
        return JSONResponse(status_code=400, content="invalid abc")
        # raise HTTPException(400, {"msg": "invalid abc"})

    return abc
