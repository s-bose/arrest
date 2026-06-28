import logging
from typing import Any

import httpx
import pytest

from arrest.exceptions import (
    ArrestError,
    ArrestHTTPException,
    HandlerNotFound,
    RequestError,
    ResponseError,
)
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
    """4xx responses are returned as Response[T], not raised as exceptions."""
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

    response = await service.user.post("/profile")
    assert response.is_client_error
    assert response.status_code == 400
    assert response.data == {"msg": "unauthenticated"}


@pytest.mark.asyncio
async def test_non_json_http_exception(service, mock_httpx):
    """Non-JSON 4xx body is returned as raw string in Response.data."""
    mock_httpx.post(url__regex="/user/*", name="http_request").mock(
        side_effect=httpx.Response(
            status_code=400,
            text="<xml>helloworld</xml>",
            headers={"Content-Type": "application/xml"},
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

    response = await service.user.post("/profile")
    assert response.is_client_error
    assert response.status_code == 400
    assert response.data == "<xml>helloworld</xml>"


@pytest.mark.asyncio
async def test_non_json_response_exception(service, mock_httpx):
    mock_httpx.post(url__regex="/user/*", name="http_request").mock(
        side_effect=httpx.Response(
            status_code=200,
            text="<xml>helloworld</xml>",
            headers={"Content-Type": "application/xml"},
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

    response = await service.user.post("/profile")
    assert response.data == "<xml>helloworld</xml>"


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

    with pytest.raises(RequestError) as exc:
        await service.user.post("/profile")
    assert str(exc.value) == "request timed out"


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

    with pytest.raises(RequestError) as exc:
        await service.user.post("/profile")
    assert str(exc.value) == "error occurred while making request"


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


@pytest.mark.parametrize(
    argnames="exc_raised, expected_exc_caught, detail",
    argvalues=[
        (ArrestError("Internal Error"), HTTPException, "Something went wrong"),
        (
            ArrestHTTPException(status_code=404, data="Not found"),
            HTTPException,
            "Not found",
        ),
        (ValueError("foo is not bar"), None, None),
    ],
)
@pytest.mark.asyncio
async def test_custom_exception_handler(
    service, mocker, exc_raised, expected_exc_caught, detail
):
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


def test_response_error_str():
    """ResponseError passes message to super().__init__."""

    err = ResponseError("something went wrong")
    assert str(err) == "something went wrong"
    assert err.message == "something went wrong"


@pytest.mark.asyncio
async def test_raise_for_status_service_level(service, mock_httpx):
    """Resource with config(raise_for_status=True) raises ArrestHTTPException on non-2xx."""
    from arrest._config import ArrestConfig

    mock_httpx.post(url__regex="/user/*", name="http_request").mock(
        return_value=httpx.Response(400, json={"msg": "bad request"})
    )

    service.add_resource(
        Resource(
            route="/user",
            handlers=[("POST", "/profile")],
            config=ArrestConfig(raise_for_status=True),
        ),
    )

    with pytest.raises(ArrestHTTPException) as exc:
        await service.user.post("/profile")
    assert exc.value.status_code == 400
    assert exc.value.data == {"msg": "bad request"}


@pytest.mark.asyncio
async def test_raise_for_status_per_call(service, mock_httpx):
    """Per-call raise_for_status=True raises on non-2xx."""
    mock_httpx.post(url__regex="/user/*", name="http_request").mock(
        return_value=httpx.Response(400, json={"msg": "bad request"})
    )

    service.add_resource(
        Resource(
            route="/user",
            handlers=[("POST", "/profile")],
        )
    )

    with pytest.raises(ArrestHTTPException) as exc:
        await service.user.request(
            method="POST", path="/profile", raise_for_status=True
        )
    assert exc.value.status_code == 400
    assert exc.value.data == {"msg": "bad request"}


@pytest.mark.asyncio
async def test_raise_for_status_5xx(service, mock_httpx):
    """raise_for_status also catches 5xx."""
    mock_httpx.get(url__regex="/user/*", name="http_request").mock(
        return_value=httpx.Response(500, json={"msg": "internal error"})
    )

    service.add_resource(
        Resource(
            route="/user",
            handlers=[("GET", "")],
        )
    )

    with pytest.raises(ArrestHTTPException) as exc:
        await service.user.request(method="GET", path="", raise_for_status=True)
    assert exc.value.status_code == 500
    assert exc.value.data == {"msg": "internal error"}


@pytest.mark.asyncio
async def test_raise_for_status_success_does_not_raise(service, mock_httpx):
    """2xx with raise_for_status=True still returns Response normally."""
    mock_httpx.get(url__regex="/user/*", name="http_request").mock(
        return_value=httpx.Response(200, json={"name": "Alice"})
    )

    service.add_resource(
        Resource(
            route="/user",
            handlers=[("GET", "")],
        )
    )

    resp = await service.user.request(method="GET", path="", raise_for_status=True)
    assert resp.is_success
    assert resp.data == {"name": "Alice"}


@pytest.mark.asyncio
async def test_raise_for_status_empty_body_4xx(service, mock_httpx):
    """Empty-body 4xx with raise_for_status raises with data=None."""
    mock_httpx.delete(url__regex="/user/*", name="http_request").mock(
        return_value=httpx.Response(404, content=b"")
    )

    service.add_resource(
        Resource(
            route="/user",
            handlers=[("DELETE", "/{user_id}")],
        )
    )

    with pytest.raises(ArrestHTTPException) as exc:
        await service.user.request(method="DELETE", path="/123", raise_for_status=True)
    assert exc.value.status_code == 404
    assert exc.value.data is None


@pytest.mark.asyncio
async def test_raise_for_status_override_false(service, mock_httpx):
    """Per-call raise_for_status=False overrides resource-level True."""
    from arrest._config import ArrestConfig

    mock_httpx.get(url__regex="/user/*", name="http_request").mock(
        return_value=httpx.Response(400, json={"msg": "bad request"})
    )

    service.add_resource(
        Resource(
            route="/user",
            handlers=[("GET", "")],
            config=ArrestConfig(raise_for_status=True),
        ),
    )

    # Per-call False should override resource-level True
    resp = await service.user.request(method="GET", path="", raise_for_status=False)
    assert resp.is_client_error
    assert resp.status_code == 400
    assert resp.data == {"msg": "bad request"}
