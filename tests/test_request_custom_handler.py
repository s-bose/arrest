import httpx
import pytest
from respx.patterns import M

from arrest import Resource


@pytest.mark.asyncio
async def test_request_custom_handler(service, mock_httpx):
    patterns = [
        M(url="/user/", method__in=["GET", "POST"]),
    ]

    mock_httpx.route(*patterns, name="http_request").mock(
        return_value=httpx.Response(200, json={"status": "OK"})
    )

    mock_httpx.get(url__regex="/user/posts/*").mock(
        return_value=httpx.Response(200, json={"user": "john doe", "email": "john@doe.com"})
    )

    service.add_resource(Resource(route="/user", handlers=[("GET", "/"), ("POST", "/")]))

    @service.user.handler("/posts")
    async def get_posts(self, url, *, post_id: int):
        url = f"{url}/{post_id}"

        async with httpx.AsyncClient(**self._httpx_args) as client:
            resp = await client.get(url)

        return resp.json()

    resp1 = await service.user.get("/")
    resp2 = await service.user.post("/")
    assert resp1 == resp2 == {"status": "OK"}

    resp3 = await service.user.get_posts(post_id=123)
    assert resp3 == {"user": "john doe", "email": "john@doe.com"}
