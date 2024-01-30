"""
OpenAPI Generator module

Note: only supports >=v3.0 specifications

Dependencies:
    - datamodel-code-generator
"""
import io
import itertools
import json
import os
import sys
from pathlib import Path
from typing import IO, Generator, Optional

import backoff
import httpx
import yaml

from arrest.defaults import MAX_RETRIES, OPENAPI_DIRECTORY, OPENAPI_SCHEMA_FILENAME
from arrest.exceptions import ArrestError
from arrest.http import Methods
from arrest.logging import logger

try:
    from datamodel_code_generator import DataModelType, InputFileType, OpenAPIScope, generate
except ImportError:
    sys.exit(1)

from arrest.openapi._config import Format
from arrest.openapi.init_template import InitTemplate
from arrest.openapi.resource_template import HandlerSchema, ResourceSchema, ResourceTemplate
from arrest.openapi.service_template import ServiceSchema, ServiceTemplate
from arrest.openapi.spec import OpenAPI, Operation, PathItem, Reference, Server
from arrest.openapi.utils import get_ref_schema, sanitize_name


class OpenAPIGenerator:
    def __init__(
        self,
        *,
        url: str,
        output_path: str,
        dir_name: Optional[str] = None,
        use_pydantic_v2: Optional[bool] = False,
    ) -> None:
        """
        class for generating Arrest services, resources and schema
        components from OpenAPI specification (>= v3.0)
        Generates three files:

        1. models.py (contains OpenAPI Schema component definitions)
        2. resources.py (Arrest Resources based on the path items)
        3. services.py (Arrest Services using the resources)


        Parameters:
            url:
                an HTTP url or full path to the OpenAPI specification (json or yaml)
            output_path:
                path where the generated files will be saved
            dir_name:
                (optional) specify the folder name containing the files

        """
        self.url: str = url
        self.output_path: str = output_path
        self.dir_name: str = dir_name
        self.use_pydantic_v2 = use_pydantic_v2

    @backoff.on_exception(
        backoff.expo,
        (httpx.HTTPError, httpx.TimeoutException),
        max_tries=MAX_RETRIES,
        jitter=backoff.full_jitter,
    )
    def download_openapi_spec(self) -> bytes:
        if self.url.startswith("http"):
            response = httpx.get(self.url)
            response.raise_for_status()
            return response.read()

        else:
            with open(self.url, "rb") as file:
                return file.read()

    def generate_schema(self, fmt: Optional[Format] = None):
        """Generates the boilerplate files against an OpenAPI Spec

        Parameters:
            fmt (Optional[Format], optional): specification format [json, yaml, yml]

        Raises:
            ArrestError
        """
        openapi_bytes = self.download_openapi_spec()
        fmt = fmt if fmt else self.url.split(".")[-1]
        openapi: OpenAPI = self.parse_openapi(fmt=fmt, data=io.BytesIO(openapi_bytes))

        output_path = Path(self.output_path)
        if not output_path.exists():
            raise ArrestError("output path does not exist")

        service_name = self.dir_name or self.get_service_name(openapi)
        output_path = output_path / service_name
        schema_path = output_path / OPENAPI_SCHEMA_FILENAME

        Path.mkdir(output_path, exist_ok=True)

        self.generate_component_schema(input_bytes=openapi_bytes, schema_path=schema_path)
        resources = self.generate_resource_file(
            openapi=openapi, schema_path=schema_path, resource_path=output_path
        )
        self.generate_service_file(openapi=openapi, service_path=output_path, resources=resources)
        InitTemplate(destination_path=output_path).render_and_save()

    def generate_component_schema(self, input_bytes: bytes, schema_path: Path | str) -> None:
        generate(
            input_=input_bytes.decode("utf-8"),
            input_file_type=InputFileType.OpenAPI,
            openapi_scopes=[OpenAPIScope.Schemas],
            output=schema_path,
            output_model_type=DataModelType.PydanticV2BaseModel
            if self.use_pydantic_v2
            else DataModelType.PydanticBaseModel,
        )
        logger.info(f"generated pydantic models from schema definitions in : {schema_path}")

    def generate_service_file(
        self,
        *,
        openapi: OpenAPI,
        service_name: Optional[str] = None,
        service_path: Path | str,
        resources: list[ResourceSchema],
    ):
        services = list(
            self._build_arrest_service(openapi=openapi, service_name=service_name, resources=resources)
        )

        ServiceTemplate(services=services, destination_path=service_path).render_and_save()
        logger.info(f"generated arrest services in : {service_path}/services.py")

    def get_service_name(self, openapi: OpenAPI, service_name: Optional[str] = None) -> str:
        name = service_name or openapi.info.title or OPENAPI_DIRECTORY
        return sanitize_name(name)

    def generate_resource_file(
        self, openapi: OpenAPI, schema_path: Path | str, resource_path: Path | str
    ) -> list[ResourceSchema]:
        resources = list(self._build_arrest_resources(openapi=openapi))
        path, _ = os.path.splitext(schema_path)
        module = Path(path).stem

        ResourceTemplate(
            schema_module=module, resources=resources, destination_path=resource_path
        ).render_and_save()
        logger.info(f"generated arrest resources in : {resource_path}/resources.py")
        return resources

    def _build_arrest_service(
        self, openapi: OpenAPI, service_name: Optional[str] = None, resources: list[ResourceSchema] = None
    ) -> Generator[ServiceSchema, None, None]:
        name = service_name or self.get_service_name(openapi)

        resource_names = [res.name for res in resources]
        for idx, server in enumerate(openapi.servers):
            for idxx, url in enumerate(self._extract_url(server)):
                suffix = f"_{idx}" if idx else ""
                suffix += f"_{idxx}" if idxx else ""
                service_id = f"{name}{suffix}"
                yield ServiceSchema(
                    service_id=service_id,
                    name=name,
                    url=url,
                    description=server.description,
                    resources=resource_names,
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

    def _build_arrest_resources(self, openapi: OpenAPI) -> Generator[ResourceSchema, None, None]:
        def prefix(path: str) -> str:
            """
            ("/root/xyz/123") -> "root"
            ("/root/{id}") -> "root"
            """
            return path[1:].split("/")[0]

        for key, group in itertools.groupby(openapi.paths.keys(), key=prefix):
            routes = list(group)
            path_items = [openapi.paths.get(route) for route in routes]
            handlers: list[HandlerSchema] = []
            for route, path_item in zip(routes, path_items):
                route = route.removeprefix(f"/{key}")
                handlers.extend(self._build_handlers(route=route, path_item=path_item))

            yield ResourceSchema(name=key, route=f"/{key}", handlers=handlers)

    def _build_handlers(self, route: str, path_item: PathItem) -> list[HandlerSchema]:
        handlers = []
        for method in list(Methods):
            operation: Operation
            if operation := getattr(path_item, str(method).lower(), None):
                request_class = self.get_request_schema(operation)
                response_class = self.get_response_schema(operation)

                handlers.append(
                    HandlerSchema(route=route, method=method, request=request_class, response=response_class)
                )

        return handlers

    def get_request_schema(self, operation: Operation) -> Optional[str]:
        if not (request_body := operation.requestBody):
            logger.debug("no request body defined")
            return None

        if isinstance(request_body, Reference):
            return get_ref_schema(request_body)

        if media := request_body.content.get("application/json", None):
            return get_ref_schema(media.media_type_schema)

    def get_response_schema(self, operation: Operation) -> Optional[str]:
        if not operation.responses or not (
            success_response := operation.responses.get(str(httpx.codes.OK), None)
        ):
            logger.debug("no success (200) response defined")
            return None
        if isinstance(success_response, Reference):
            return get_ref_schema(success_response)

        if success_response.content and (media := success_response.content.get("application/json", None)):
            return get_ref_schema(media.media_type_schema)

    @classmethod
    def load_dict(cls, fmt: Format, data: IO) -> dict:
        if fmt == Format.json:
            return json.load(data)
        elif fmt in (Format.yaml, Format.yml):
            return yaml.load(data, yaml.SafeLoader)

    @classmethod
    def parse_openapi(cls, fmt: Format, data: IO) -> OpenAPI:
        spec = cls.load_dict(fmt, data)
        return OpenAPI(**spec)
