import pytest
import respx

from arrest.service import Service
from tests import TEST_DEFAULT_SERVICE_NAME, TEST_DEFAULT_SERVICE_URL


# @pytest.fixture(scope="function", autouse=True)
# def mock_httpx_asyncclient(mocker: MockerFixture):
#     mocker.patch("httpx.AsyncClient.request", return_value={"status": "ok"})


@pytest.fixture(scope="function")
def mock_httpx():
    with respx.mock(
        base_url=TEST_DEFAULT_SERVICE_URL, assert_all_called=False
    ) as respx_mock:
        yield respx_mock


@pytest.fixture(scope="function")
def service():
    service_ = Service(name=TEST_DEFAULT_SERVICE_NAME, url=TEST_DEFAULT_SERVICE_URL)
    return service_
