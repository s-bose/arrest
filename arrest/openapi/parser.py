"""
OpenAPI Generator module

Note: only supports >=v3.0 specifications

Dependencies:
    - datamodel-code-generator
"""
from typing import IO, Generator, Optional, Union, Any
import os
import importlib
import io
import itertools
import json
from pathlib import Path
from functools import lru_cache

import backoff
import httpx
import yaml
from datamodel_code_generator import DataModelType, InputFileType, OpenAPIScope, generate
from arrest.utils import join_url

from arrest.http import Methods
from arrest import Resource, Service
from arrest._config import PYDANTIC_V2
from arrest.defaults import MAX_RETRIES, OPENAPI_SCHEMA_FILENAME, SERVICE_FILENAME, RESOURCE_FILENAME
from arrest.logging import logger
from arrest.openapi._config import Format
from arrest.openapi.spec import OpenAPI, Server, PathItem, Operation, Response, Reference
from arrest.openapi.utils import get_ref_schema


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
    async def download_openapi_spec(self) -> bytes:
        if self.url.startswith("http"):
            async with httpx.AsyncClient() as client:
                response = await client.get(self.url)
                response.raise_for_status()
                return response.read()

        else:
            with open(self.url, "rb", encoding="utf-8") as file:
                return file.read()

    async def generate_schema(self, fmt: Optional[Format] = None):
        openapi_bytes = await self.download_openapi_spec()
        fmt = fmt if fmt else self.url.split(".")[-1]
        openapi: OpenAPI = self.parse_openapi(fmt=fmt, data=io.BytesIO(openapi_bytes))

        schema_path = self.output_path / OPENAPI_SCHEMA_FILENAME
        service_path = self.output_path / SERVICE_FILENAME
        resource_path = self.output_path / RESOURCE_FILENAME

        schema_module = await self._generate_schema_models(input_bytes=openapi_bytes, schema_path=schema_path)
        return list(self._build_arrest_resources(openapi=openapi, schema_module=schema_module))

    async def _generate_schema_models(self, input_bytes: bytes, schema_path: Path | str) -> None:
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

    def _build_arrest_resources(self, openapi: OpenAPI, schema_module: Any):
        def prefix(path: str) -> str:
            """
            ("/root/xyz/123") -> "root"
            ("/root/{id}") -> "root"
            """
            return path[1:].split("/")[0]

        if not openapi.paths:
            return None

        for key, group in itertools.groupby(openapi.paths.keys(), key=prefix):
            routes = list(group)
            path_items = [openapi.paths.get(route) for route in routes]
            handlers = []
            for route, path_item in zip(routes, path_items):
                route = route.removeprefix(f"/{key}")
                handlers.extend(
                    self._build_handlers(route=route, path_item=path_item, schema_module=schema_module)
                )
            yield Resource(name=key, route=f"/{key}", handlers=handlers)

    def _build_handlers(self, route: str, path_item: PathItem, schema_module: Any) -> list[tuple]:
        handlers = []
        for method in list(Methods):
            operation: Operation
            if operation := getattr(path_item, str(method).lower(), None):
                request_class = self.get_request_schema(operation, schema_module)
                response_class = self.get_response_schema(operation, schema_module)

                handlers.append((method, route, request_class, response_class))

        return handlers

    def get_request_schema(self, operation: Operation, module: Any) -> Optional[Any]:
        if not (request_body := operation.requestBody):
            logger.debug("no request body defined")
            return None

        request_schema = None
        if isinstance(request_body, Reference):
            request_schema = get_ref_schema(request_body)

        if media := request_body.content.get("application/json", None):
            request_schema = get_ref_schema(media.media_type_schema)

        return module.__dict__.get(request_schema, None)

    def get_response_schema(self, operation: Operation, module: Any) -> Optional[Any]:
        if not operation.responses or not (
            success_response := operation.responses.get(str(httpx.codes.OK), None)
        ):
            logger.debug("no success (200) response defined")
            return None

        if isinstance(success_response, Reference):
            response_schema = get_ref_schema(success_response)

        if success_response.content and (media := success_response.content.get("application/json", None)):
            response_schema = get_ref_schema(media.media_type_schema)

        return module.__dict__.get(response_schema)

    @classmethod
    def load_dict(cls, fmt: Format, data: IO) -> dict:
        if fmt == "json":
            return json.load(data)
        elif fmt == "yaml":
            return yaml.load(data, yaml.SafeLoader)

    @classmethod
    def parse_openapi(cls, fmt: Format, data: IO) -> OpenAPI:
        spec = cls.load_dict(fmt, data)
        return OpenAPI(**spec)
