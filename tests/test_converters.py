from typing import Any
import uuid
from datetime import datetime
import httpx
import pytest


import arrest
from arrest.resource import Resource
from arrest.http import Methods
from arrest.converters import add_converter, Converter

base_url = "http://example.com/user"
dummy_uuid = uuid.uuid4()
dummy_date = datetime.now()


# class DatetimeConverter(Converter[datetime]):
#     regex = r"\s+(?=\d{2}(?:\d{2})?-\d{1,2}-\d{1,2}\b)"

#     def to_str(self, value: datetime) -> str:
#         return str(value)


# add_converter(DatetimeConverter, "datetime")


@pytest.mark.parametrize(
    "url, path_param_kwargs, expected_path",
    [
        ("/profile/{profile_id}", {"profile_id": 123}, f"{base_url}/profile/123"),
        ("/profile/{profile_id:str}", {"profile_id": 123}, f"{base_url}/profile/123"),
        ("/profile/{profile_id:int}", {"profile_id": 123}, f"{base_url}/profile/123"),
        ("/profile/{profile_id:float}", {"profile_id": 145}, f"{base_url}/profile/145"),
        (
            "/profile/{profile_id:float}",
            {"profile_id": 145.56},
            f"{base_url}/profile/145.56000000000000227374",
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
            "/profile/{profile_id:int}/comments/{comment_id:int}",
            {"profile_id": 123, "comment_id": 456},
            f"{base_url}/profile/123/comments/456",
        ),
        (
            "/profile/{pdate:datetime}",
            {"pdate": dummy_date},
            f"{base_url}/profile/{dummy_date.strftime('%Y-%m-%dT%H:%M:%S')}",
        ),
    ],
)
@pytest.mark.asyncio
async def test_converter_path_params(
    service,
    mock_httpx,
    mocker,
    url: str,
    path_param_kwargs: dict[str, Any],
    expected_path: str,
):
    mock_httpx.post(url__regex="/user/*", name="http_request").mock(
        return_value=httpx.Response(status_code=200, json={"status": "OK"})
    )

    service.add_resource(
        Resource(
            route="/user",
            handlers=[
                (Methods.POST, url),
            ],
        )
    )

    class DatetimeConverter(Converter[datetime]):
        regex = "[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(.[0-9]+)?"

        def to_str(self, value: datetime) -> str:
            return value.strftime("%Y-%m-%dT%H:%M:%S")

    add_converter(DatetimeConverter(), "datetime")

    replace_params = mocker.spy(arrest.resource, "replace_params")
    await service.user.post("/profile", **path_param_kwargs)
    response = replace_params.spy_return

    assert response[0] == expected_path
