import httpx
import pytest
from respx.patterns import M

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


@pytest.mark.asyncio
async def test_request_path_params(service, mock_httpx, mocker):
    pattern = M(url__regex="/user/profile/*", method__in=["GET", "POST"])

    mock_httpx.route(pattern, name="http_request").mock(
        return_value=httpx.Response(200, json={"status": "OK"})
    )

    service.add_resource(
        Resource(
            route="/user",
            handlers=[
                (Methods.GET, "/profile"),
                (Methods.GET, "/profile/{id:int}"),
                (Methods.POST, "/profile"),
            ],
        )
    )

    get_matching_handler = mocker.spy(service.user, "get_matching_handler")
    await service.user.get("/profile")
    handler, _ = get_matching_handler.spy_return
    assert handler.route == "/profile"

    await service.user.get("/profile/2")
    handler, _ = get_matching_handler.spy_return
    assert handler.route == "/profile/{id:int}"

    await service.user.get("/profile", id=2)
    handler, _ = get_matching_handler.spy_return
    assert handler.route == "/profile/{id:int}"

    await service.user.get("/profile", id="2")
    handler, _ = get_matching_handler.spy_return
    assert handler.route == "/profile/{id:int}"

    await service.user.post("/profile")
    handler, _ = get_matching_handler.spy_return
    assert handler.route == "/profile"
    assert handler.method == "POST"
