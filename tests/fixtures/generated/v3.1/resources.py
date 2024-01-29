from arrest import Resource
from .models import Pet, Pets

pets = Resource(
    name="pets",
    route="/pets",
    handlers=[
        ("GET", "", None, Pets),
        ("POST", "", None, None),
        ("GET", "/{petId}", None, Pet),
    ]
)
