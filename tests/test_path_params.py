import uuid
from datetime import datetime
from typing import Any

import pytest

from arrest.http import Methods
from arrest.resource import Resource

base_url = "/user"
dummy_uuid = uuid.uuid4()
dummy_date = datetime.now()


@pytest.mark.parametrize(
    "url, path_param_kwargs, expected_path",
    [
        ("/profile/{profile_id}", {"profile_id": 123}, f"{base_url}/profile/123"),
        (
            "/profile/{profile_id:str}",
            {"profile_id": 123},
            f"{base_url}/profile/123",
        ),
        (
            "/profile/{profile_id:int}",
            {"profile_id": 123},
            f"{base_url}/profile/123",
        ),
        (
            "/profile/{profile_id:int}/",
            {"profile_id": 123},
            f"{base_url}/profile/123/",
        ),
        (
            "/profile/{profile_id:float}",
            {"profile_id": 145},
            f"{base_url}/profile/145",
        ),
        (
            "/profile/{profile_id:float}",
            {"profile_id": 145.56},
            f"{base_url}/profile/145.56000000000000227374",
        ),
        (
            "/profile/{profile_id:float}/",
            {"profile_id": 145.56},
            f"{base_url}/profile/145.56000000000000227374/",
        ),
        (
            "/profile/{profile_id:uuid}",
            {"profile_id": "4d96597f-5d49-4ec0-a400-a4a01efd4b53"},
            f"{base_url}/profile/4d96597f-5d49-4ec0-a400-a4a01efd4b53",
        ),
        (
            "/profile/{profile_id:uuid}",
            {"profile_id": dummy_uuid},
            f"{base_url}/profile/{str(dummy_uuid)}",
        ),
        (
            "/profile/{profile_id:uuid}/",
            {"profile_id": dummy_uuid},
            f"{base_url}/profile/{str(dummy_uuid)}/",
        ),
    ],
)
def test_path_params_kwargs(
    service,
    url: str,
    path_param_kwargs: dict[str, Any],
    expected_path: str,
):
    service.add_resource(
        Resource(
            route="/user",
            handlers=[
                (Methods.POST, url),
            ],
        )
    )
    _, parsed_path = service.user.get_matching_handler(method="POST", path="/profile/", **path_param_kwargs)

    assert parsed_path == expected_path


@pytest.mark.parametrize(
    "handler_route, request_path, expected_path",
    [
        ("/profile/{profile_id}", "/profile/123", f"{base_url}/profile/123"),
        (
            "/profile/{profile_id:str}",
            "/profile/123",
            f"{base_url}/profile/123",
        ),
        (
            "/profile/{profile_id:str}/",
            "/profile/123/",
            f"{base_url}/profile/123/",
        ),
        (
            "/profile/{profile_id:int}",
            "/profile/123",
            f"{base_url}/profile/123",
        ),
        (
            "/profile/{profile_id:int}/",
            "/profile/123/",
            f"{base_url}/profile/123/",
        ),
        (
            "/profile/{profile_id:float}",
            "/profile/145",
            f"{base_url}/profile/145",
        ),
        (
            "/profile/{profile_id:float}",
            f"/profile/{145.56}",
            f"{base_url}/profile/145.56",
        ),
        (
            "/profile/{profile_id:float}/",
            f"/profile/{145.56}/",
            f"{base_url}/profile/145.56/",
        ),
        (
            "/profile/{profile_id:uuid}",
            "/profile/4d96597f-5d49-4ec0-a400-a4a01efd4b53",
            f"{base_url}/profile/4d96597f-5d49-4ec0-a400-a4a01efd4b53",
        ),
        (
            "/profile/{profile_id:uuid}",
            f"/profile/{dummy_uuid}",
            f"{base_url}/profile/{str(dummy_uuid)}",
        ),
        (
            "/profile/{profile_id:uuid}/",
            f"/profile/{dummy_uuid}/",
            f"{base_url}/profile/{str(dummy_uuid)}/",
        ),
    ],
)
def test_path_params_str(service, handler_route, request_path, expected_path):
    service.add_resource(
        Resource(
            route="/user",
            handlers=[
                (Methods.GET, handler_route),
            ],
        )
    )
    _, parsed_path = service.user.get_matching_handler(method="GET", path=request_path)

    assert parsed_path == expected_path


@pytest.mark.parametrize(
    "method, request_path, kwargs, expected_handler_route",
    [
        ("GET", "/posts", {}, "/posts"),
        ("GET", "/posts/", {}, None),
        ("POST", "/posts/", {}, None),
        ("GET", "/posts", {"foo": 123}, "/posts/{foo:int}"),
        ("GET", "/posts/", {"foo": 123}, "/posts/{foo:int}"),
        ("GET", "/posts/", {"foo": "notanumber"}, None),
        (
            "GET",
            "/posts",
            {"foo": 123, "bar": 456},
            "/posts/{foo:int}/comments/{bar:int}",
        ),
        (
            "GET",
            "/posts/",
            {"foo": 123, "bar": 456},
            "/posts/{foo:int}/comments/{bar:int}",
        ),
        ("GET", "/posts/", {"xyz": "abc"}, None),
        ("GET", "/xyz", {"ping": "pong"}, None),
    ],
)
def test_path_params_kwargs_multiple_handlers(service, method, request_path, kwargs, expected_handler_route):
    service.add_resource(
        Resource(
            route="/user",
            handlers=[
                (Methods.GET, "/posts"),
                (Methods.GET, "/posts/{foo:int}"),
                (Methods.GET, "/posts/{foo:int}/comments/{bar:int}"),
            ],
        )
    )

    result = service.user.get_matching_handler(method=method, path=request_path, **kwargs)
    if result is not None:
        assert result[0].route == expected_handler_route
    else:
        assert result is expected_handler_route


@pytest.mark.parametrize(
    "method, request_path, expected_handler_route",
    [
        ("GET", "/posts", "/posts"),
        ("GET", "/posts/", None),
        ("POST", "/posts/", None),
        ("GET", "/posts/123", "/posts/{foo:int}"),
        ("GET", "/posts/123/", None),
        ("GET", "/posts/notanumber", None),
        (
            "GET",
            "/posts/123/comments/456",
            "/posts/{foo:int}/comments/{bar:int}",
        ),
        ("GET", "/posts/123/comments/456/", None),
        ("GET", "/posts/123/comments", None),
        ("GET", "/posts/123/comments/", None),
        ("GET", "/posts/123/xyz", None),
        ("GET", "/xyz", None),
    ],
)
def test_path_params_fstrings_multiple_handlers(service, method, request_path, expected_handler_route):
    service.add_resource(
        Resource(
            route="/user",
            handlers=[
                (Methods.GET, "/posts"),
                (Methods.GET, "/posts/{foo:int}"),
                (Methods.GET, "/posts/{foo:int}/comments/{bar:int}"),
            ],
        )
    )

    result = service.user.get_matching_handler(method=method, path=request_path)
    if result is not None:
        assert result[0].route == expected_handler_route
    else:
        assert result is expected_handler_route
