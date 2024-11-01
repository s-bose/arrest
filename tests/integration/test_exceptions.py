import json
import logging
from typing import Any

import httpx
import pytest

from arrest.exceptions import ArrestError, ArrestHTTPException, HandlerNotFound, ResourceNotFound
from arrest.http import Methods
from arrest.resource import Resource


class HTTPException(Exception):
    def __init__(self, status_code: int, detail: Any) -> None:
        self.status_code = status_code
        self.detail = detail

    def __str__(self) -> str:
        return f"{self.status_code}: {self.detail}"


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
async def test_non_json_http_exception(service, mock_httpx):
    mock_httpx.post(url__regex="/user/*", name="http_request").mock(
        side_effect=httpx.Response(
            status_code=400, text="<xml>helloworld</xml>", headers={"Content-Type": "application/xml"}
        )
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
        assert exc.data == "<xml>helloworld</xml>"


@pytest.mark.asyncio
async def test_non_json_response_exception(service, mock_httpx):
    mock_httpx.post(url__regex="/user/*", name="http_request").mock(
        side_effect=httpx.Response(
            status_code=200, text="<xml>helloworld</xml>", headers={"Content-Type": "application/xml"}
        )
    )

    service.add_resource(
        Resource(
            route="/user",
            handlers=[
                (Methods.POST, "/profile"),
            ],
        )
    )

    with pytest.raises(json.JSONDecodeError):
        await service.user.post("/profile")


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

    with pytest.raises(ResourceNotFound):
        await service.request("/dashboard/profile", method=Methods.POST)


@pytest.mark.parametrize(
    argnames="exc_raised, expected_exc_caught, detail",
    argvalues=[
        (ArrestError("Internal Error"), HTTPException, "Something went wrong"),
        (ArrestHTTPException(status_code=404, data="Not found"), HTTPException, "Not found"),
        (ValueError("foo is not bar"), None, None),
    ],
)
@pytest.mark.asyncio
async def test_custom_exception_handler(service, mocker, exc_raised, expected_exc_caught, detail):
    def http_exc_handler(exc: ArrestHTTPException):
        raise HTTPException(status_code=exc.status_code, detail=exc.data)

    def err_handler(_exc: ArrestError):
        raise HTTPException(status_code=500, detail="Something went wrong")

    def generic_err_handler(_exc: Exception):
        logging.warning("Something went wrong")

    service.add_exception_handlers(
        exc_handlers={
            Exception: generic_err_handler,
            ArrestHTTPException: http_exc_handler,
            ArrestError: err_handler,
        }
    )

    service.add_resource(
        Resource(
            route="/user",
            handlers=[
                ("GET", ""),
            ],
        )
    )

    mocker.patch("arrest.resource.Resource.make_request", side_effect=exc_raised)

    if not expected_exc_caught:
        assert await service.user.get("") is None
    else:
        with pytest.raises(expected_exc_caught) as exc:
            await service.user.get("")
            if detail:
                assert exc.value.detail == detail
