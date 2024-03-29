import httpx
import pytest
from pydantic import BaseModel, ConfigDict
from respx.patterns import M

from arrest._config import PYDANTIC_V2
from arrest.http import Methods
from arrest.params import Header
from arrest.resource import Resource


@pytest.mark.asyncio
async def test_header_params(service, mock_httpx, mocker):
    patterns = [
        M(url__regex="/user/*", method__in=["GET"]),
    ]

    mock_httpx.route(*patterns, name="http_request").mock(
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

    extract_request_params = mocker.spy(service.user, "extract_request_params")
    await service.user.get("/profile", headers={"x-header": "123"})

    params = extract_request_params.spy_return
    assert params.header == httpx.Headers(
        {
            "x-header": "123",
        }
    )


@pytest.mark.asyncio
async def test_header_params_in_request(service, mock_httpx, mocker):
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

    extract_request_params = mocker.spy(service.user, "extract_request_params")
    await service.user.get(
        "/profile",
        request=UserRequest(x_user_agent="mozila", name="abc", email="abc@email.com", password="123"),
        headers={"x-header": "123"},
    )

    params = extract_request_params.spy_return
    assert params.header == httpx.Headers(
        {
            "x-header": "123",
            "x-user-agent": "mozila",
        }
    )
