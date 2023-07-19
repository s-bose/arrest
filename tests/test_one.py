from arrest.service.service import Service
from arrest.resource.resource import Resource


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

print(payments_service.__dict__z)
