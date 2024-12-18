from arrest import Service
from .resources import health, pets, root

swagger_petstore = Service(
    name="swagger_petstore",
    url="http://petstore.swagger.io/v1",
    resources=[health, pets, root]
)
