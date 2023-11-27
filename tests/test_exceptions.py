import pytest
import httpx

from arrest.exceptions import ArrestHTTPException, HandlerNotFound, NotFoundException
from arrest.resource import Resource
from arrest.http import Methods


@pytest.mark.asyncio
async def test_http_exception(service, mock_httpx):
    mock_httpx.post(url__regex="/user/*", name="http_request").mock(
        return_value=httpx.Response(400, json={"msg": "unauthenticated"})
    )

    service.add_resource(
        Resource(
            route="/user",
            handlers=[
                (Methods.POST, "/profile"),
            ],
        )
    )

    with pytest.raises(ArrestHTTPException) as exc:
        await service.user.post("/profile")
        assert exc.status_code == 400
        assert exc.data == {"msg": "unauthenticated"}


@pytest.mark.asyncio
async def test_timeout_exception(service, mock_httpx):
    mock_httpx.post(url__regex="/user/*", name="http_request").mock(
        side_effect=httpx.TimeoutException(message="connection timed out")
    )

    service.add_resource(
        Resource(
            route="/user",
            handlers=[
                (Methods.POST, "/profile"),
            ],
        )
    )

    with pytest.raises(ArrestHTTPException) as exc:
        await service.user.post("/profile")
        assert exc.status_code == 500
        assert exc.data == "connection timed out"


@pytest.mark.asyncio
async def test_base_request_error(service, mock_httpx):
    mock_httpx.post(url__regex="/user/*", name="http_request").mock(
        side_effect=httpx.RequestError(message="something went wrong")
    )

    service.add_resource(
        Resource(
            route="/user",
            handlers=[
                (Methods.POST, "/profile"),
            ],
        )
    )

    with pytest.raises(ArrestHTTPException) as exc:
        await service.user.post("/profile")
        assert exc.status_code == 500
        assert exc.data == "something went wrong"


@pytest.mark.asyncio
async def test_handler_not_found(service):
    service.add_resource(
        Resource(
            route="/user",
            handlers=[
                (Methods.POST, "/profile"),
            ],
        )
    )

    with pytest.raises(HandlerNotFound):
        await service.user.post("/dashboard")


@pytest.mark.asyncio
async def test_resource_not_found(service):
    service.add_resource(
        Resource(
            route="/user",
            handlers=[
                (Methods.POST, "/profile"),
            ],
        )
    )

    with pytest.raises(NotFoundException):
        await service.request("/dashboard/profile", method=Methods.POST)
