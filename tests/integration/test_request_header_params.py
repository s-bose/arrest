import httpx
import pytest
from pydantic import BaseModel, ConfigDict
from respx.patterns import M

from arrest._config import PYDANTIC_V2
from arrest.http import Methods
from arrest.params import Body, Header
from arrest.resource import Resource


@pytest.mark.parametrize(
    "resource_header, kwarg_header, expected_result",
    [
        (
            {"x-resource-header": "123"},
            None,
            {
                "x-max-age": "20",
                "x-user-agent": "mozila",
                "x-resource-header": "123",
            },
        ),
        (
            None,
            {"x-kwarg-header": "abc"},
            {
                "x-max-age": "20",
                "x-user-agent": "mozila",
                "x-kwarg-header": "abc",
            },
        ),
        (
            {"x-resource-header": "123"},
            {"x-kwarg-header": "abc"},
            {
                "x-max-age": "20",
                "x-user-agent": "mozila",
                "x-kwarg-header": "abc",
                "x-resource-header": "123",
            },
        ),
    ],
)
@pytest.mark.asyncio
async def test_request_header_params(service, mock_httpx, resource_header, kwarg_header, expected_result):
    patterns = [
        M(url__regex="/user/*", method__in=["POST"]),
    ]

    mock_httpx.route(*patterns, name="http_request").mock(
        return_value=httpx.Response(200, json={"status": "OK"})
    )

    class UserRequest(BaseModel):
        if PYDANTIC_V2:
            x_max_age: str = Header(serialization_alias="x-max-age")
            x_user_agent: str = Header(serialization_alias="x-user-agent")
        else:
            x_max_age: str = Header(alias="x-max-age")
            x_user_agent: str = Header(alias="x-user-agent")

        name: str = Body(...)
        email: str
        password: str

        if PYDANTIC_V2:
            model_config = ConfigDict(populate_by_name=True)
        else:

            class Config:
                allow_population_by_field_name = True

    service.add_resource(
        Resource(
            route="/user",
            handlers=[
                (Methods.POST, "/profile", UserRequest),
            ],
            headers=resource_header,
        )
    )
    await service.user.post(
        "/profile",
        request=UserRequest(
            name="bob",
            email="bob@mail.com",
            password="xyz",
            x_max_age="20",
            x_user_agent="mozila",
        ),
        headers=kwarg_header,
    )

    req: httpx.Request = mock_httpx["http_request"].calls[0].request
    headers = req.headers

    for key, value in expected_result.items():
        assert key in headers
        assert headers[key] == value


@pytest.mark.asyncio
async def test_request_header_params_arguments(service, mock_httpx):
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

    await service.user.get("/profile", headers={"x-header": "123"})
    request: httpx.Request = mock_httpx["http_request"].calls[0].request

    request_headers = httpx.Headers(request.headers)
    assert request_headers["x-header"] == "123"


@pytest.mark.asyncio
async def test_header_params_in_both_request_model_and_arguments(service, mock_httpx):
    patterns = [
        M(url__regex="/user/*", method__in=["GET"]),
    ]

    mock_httpx.route(*patterns, name="http_request").mock(
        return_value=httpx.Response(200, json={"status": "OK"})
    )

    class UserRequest(BaseModel):
        if PYDANTIC_V2:
            x_user_agent: str = Header(serialization_alias="x-user-agent")
        else:
            x_user_agent: str = Header(alias="x-user-agent")

        name: str
        email: str
        password: str

        if PYDANTIC_V2:
            model_config = ConfigDict(populate_by_name=True)

        else:

            class Config:
                allow_population_by_field_name = True

    service.add_resource(
        Resource(
            route="/user",
            handlers=[
                (Methods.GET, "/profile", UserRequest),
            ],
        )
    )

    await service.user.get(
        "/profile",
        request=UserRequest(x_user_agent="mozila", name="abc", email="abc@email.com", password="123"),
        headers={"x-header": "123"},
    )

    request: httpx.Request = mock_httpx["http_request"].calls[0].request

    request_headers = httpx.Headers(request.headers)
    assert request_headers["x-header"] == "123"
    assert request_headers["x-user-agent"] == "mozila"
