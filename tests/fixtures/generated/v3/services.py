from arrest import Service
from .resources import pet, store, user

swagger_petstore_openapi_3_0 = Service(
    name="swagger_petstore_openapi_3_0",
    url="/api/v3",
    resources=[pet, store, user]
)
