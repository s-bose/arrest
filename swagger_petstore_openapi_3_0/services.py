from arrest import Resource, Service

from .resources import store, user, pet



swagger_petstore_openapi_3_0 = Service(
    name="swagger_petstore_openapi_3_0",
    url="/api/v3",
    resources=[pet, store, user]
)

