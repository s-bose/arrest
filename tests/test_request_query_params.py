import httpx
import pytest
import respx
from pydantic import BaseModel, ValidationError
from respx.patterns import M

from arrest.http import Methods
from arrest.params import Query
from arrest.resource import Resource
from tests import TEST_DEFAULT_SERVICE_URL


@pytest.mark.asyncio
async def test_request_query_params(service, mock_httpx, mocker):
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

    get_matching_handler = mocker.spy(service.user, "get_matching_handler")
    extract_request_params = mocker.spy(service.user, "extract_request_params")
    await service.user.post("/profile", request=UserRequest(limit=1, q="abc"))
    handler, _ = get_matching_handler.spy_return
    assert handler.route == "/profile"
    params = extract_request_params.spy_return
    assert params.query == httpx.QueryParams({"limit": 1, "q": "abc"})


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
    with respx.mock(
        base_url=TEST_DEFAULT_SERVICE_URL, assert_all_called=False
    ) as mock:
        mock.route(
            url__regex="/user/*", name="http_request", method__in=["GET", "POST"]
        ).mock(return_value=httpx.Response(200, json={"status": "OK"}))

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
            await service.user.post(
                "/profile", request=UserRequest(limit=15, q=123.0)
            )
            await service.user.post(
                "/profile", request=UserRequest(limit=10, q="abc")
            )
