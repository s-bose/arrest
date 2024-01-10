"""
OpenAPI Generator module

Note: only supports >=v3.0 specifications

Dependencies:
    - datamodel-code-generator
"""

import json
from pathlib import Path
from typing import IO, Literal, Optional, Union

import backoff
import httpx
import yaml
from datamodel_code_generator import DataModelType, InputFileType, OpenAPIScope, generate

from arrest._config import PYDANTIC_V2
from arrest.defaults import MAX_RETRIES
from arrest.utils import join_url

# from openapi_pydantic import OpenAPI
# from openapi_pydantic.v3 import v3_0_3, v3_1_0


# from arrest import Service, Resource


class OpenAPIGenerator:
    def __init__(
        self,
        base_url: Optional[str] = None,
        *,
        openapi_path: str,
        output_path: Optional[Union[str, Path]] = None,
    ) -> None:
        self.url = join_url(base_url, openapi_path) if base_url else openapi_path
        self.output_path = output_path

    @classmethod
    def load_dict(cls, format: Literal["json", "yaml"], spec: IO) -> dict:
        if format == "json":
            return json.load(spec)
        elif format == "yaml":
            return yaml.load(spec, yaml.SafeLoader)

    # @classmethod
    # def parse_openapi(format: Literal["json", "yaml"], data: IO) -> OpenAPI:
    #     spec = OpenAPIGenerator.load_dict(format, data)

    #     if spec["openapi"].startswith("3.1"):
    #         return v3_1_0.OpenAPI(**spec)
    #     elif spec["openapi"].startswith("3.0"):
    #         return v3_0_3.OpenAPI(**spec)

    @backoff.on_exception(
        backoff.expo,
        (httpx.HTTPError, httpx.TimeoutException),
        max_tries=MAX_RETRIES,
        jitter=backoff.full_jitter,
    )
    async def download_openapi_spec(self, url: str) -> bytes:
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.read()

    async def generate_schema(self):
        openapi_bytes = await self.download_openapi_spec(self.url)

        # filepath = Path(Path.cwd() / "model.py")

        generate(
            input_=openapi_bytes.decode("utf-8"),
            input_file_type=InputFileType.OpenAPI,
            openapi_scopes=[OpenAPIScope.Schemas],
            output=...,
            output_model_type=DataModelType.PydanticV2BaseModel
            if PYDANTIC_V2
            else DataModelType.PydanticBaseModel,
        )
