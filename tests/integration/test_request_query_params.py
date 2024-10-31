import httpx
import pytest
from pydantic import BaseModel, ValidationError
from respx.patterns import M

from arrest.http import Methods
from arrest.params import Query
from arrest.resource import Resource


@pytest.mark.asyncio
async def test_request_query_params(service, mock_httpx):
    patterns = [
        M(url__regex="/user/*", method__in=["GET", "POST"]),
    ]

    mock_httpx.route(*patterns, name="http_request").mock(
        return_value=httpx.Response(200, json={"status": "OK"})
    )

    class UserRequest(BaseModel):
        limit: int = Query()
        q: str = Query()

    service.add_resource(
        Resource(
            route="/user",
            handlers=[
                (Methods.POST, "/profile", UserRequest),
            ],
        )
    )

    await service.user.post("/profile", request=UserRequest(limit=1, q="abc"))

    assert len(mock_httpx["http_request"].calls) == 1
    req: httpx.Request = mock_httpx["http_request"].calls[0].request
    assert httpx.QueryParams(req.url.query) == httpx.QueryParams({"limit": 1, "q": "abc"})


@pytest.mark.asyncio
async def test_request_query_params_invalid_type(service, mocker):
    class UserRequest(BaseModel):
        limit: int = Query()
        q: str = Query()

    class FooModel(BaseModel):
        bar: int

    service.add_resource(
        Resource(
            route="/user",
            handlers=[
                (Methods.POST, "/profile", UserRequest),
            ],
        )
    )

    get_matching_handler = mocker.spy(service.user, "get_matching_handler")
    with pytest.raises(ValueError):
        await service.user.post("/profile", request=FooModel(bar=1))

    handler, _ = get_matching_handler.spy_return
    assert handler.route == "/profile"


@pytest.mark.asyncio
async def test_request_query_params_validation_error(service):
    class UserRequest(BaseModel):
        limit: int = Query(gt=10)
        q: str = Query(default="default")

    service.add_resource(
        Resource(
            route="/user",
            handlers=[
                (Methods.POST, "/profile", UserRequest),
            ],
        )
    )

    with pytest.raises(ValidationError):
        await service.user.post("/profile", request=UserRequest(limit=15, q=123.0))
        await service.user.post("/profile", request=UserRequest(limit=10, q="abc"))


@pytest.mark.asyncio
async def test_request_query_params_in_url(service, mock_httpx):
    mock_httpx.route(url__regex="/user/*", name="http_request", method__in=["GET", "POST"]).mock(
        return_value=httpx.Response(200, json={"status": "OK"})
    )

    service.add_resource(
        Resource(
            route="/user",
            handlers=[
                (Methods.GET, "/profile"),
            ],
        )
    )

    await service.user.get("/profile?limit=2&q=abc")
    request: httpx.Request = mock_httpx["http_request"].calls[0].request
    assert httpx.QueryParams(request.url.query) == httpx.QueryParams({"limit": "2", "q": "abc"})


@pytest.mark.asyncio
async def test_request_query_params_in_arguments(service, mock_httpx):
    mock_httpx.route(url__regex="/user/*", name="http_request", method__in=["GET", "POST"]).mock(
        return_value=httpx.Response(200, json={"status": "OK"})
    )

    service.add_resource(
        Resource(
            route="/user",
            handlers=[
                (Methods.GET, "/profile"),
            ],
        )
    )

    await service.user.get("/profile", query={"limit": 2, "q": "abc"})
    request: httpx.Request = mock_httpx["http_request"].calls[0].request

    assert httpx.QueryParams(request.url.params) == httpx.QueryParams({"limit": 2, "q": "abc"})


@pytest.mark.asyncio
async def test_query_params_in_both_request_model_and_arguments(service, mock_httpx, mocker):
    patterns = [
        M(url__regex="/user/*", method__in=["GET"]),
    ]

    mock_httpx.route(*patterns, name="http_request").mock(
        return_value=httpx.Response(200, json={"status": "OK"})
    )

    class UserRequest(BaseModel):
        limit: int = Query(...)
        name: str
        email: str
        password: str

    service.add_resource(
        Resource(
            route="/user",
            handlers=[
                (Methods.GET, "/profile"),
            ],
        )
    )

    await service.user.get(
        "/profile",
        request=UserRequest(limit=2, name="abc", email="abc@email.com", password="123"),
        query={"value": "xyz"},
    )

    request: httpx.Request = mock_httpx["http_request"].calls[0].request
    assert httpx.QueryParams(request.url.params) == httpx.QueryParams({"limit": 2, "value": "xyz"})
