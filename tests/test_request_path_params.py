import uuid
import httpx
import pytest
from respx.patterns import M

from arrest.resource import Resource
from arrest.http import Methods


@pytest.mark.parametrize(
    "route, method, kwargs, handler_expected_route, handler_expected_method",
    [
        ("/", Methods.GET, None, "/", Methods.GET),
        ("/", Methods.GET, {"user_id": 2}, "/{user_id:int}", Methods.GET),
        ("/2", Methods.GET, None, "/{user_id:int}", Methods.GET),
        ("/profile", Methods.GET, None, "/profile", Methods.GET),
        ("/profile/2", Methods.GET, None, "/profile/{id:int}", Methods.GET),
        ("/profile", Methods.POST, None, "/profile", Methods.POST),
        ("/profile", Methods.GET, {"id": 2}, "/profile/{id:int}", Methods.GET),
        ("/profile/", Methods.GET, {"id": 2}, "/profile/{id:int}", Methods.GET),
        ("/profile", Methods.GET, {"id": "2"}, "/profile/{id:int}", Methods.GET),
        (
            "/profile/2/badges/",
            Methods.GET,
            {"badge_id": uuid.uuid4()},
            "/profile/{id:int}/badges/{badge_id:uuid}",
            Methods.GET,
        ),
        (
            f"/profile/2/badges/{uuid.uuid4()}",
            Methods.GET,
            None,
            "/profile/{id:int}/badges/{badge_id:uuid}",
            Methods.GET,
        ),
    ],
)
@pytest.mark.asyncio
async def test_request_path_params(
    service,
    mock_httpx,
    mocker,
    route: str,
    method: Methods,
    kwargs: dict,
    handler_expected_route: str,
    handler_expected_method: Methods,
):
    patterns = [
        M(url__regex="/user/*", method__in=["GET", "POST"]),
    ]

    mock_httpx.route(*patterns, name="http_request").mock(
        return_value=httpx.Response(200, json={"status": "OK"})
    )

    service.add_resource(
        Resource(
            route="/user",
            handlers=[
                (Methods.GET, "/"),
                (Methods.GET, "/{user_id:int}"),
                (Methods.GET, "/profile"),
                (Methods.GET, "/profile/{id:int}"),
                (Methods.POST, "/profile"),
                (Methods.GET, "/profile/{id:int}/badges/{badge_id:uuid}"),
            ],
        )
    )

    get_matching_handler = mocker.spy(service.user, "get_matching_handler")
    if kwargs:
        await service.user.request(url=route, method=method, **kwargs)
    else:
        await service.user.request(url=route, method=method)

    handler, _ = get_matching_handler.spy_return
    assert handler.route == handler_expected_route
    assert handler.method == handler_expected_method
