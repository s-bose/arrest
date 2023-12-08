import asyncio
from typing import Any

import httpx
import pytest
from pydantic import BaseModel

from arrest.handler import ResourceHandler
from arrest.http import Methods
from arrest.resource import Resource


class ResponseType(BaseModel):
    a: int
    b: int
    c: str


@pytest.mark.parametrize("response_type, expected_type", [(ResponseType, ResponseType), (None, dict)])
@pytest.mark.asyncio
async def test_request_callback(
    service,
    mock_httpx,
    response_type: BaseModel | None,
    expected_type: dict | None,
):
    mock_httpx.get(url__regex="/user/*", name="http_request").mock(
        return_value=httpx.Response(200, json={"a": 1, "b": 2, "c": "str"})
    )

    def sync_callback(arg: Any):
        return arg

    service.add_resource(
        Resource(
            route="/user",
            handlers=[
                ResourceHandler(
                    method=Methods.GET,
                    route="/",
                    response=response_type,
                    callback=sync_callback,
                )
            ],
        )
    )

    response = await service.user.get("/")
    assert isinstance(response, expected_type)


@pytest.mark.parametrize("response_type, expected_type", [(ResponseType, ResponseType), (None, dict)])
@pytest.mark.asyncio
async def test_request_callback_async(
    service,
    mock_httpx,
    response_type: BaseModel | None,
    expected_type: dict | None,
):
    mock_httpx.get(url__regex="/user/*", name="http_request").mock(
        return_value=httpx.Response(200, json={"a": 1, "b": 2, "c": "str"})
    )

    async def async_callback(arg: Any):
        await asyncio.sleep(1)
        return arg

    service.add_resource(
        Resource(
            route="/user",
            handlers=[
                ResourceHandler(
                    method=Methods.GET,
                    route="/",
                    response=response_type,
                    callback=async_callback,
                )
            ],
        )
    )

    response = await service.user.get("/")
    assert isinstance(response, expected_type)


@pytest.mark.asyncio
async def test_request_callback_exception(
    service,
    mock_httpx,
):
    mock_httpx.get(url__regex="/user/*", name="http_request").mock(
        return_value=httpx.Response(200, json={"a": 1, "b": 2, "c": "str"})
    )

    async def sync_callback(_: Any):
        raise ValueError("foo is bar")

    service.add_resource(
        Resource(
            route="/user",
            handlers=[
                ResourceHandler(
                    method=Methods.GET,
                    route="/",
                    callback=sync_callback,
                )
            ],
        )
    )

    with pytest.raises(ValueError):
        await service.user.get("/")
