import httpx
import pytest
from arrest.resource import Resource
from arrest.service import Service
from arrest.http import Methods


@pytest.mark.asyncio
async def test_get_request(service, mock_httpx):
    mock_httpx.get("/test").mock(
        return_value=httpx.Response(200, json={"status": "OK"})
    )
    mock_httpx.post("/test/post").mock(
        return_value=httpx.Response(200, json={"status": "OK"})
    )

    service.add_resource(
        Resource(
            name="test",
            route="/test",
            handlers=[(Methods.GET, ""), (Methods.POST, "/post")],
        )
    )

    response = await service.post("/test/post")
    assert mock_httpx.calls.call_count == 1

    print(response)
    assert False

    # assert response is not None
