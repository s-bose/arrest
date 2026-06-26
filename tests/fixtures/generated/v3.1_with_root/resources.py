from arrest import Resource
from .models import Pet, Pets

root = Resource(
    name="root",
    route="",
    handlers=[
        ("GET", "/", None, None),
    ]
)

health = Resource(
    name="health",
    route="/health",
    handlers=[
        ("GET", "", None, None),
    ]
)

pets = Resource(
    name="pets",
    route="/pets",
    handlers=[
        ("GET", "", None, Pets),
        ("POST", "", None, None),
        ("GET", "/{petId}", None, Pet),
    ]
)
