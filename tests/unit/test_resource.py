from contextlib import nullcontext as noraise
from datetime import datetime

import pytest
from pydantic import BaseModel

from arrest.converters import UUIDConverter
from arrest.defaults import ROOT_RESOURCE
from arrest.http import Methods
from arrest.resource import Resource, ResourceHandler
from arrest.service import Service


class XYZ:
    pass


class UserCreate(BaseModel):
    name: str
    email: str
    password: str


class PaymentRequest(BaseModel):
    user_id: int
    name: str
    amount: float
    currency: str
    date: datetime


class PaymentResponse(BaseModel):
    id: str
    user_id: int
    name: str
    amount: float
    currency: str
    date: datetime
    status: str
    created_at: datetime
    updated_at: datetime


def test_resource_handlers_dict():
    payment_resource = Resource(
        route="/payments",
        handlers=[
            {"method": Methods.GET, "route": "/"},
            {"method": Methods.GET, "route": "/{payment_id:int}"},
            {"method": Methods.POST, "route": "/", "request": PaymentRequest},
            {
                "method": Methods.PUT,
                "route": "/{payment_id:int}",
                "request": PaymentRequest,
                "response": PaymentResponse,
                "callback": lambda response: print(response.dict()),
            },
        ],
    )

    assert set(payment_resource.routes.keys()) == set(
        [
            (Methods.GET, ""),
            (Methods.GET, "/"),
            (Methods.GET, "/{payment_id}"),
            (Methods.POST, "/"),
            (Methods.PUT, "/{payment_id}"),
        ]
    )


@pytest.mark.parametrize(
    "handler_tuple, exception",
    [
        (
            (
                Methods.GET,
                "/abc",
                PaymentRequest,
                PaymentResponse,
                print,
                "helloworld",
            ),
            pytest.raises(ValueError),
        ),
        ((Methods.GET,), pytest.raises(ValueError)),
        ((Methods.GET, "/"), noraise()),
        (
            (
                Methods.PUT,
                "/{payment_id:int}",
                PaymentRequest,
            ),
            noraise(),
        ),
        (
            (
                Methods.PUT,
                "/{payment_id:int}",
                PaymentRequest,
                PaymentResponse,
                lambda response: print(response.dict()),
            ),
            noraise(),
        ),
    ],
)
def test_resource_handler_tuple(handler_tuple, exception):
    with exception:
        res = Resource(
            route="/payments",
            handlers=[handler_tuple],
        )

        _handlers = list(res.routes.values())
        root_handler, _handler = _handlers[0], _handlers[1]

        assert root_handler.method == Methods.GET
        assert root_handler.route == ""

        if len(handler_tuple) == 2:
            assert _handler.method == handler_tuple[0]
            assert _handler.route == handler_tuple[1]

        if len(handler_tuple) == 3:
            assert _handler.request == handler_tuple[2]
        if len(handler_tuple) == 4:
            assert _handler.response == handler_tuple[3]
        if len(handler_tuple) == 5:
            assert _handler.callback == handler_tuple[4]


@pytest.mark.parametrize(
    "handler, exception",
    [
        (ResourceHandler(method=Methods.GET, route="/"), noraise()),
        (XYZ(), pytest.raises(ValueError)),
    ],
)
def test_resource_handler_pydantic(handler, exception):
    with exception:
        res = Resource(route="/payments", handlers=[handler])
        handlers = list(res.routes.values())
        root_handler, _handler = handlers[0], handlers[1]
        assert root_handler.method == Methods.GET
        assert root_handler.route == ""

        assert _handler == handler


def test_resource_handler_pydantic_validation_error():
    with pytest.raises(ValueError):
        Resource(route="/payments", handlers=[{"method": Methods.GET, "route": XYZ()}])


@pytest.mark.parametrize(
    "resource",
    [
        Resource(route="/payments"),
        Resource(route="/payments", handlers=None),
        Resource(route="/payments", handlers=[]),
    ],
)
def test_resource_handler_empty(resource: Resource):
    assert len(resource.routes) == 1
    root_handler = list(resource.routes.values())[0]

    assert root_handler.method == Methods.GET
    assert root_handler.route == ""

    # unbound handler with no path_regex returns None from parse_path
    handler = ResourceHandler(method=Methods.GET, route="/unbound")
    assert handler.parse_path(method=Methods.GET, path="/unbound") is None


def test_resource_multiple_handler_same_signature():
    res = Resource(
        route="/payments",
        handlers=[("GET", "/audit/{audit_id}"), ("GET", "/audit/{audit_id:uuid}")],
    )

    assert len(res.routes) == 2
    root_handler = list(res.routes.values())[0]
    assert root_handler.method == Methods.GET
    assert root_handler.route == ""

    key, handler = list(res.routes.items())[-1]

    assert key.method, key.route == ("GET", "/audit/{audit_id}")
    assert isinstance(handler._param_types["audit_id"], UUIDConverter)


@pytest.mark.asyncio
async def test_resource_decorator():
    class UserResource(Resource):
        def __init__(self, **kwargs) -> None:
            super().__init__(
                route="/user", handlers=[("GET", "/"), ("POST", "/")], **kwargs
            )

    res = UserResource()

    # res = Resource(route="/user", handlers=[("GET", "/"), ("POST", "/")])
    svc = Service(name="example", url="http://www.example.com/api")
    svc.add_resource(res)

    @res.handler("/xyz")
    async def get_user_xml(self, url, my_arg: int):
        url_new = f"{url}/{my_arg}"
        return url_new, self.base_url

    assert await res.get_user_xml(123) == (
        "http://www.example.com/api/user/xyz/123",
        "http://www.example.com/api",
    )


@pytest.mark.parametrize(argnames="route", argvalues=["", "/"])
def test_root_resource(route: str):
    res = Resource(route=route)
    assert res.route == route
    assert res.name == ROOT_RESOURCE

    assert len(res.routes) == 1
    root_handler = list(res.routes.values())[0]

    assert root_handler.method == Methods.GET
    assert root_handler.route == route


@pytest.mark.parametrize(
    "resource, default_handler",
    [
        (
            Resource(
                route="/users",
                handlers=[
                    {"method": Methods.GET, "route": "/{user_id}"},
                    {"method": Methods.POST, "route": ""},
                ],
            ),
            ResourceHandler(
                method=Methods.GET,
                route="",
            ),
        ),
        (
            Resource(
                route="/users/",
                handlers=[
                    {"method": Methods.GET, "route": "/{user_id}"},
                    {"method": Methods.POST, "route": ""},
                ],
            ),
            ResourceHandler(
                method=Methods.GET,
                route="/",
            ),
        ),
        (
            Resource(
                route="/users",
                handlers=[
                    {"method": Methods.GET, "route": "", "request": UserCreate},
                    {"method": Methods.GET, "route": "/{user_id}"},
                    {"method": Methods.POST, "route": ""},
                ],
            ),
            ResourceHandler(
                method=Methods.GET,
                route="",
                request=UserCreate,
            ),
        ),
    ],
)
def test_resource_default_handler(resource: Resource, default_handler: ResourceHandler):
    routes = list(resource.routes.values())

    _default_handler = routes[0]

    assert _default_handler.method == default_handler.method
    assert _default_handler.route == default_handler.route
    assert _default_handler.request == default_handler.request


def _identity_cb(x):
    return x


@pytest.mark.parametrize(
    "args,kw,expected",
    [
        pytest.param(
            (Methods.GET, "/"),
            {},
            dict(
                method=Methods.GET,
                route="/",
                request=None,
                response=None,
                callback=None,
                headers=None,
            ),
            id="2 positional",
        ),
        pytest.param(
            (Methods.POST, "/items"),
            {"headers": {"X-Key": "val"}},
            dict(
                method=Methods.POST,
                route="/items",
                request=None,
                response=None,
                callback=None,
                headers={"X-Key": "val"},
            ),
            id="2 positional + headers",
        ),
        pytest.param(
            (Methods.PUT, "/users", UserCreate),
            {},
            dict(
                method=Methods.PUT,
                route="/users",
                request=UserCreate,
                response=None,
                callback=None,
                headers=None,
            ),
            id="3 positional",
        ),
        pytest.param(
            (Methods.PATCH, "/users/{user_id}", PaymentRequest),
            {"headers": {"Accept": "application/json"}},
            dict(
                method=Methods.PATCH,
                route="/users/{user_id}",
                request=PaymentRequest,
                response=None,
                callback=None,
                headers={"Accept": "application/json"},
            ),
            id="3 positional + headers",
        ),
        pytest.param(
            (Methods.POST, "/users", UserCreate, PaymentRequest),
            {},
            dict(
                method=Methods.POST,
                route="/users",
                request=UserCreate,
                response=PaymentRequest,
                callback=None,
                headers=None,
            ),
            id="4 positional",
        ),
        pytest.param(
            (Methods.GET, "/export", None, PaymentRequest),
            {"headers": {"Content-Type": "text/csv"}},
            dict(
                method=Methods.GET,
                route="/export",
                request=None,
                response=PaymentRequest,
                callback=None,
                headers={"Content-Type": "text/csv"},
            ),
            id="4 positional + headers",
        ),
        pytest.param(
            (Methods.DELETE, "/users/{user_id}", None, None, _identity_cb),
            {},
            dict(
                method=Methods.DELETE,
                route="/users/{user_id}",
                request=None,
                response=None,
                callback=_identity_cb,
                headers=None,
            ),
            id="5 positional",
        ),
        pytest.param(
            (Methods.HEAD, "/ping", None, None, _identity_cb),
            {"headers": {"X-Trace": "abc123"}},
            dict(
                method=Methods.HEAD,
                route="/ping",
                request=None,
                response=None,
                callback=_identity_cb,
                headers={"X-Trace": "abc123"},
            ),
            id="5 positional + headers",
        ),
        pytest.param(
            (Methods.GET, "/health"),
            {"headers": None},
            dict(
                method=Methods.GET,
                route="/health",
                request=None,
                response=None,
                callback=None,
                headers=None,
            ),
            id="headers=None",
        ),
    ],
)
def test_h_all_combinations(args, kw, expected):
    """Every valid H() call returns a correctly-populated ResourceHandler."""
    from arrest.handler import H

    result = H(*args, **kw)

    assert isinstance(result, ResourceHandler)
    for attr, want in expected.items():
        actual = getattr(result, attr)
        assert actual == want, f"{attr}: {actual!r} != {want!r}"

    # internal fields must stay at defaults (not settable by users)
    assert result._path_format is None
    assert result._path_regex is None
    assert result._param_types is None


@pytest.mark.parametrize(
    "args,kw",
    [
        pytest.param(
            (Methods.GET, "/"),
            {"path_format": "/hijacked"},
            id="rejects PrivateAttr name",
        ),
        pytest.param(
            (Methods.GET, "/"),
            {"foo": "bar"},
            id="rejects unknown field",
        ),
    ],
)
def test_h_rejects_internal_and_unknown_fields(args, kw):
    """H() rejects unknown kwargs (TypeError) — ResourceHandler rejects them
    via extra='forbid' (ValidationError). Both paths are tested."""
    from pydantic import ValidationError

    from arrest.handler import H

    # H() itself rejects unknown kwargs before they reach Pydantic
    with pytest.raises(TypeError):
        H(*args, **kw)

    # Direct ResourceHandler construction also rejects them
    with pytest.raises(ValidationError):
        ResourceHandler(method=args[0], route=args[1], **kw)
