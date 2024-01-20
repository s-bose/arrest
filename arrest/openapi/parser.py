"""
OpenAPI Generator module

Note: only supports >=v3.0 specifications

Dependencies:
    - datamodel-code-generator
"""
import io
import itertools
import json
from pathlib import Path
from typing import IO, Optional, Union, NoReturn, Generator

import backoff
import httpx
import yaml
from datamodel_code_generator import DataModelType, InputFileType, OpenAPIScope, generate
from openapi_pydantic import OpenAPI, Server
from openapi_pydantic.v3 import v3_0_3, v3_1_0

from arrest.logging import logger
from arrest._config import PYDANTIC_V2
from arrest.defaults import MAX_RETRIES, OPENAPI_SCHEMA_FILENAME, OPENAPI_SERVICE_FILENAME
from arrest.utils import join_url
from arrest.openapi._config import Format

from arrest import Service, Resource


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

    async def generate_schema(self, fmt: Optional[Format] = None):
        openapi_bytes = await self.download_openapi_spec(self.url)
        fmt = fmt if fmt else self.url.split(".")[-1]
        openapi: OpenAPI = self.parse_openapi(fmt=fmt, data=io.BytesIO(openapi_bytes))

        schema_path = self.output_path / OPENAPI_SCHEMA_FILENAME
        service_path = self.output_path / OPENAPI_SERVICE_FILENAME

    async def _generate_schema_models(self, input_bytes: bytes, schema_path: Path | str) -> NoReturn:
        generate(
            input_=input_bytes.decode("utf-8"),
            input_file_type=InputFileType.OpenAPI,
            openapi_scopes=[OpenAPIScope.Schemas],
            output=schema_path,
            output_model_type=DataModelType.PydanticV2BaseModel
            if PYDANTIC_V2
            else DataModelType.PydanticBaseModel,
        )
        logger.info(f"generated pydantic models from schema definitions in : {schema_path}")

    def _build_arrest_service(
        self, openapi: OpenAPI, service_name: Optional[str] = None
    ) -> Generator[Service, None, None]:
        name = service_name or openapi.info.title
        name = "_".join(name.replace("-", "_").split(" "))

        for server in openapi.servers:
            for url in self._extract_url(server):
                yield Service(
                    name=name,
                    url=url,
                    description=server.description,
                )

    def _extract_url(self, server: Server) -> Generator[str, None, None]:
        url, variables = server.url, server.variables
        if not variables:
            yield url
        else:
            value_list = []
            for var in variables.values():
                values = set(var.enum) if var.enum else set()
                values.add(var.default)
                value_list.append(values)
            for values in itertools.product(*value_list):
                kwargs = {k: v for k, v in zip(variables.keys(), values)}
                yield url.format(**kwargs)

    def _build_arrest_resources(self, openapi: OpenAPI):
        ...

    @classmethod
    def load_dict(cls, fmt: Format, data: IO) -> dict:
        if fmt == "json":
            return json.load(data)
        elif fmt == "yaml":
            return yaml.load(data, yaml.SafeLoader)

    @classmethod
    def parse_openapi(cls, fmt: Format, data: IO) -> OpenAPI:
        spec = cls.load_dict(fmt, data)

        if spec["openapi"].startswith("3.1"):
            return v3_1_0.OpenAPI(**spec)
        elif spec["openapi"].startswith("3.0"):
            return v3_0_3.OpenAPI(**spec)
