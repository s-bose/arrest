import httpx
import pytest

from arrest.http import Methods
from arrest.resource import Resource


@pytest.mark.parametrize(
    "method",
    [
        Methods.GET,
        Methods.POST,
        Methods.PUT,
        Methods.PATCH,
        Methods.DELETE,
        Methods.HEAD,
        Methods.OPTIONS,
    ],
)
@pytest.mark.asyncio
async def test_request_http_methods(method: Methods, service, mock_httpx):
    route = str(method).lower()

    mock_httpx.request(method=method, url=f"/test/{route}", name="http_request").mock(
        return_value=httpx.Response(200, json={"status": "OK"})
    )

    service.add_resource(
        Resource(
            route="/test",
            handlers=[(method, f"/{route}"), (Methods.GET, "/{anything:int}")],
        )
    )

    response = await service.test.request(method, f"/{route}")

    assert response == {"status": "OK"}
    assert mock_httpx["http_request"].called
    assert mock_httpx["http_request"].calls.call_count == 1


@pytest.mark.parametrize(
    "method",
    [
        Methods.GET,
        Methods.POST,
        Methods.PUT,
        Methods.PATCH,
        Methods.DELETE,
        Methods.HEAD,
        Methods.OPTIONS,
    ],
)
@pytest.mark.asyncio
async def test_request_http_methods_helpers(service, mock_httpx, method):
    mock_httpx.request(method=method, url__regex="/test/*", name="http_request").mock(
        return_value=httpx.Response(200, json={"status": "OK"})
    )

    service.add_resource(
        Resource(
            route="/test",
            handlers=[(method, "/")],
        )
    )

    response = None
    match method:
        case Methods.GET:
            response = await service.test.get("/")
        case Methods.POST:
            response = await service.test.post("/")
        case Methods.PUT:
            response = await service.test.put("/")
        case Methods.PATCH:
            response = await service.test.patch("/")
        case Methods.DELETE:
            response = await service.test.delete("/")
        case Methods.HEAD:
            response = await service.test.head("/")
        case Methods.OPTIONS:
            response = await service.test.options("/")

    assert response == {"status": "OK"}
