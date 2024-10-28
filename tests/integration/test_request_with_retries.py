import httpx
import pytest

from arrest import Resource, Service
from arrest.exceptions import ArrestHTTPException
from tests import TEST_DEFAULT_SERVICE_NAME, TEST_DEFAULT_SERVICE_URL


@pytest.mark.asyncio
async def test_mrequest_with_retry_http_transport(mock_httpx):
    mock_httpx.get(url__regex="/user", name="http_request").mock(
        side_effect=httpx.TimeoutException(message="connection timed out")
    )

    service = Service(
        name=TEST_DEFAULT_SERVICE_NAME,
        url=TEST_DEFAULT_SERVICE_URL,
        resources=[
            Resource(
                route="/user",
            )
        ],
        transport=httpx.AsyncHTTPTransport(retries=3),
    )

    with pytest.raises(ArrestHTTPException):
        await service.user.get("")

    assert mock_httpx["http_request"].call_count == 1
    # https://github.com/lundberg/respx/issues/141
    # httpx with retry at transport only configures the client to make
    # N socket connection `attempts`

    # assert mock_httpx["http_request"].call_count == 3


@pytest.mark.asyncio
async def test_request_with_arrest_retry(mock_httpx):
    mock_httpx.get(url__regex="/user", name="http_request").mock(
        side_effect=httpx.TimeoutException(message="connection timed out")
    )

    service = Service(
        name=TEST_DEFAULT_SERVICE_NAME,
        url=TEST_DEFAULT_SERVICE_URL,
        resources=[
            Resource(route="/user"),
        ],
        retry=3,
    )

    with pytest.raises(ArrestHTTPException):
        await service.user.get("")

    assert mock_httpx["http_request"].call_count == 3


@pytest.mark.asyncio
async def test_request_with_manual_retry(mock_httpx):
    from tenacity import retry, stop_after_attempt

    mock_httpx.get(url__regex="/user", name="http_request").mock(
        side_effect=httpx.TimeoutException(message="connection timed out")
    )

    service = Service(
        name=TEST_DEFAULT_SERVICE_NAME,
        url=TEST_DEFAULT_SERVICE_URL,
        resources=[
            Resource(
                route="/user",
            )
        ],
        transport=httpx.AsyncHTTPTransport(retries=3),
    )

    @retry(stop=stop_after_attempt(3), reraise=True)
    async def get_with_retry():
        await service.user.get("")

    with pytest.raises(ArrestHTTPException):
        await get_with_retry()

    assert mock_httpx["http_request"].call_count == 3
