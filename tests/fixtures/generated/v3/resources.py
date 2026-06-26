from arrest import Resource
from .models import ApiResponse, Order, Pet, User

pet = Resource(
    name="pet",
    route="/pet",
    handlers=[
        ("POST", "", Pet, Pet),
        ("PUT", "", Pet, Pet),
        ("GET", "/findByStatus", None, None),
        ("GET", "/findByTags", None, None),
        ("GET", "/{petId}", None, Pet),
        ("POST", "/{petId}", None, None),
        ("DELETE", "/{petId}", None, None),
        ("POST", "/{petId}/uploadImage", None, ApiResponse),
    ]
)

store = Resource(
    name="store",
    route="/store",
    handlers=[
        ("GET", "/inventory", None, None),
        ("POST", "/order", Order, Order),
        ("GET", "/order/{orderId}", None, Order),
        ("DELETE", "/order/{orderId}", None, None),
    ]
)

user = Resource(
    name="user",
    route="/user",
    handlers=[
        ("POST", "", User, None),
        ("POST", "/createWithList", None, User),
        ("GET", "/login", None, None),
        ("GET", "/logout", None, None),
        ("GET", "/{username}", None, User),
        ("PUT", "/{username}", User, None),
        ("DELETE", "/{username}", None, None),
    ]
)
