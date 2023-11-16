import httpx
import pytest
from pydantic import BaseModel

from arrest.resource import Resource
from arrest.http import Methods
from arrest.params import Query, Path


@pytest.mark.parametrize(
    "method",
    [
        Methods.GET,
        Methods.POST,
        Methods.PUT,
        Methods.PATCH,
        Methods.DELETE,
        Methods.HEAD,
    ],
)
@pytest.mark.asyncio
async def test_http_methods(method: Methods, service, mock_httpx):
    route = str(method).lower()
    mock_httpx.request(method=method, url=f"/test/{route}", name="http_request").mock(
        return_value=httpx.Response(200, json={"status": "OK"})
    )

    service.add_resource(
        Resource(
            route="/test",
            handlers=[(method, f"/{route}")],
        )
    )

    response = await service.test.request(f"/{route}", method=method)
    assert response == {"status": "OK"}
    assert mock_httpx["http_request"].called
    assert mock_httpx["http_request"].calls.call_count == 1


@pytest.mark.asyncio
async def test_http_params(service, mock_httpx):
    class TestRequest(BaseModel):
        anything: int = Path(...)

    mock_httpx.get(url__regex="/test/get/*", name="http_request").mock(
        return_value=httpx.Response(200, json={"status": "OK"})
    )

    service.add_resource(
        Resource(
            route="/test",
            handlers=[
                (Methods.GET, "/get/{anything:int}"),
                (Methods.GET, "/get", TestRequest),
            ],
        )
    )

    response = await service.test.get("/get/2")
    assert response == {"status": "OK"}
    assert mock_httpx["http_request"].called
    assert mock_httpx["http_request"].calls.call_count == 1
