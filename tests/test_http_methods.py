import httpx
import pytest

from arrest.resource import Resource
from arrest.http import Methods


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

    print(service.test.routes)
    response = await service.test.request(f"/{route}", method=method)
    assert response == {"status": "OK"}
    assert mock_httpx["http_request"].called
    assert mock_httpx["http_request"].calls.call_count == 1
