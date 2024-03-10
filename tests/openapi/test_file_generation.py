import os
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
from httpx import Response

from arrest.common import StrEnum
from arrest.exceptions import ArrestError
from arrest.openapi import OpenAPIGenerator
from tests import TEST_DEFAULT_SERVICE_URL

FIXTURE_PATH = Path("tests/fixtures")


class FileNames(StrEnum):
    RESOURCE = "resources.py"
    SERVICE = "services.py"
    MODEL = "models.py"
    INIT = "__init__.py"


def validate_file_contents(src_dir: str, dst_dir: str, filename: FileNames) -> bool:
    with open(os.path.join(src_dir, filename)) as f1, open(os.path.join(dst_dir, filename)) as f2:
        for line1, line2 in zip(f1, f2):
            line1, line2 = line1.strip().replace("'", '"'), line2.strip().replace("'", '"')
            if line1.startswith("#") and line2.startswith("#"):
                continue
            if line1 != line2:
                return False

        return True


@pytest.mark.parametrize(
    "fixture_dir, fixture_file",
    [
        ("v3", "openapi_petstore.json"),
        ("v3.1", "openapi_petstore_3.1.json"),
        ("v3", "openapi_petstore.yaml"),
        ("v3.1", "openapi_petstore_3.1.yaml"),
        ("v3.1_with_root", "openapi_petstore_3.1_with_root.json"),
    ],
)
@pytest.mark.asyncio
async def test_openapi_generate_from_file(fixture_dir, fixture_file):
    filepath = os.path.join(FIXTURE_PATH, fixture_file)

    with TemporaryDirectory() as tempdir:
        openapi = OpenAPIGenerator(url=filepath, output_path=tempdir)
        openapi.generate_schema()

        dir_name, _, generated_files = list(os.walk(tempdir))[-1]
        assert set(list(FileNames)) == set(generated_files)

        fixture_dir = os.path.join(FIXTURE_PATH, "generated", fixture_dir)
        for filename in list(FileNames):
            assert validate_file_contents(src_dir=dir_name, dst_dir=fixture_dir, filename=filename)


@pytest.mark.parametrize(
    "openapi_version, url_stub, fixture_file",
    [
        ("v3", "openapi.json", "openapi_petstore.json"),
        ("v3.1", "openapi_3.1.json", "openapi_petstore_3.1.json"),
        ("v3", "openapi.yaml", "openapi_petstore.yaml"),
        ("v3.1", "openapi_3.1.yaml", "openapi_petstore_3.1.yaml"),
    ],
)
@pytest.mark.asyncio
async def test_openapi_generate_from_http(openapi_version, url_stub, fixture_file, mock_httpx):
    filepath = os.path.join(FIXTURE_PATH, fixture_file)
    with open(filepath, "rb") as file:
        mock_httpx.get(url=url_stub).mock(return_value=Response(200, content=file.read()))

    with TemporaryDirectory() as tempdir:
        openapi = OpenAPIGenerator(url=f"{TEST_DEFAULT_SERVICE_URL}/{url_stub}", output_path=tempdir)
        openapi.generate_schema()

        dir_name, _, generated_files = list(os.walk(tempdir))[-1]
        assert set(list(FileNames)) == set(generated_files)

        fixture_dir = os.path.join(FIXTURE_PATH, "generated", openapi_version)
        for filename in list(FileNames):
            assert validate_file_contents(src_dir=dir_name, dst_dir=fixture_dir, filename=filename)


@pytest.mark.asyncio
async def test_generate_invalid_file():
    filepath = os.path.join(FIXTURE_PATH, "openapi_petstore.json")

    openapi = OpenAPIGenerator(url=filepath, output_path="/does/not/exist")
    with pytest.raises(ArrestError):
        openapi.generate_schema()
