# flake8: noqa
from importlib.metadata import PackageNotFoundError, version

from .exceptions import ArrestHTTPException, RequestError
from .handler import H
from .http import Methods
from .resource import Resource
from .response import Response
from .service import Service
from ._config import ArrestConfig

try:
    __version__ = version("arrest")
except PackageNotFoundError:
    __version__ = "unknown"

GET = Methods.GET
POST = Methods.POST
PUT = Methods.PUT
PATCH = Methods.PATCH
DELETE = Methods.DELETE
HEAD = Methods.HEAD
OPTIONS = Methods.OPTIONS

__all__ = [
    "ArrestHTTPException",
    "H",
    "Methods",
    "RequestError",
    "Resource",
    "Response",
    "Service",
    "GET",
    "POST",
    "PUT",
    "PATCH",
    "DELETE",
    "HEAD",
    "OPTIONS",
    "ArrestConfig",
    "__version__",
]
