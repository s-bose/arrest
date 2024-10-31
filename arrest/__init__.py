# flake8: noqa
from .http import Methods
from .resource import Resource
from .service import Service

__version__ = "0.1.10"

GET = Methods.GET
POST = Methods.POST
PUT = Methods.PUT
PATCH = Methods.PATCH
DELETE = Methods.DELETE
HEAD = Methods.HEAD
OPTIONS = Methods.OPTIONS

__all__ = [
    "Methods",
    "Resource",
    "Service",
    "GET",
    "POST",
    "PUT",
    "PATCH",
    "DELETE",
    "HEAD",
    "OPTIONS",
]
