import httpx
import pytest
from respx.patterns import M

from arrest import Resource


@pytest.mark.asyncio
async def test_decorate_custom_handler_within_service_scope(service, mock_httpx):
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
    resp4 = await get_posts(post_id=456)
    assert resp3 == resp4 == {"user": "john doe", "email": "john@doe.com"}


@pytest.mark.asyncio
async def test_decorate_custom_handler_outside_service_scope(service, mock_httpx):
    patterns = [
        M(url="/user/", method__in=["GET", "POST"]),
    ]

    mock_httpx.route(*patterns, name="http_request").mock(
        return_value=httpx.Response(200, json={"status": "OK"})
    )

    mock_httpx.get(url__regex="/user/posts/*").mock(
        return_value=httpx.Response(200, json={"user": "john doe", "email": "john@doe.com"})
    )

    user = Resource(route="/user", handlers=[("GET", "/"), ("POST", "/")])

    # only using the `user` resource for decorator
    @user.handler("/posts")
    async def get_posts(self, url, *, post_id: int):
        url = f"{url}/{post_id}"
        async with httpx.AsyncClient(**self._httpx_args) as client:
            resp = await client.get(url)

        return resp.json()

    service.add_resource(user)

    # predefined handler routes
    resp1 = await service.user.get("/")
    resp2 = await service.user.post("/")
    assert resp1 == resp2 == {"status": "OK"}

    # using the custom handler func
    resp3 = await service.user.get_posts(post_id=123)
    resp4 = await get_posts(post_id=456)
    assert resp3 == resp4 == {"user": "john doe", "email": "john@doe.com"}
