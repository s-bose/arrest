from arrest import Service
from .resources import pets

swagger_petstore = Service(
    name="swagger_petstore",
    url="http://petstore.swagger.io/v1",
    resources=[pets]
)
