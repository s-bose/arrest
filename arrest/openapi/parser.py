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

import httpx
import yaml

from arrest.defaults import (
    MAX_RETRIES,
    OPENAPI_DIRECTORY,
    OPENAPI_SCHEMA_FILENAME,
    ROOT_RESOURCE,
)
from arrest.exceptions import ArrestError
from arrest.http import Methods
from arrest.logging import logger
from arrest.utils import retry

try:
    from datamodel_code_generator import (
        InputFileType,
        OpenAPIScope,
        generate,
    )
    from datamodel_code_generator.enums import DataModelType
except ImportError:  # pragma: no cover
    sys.exit(1)

from arrest.openapi._config import Format
from arrest.openapi.init_template import InitTemplate
from arrest.openapi.resource_template import (
    HandlerSchema,
    ResourceSchema,
    ResourceTemplate,
)
from arrest.openapi.service_template import ServiceSchema, ServiceTemplate
from arrest.openapi.spec import OpenAPI, Operation, PathItem, Reference, Server
from arrest.openapi.utils import convert_to_pascal, get_ref_schema
from arrest.utils import sanitize_name


class OpenAPIGenerator:
    """Generates boilerplate code from an OpenAPI specification.

    Supports OpenAPI v3.0+ specifications in JSON and YAML formats.
    """

    def __init__(
        self,
        url: str,
        output_dir: Path = OPENAPI_DIRECTORY,
        schema_filename: str = OPENAPI_SCHEMA_FILENAME,
    ):
        self.url = url
        self.output_dir = output_dir / ROOT_RESOURCE
        self.schema_filename = schema_filename

        self.schema: OpenAPI | None = None
        self.service: ServiceSchema | None = None

    @retry(
        max_retries=MAX_RETRIES,
        exceptions=(
            httpx.HTTPError,
            httpx.TimeoutException,
            httpx.RequestError,
            Exception,
        ),
    )
    def download_openapi_spec(self) -> bytes:
        if self.url.startswith("http"):
            response = httpx.get(self.url, timeout=30.0)
            response.raise_for_status()
            return response.read()

        else:
            with open(self.url, "rb") as file:
                return file.read()

    def generate_schema(self, fmt: Optional[Format] = None, silent: bool = False):
        """Generates the boilerplate files against an OpenAPI Spec

        Parameters:
            fmt (Optional[Format], optional): specification format [json, yaml, yml]

        Raises:
            ValueError: If the provided format is not supported.
        """
        data = self.download_openapi_spec()

        if fmt is None:
            try:
                spec = json.loads(data)
            except json.JSONDecodeError:
                spec = yaml.safe_load(data)
        elif fmt.value == Format.json:
            spec = json.loads(data)
        elif fmt.value in {Format.yaml, Format.yml}:
            spec = yaml.safe_load(data)
        else:
            raise ArrestError(f"{fmt.value} is not a supported format for code generation.")

        if not isinstance(spec, dict):
            raise ArrestError("Unexpected OpenAPI specification content.")

        self.schema = OpenAPI(**spec)

        self.schema.servers = self.schema.servers if isinstance(self.schema.servers, list) else []
        self.schema.info = self.schema.info if self.schema.info else {}
        self.schema.external_docs = self.schema.external_docs if self.schema.external_docs else {}
        self.schema.tags = self.schema.tags if isinstance(self.schema.tags, list) else []
        self.schema.security = self.schema.security if isinstance(self.schema.security, list) else []

        service_name = sanitize_name(self.schema.info.get("title", ""))
        logger.debug("service_name: %s", service_name)
        self.service = ServiceSchema(
            name=service_name,
            url=self.schema.servers[0].get("url", "") if self.schema.servers else "",
        )

        if not silent:
            logger.info(
                "OpenAPI Content fetched. Service: %s, servers: %s, tags: %s",
                service_name,
                self.schema.servers,
                [tag.get("name", "") for tag in self.schema.tags],
            )

    def generate_models(self, spec_text: str) -> str:
        """Generate pydantic models from the OpenAPI specification.

        Parameters:
            spec_text (str): The JSON specification text.

        Returns:
            str: Generated models code.
        """
        output = io.StringIO()

        try:
            generate(
                input_=io.StringIO(spec_text),
                input_file_type=InputFileType.OpenAPI,
                output=output,
                output_model_type=DataModelType.PydanticV2BaseModel,
                openapi_scopes=[
                    OpenAPIScope.Schemas,
                    OpenAPIScope.Parameters,
                ],
            )
        except Exception as e:
            raise ArrestError(f"Error generating models: {str(e)}") from e

        return output.getvalue()

    def _create_root_init(self, schema_files: list[str]) -> None:
        """Create the root-level __init__.py that imports all schemas."""
        root_init_path = self.output_dir / "schemas" / "__init__.py"
        root_init_path.parent.mkdir(parents=True, exist_ok=True)

        init_template = InitTemplate(schema_files=schema_files)
        root_init_content = init_template.render()

        with open(root_init_path, "w", encoding="utf-8") as f:
            f.write(root_init_content)

    def _populate_schema_methods(
        self, resource: ResourceSchema
    ) -> list[HandlerSchema]:
        """Populate handler schemas for a resource from the OpenAPI specification."""
        schema_handlers: list[HandlerSchema] = []

        for path_str, path_item in self.schema.paths.items():
            operations = path_item.get_operations()
            if not operations:
                continue

            sanitized_path = path_str.strip("/")
            path_parts = sanitized_path.split("/")

            if resource.name not in path_parts:
                continue

            for method, operation in operations.items():
                handler_method = self._create_handler_method(
                    method=method,
                    operation=operation,
                    path=path_str,
                    path_item=path_item,
                )
                schema_handlers.append(handler_method)

        return schema_handlers

    def _create_handler_method(
        self,
        method: str,
        operation: Operation,
        path: str,
        path_item: PathItem,
    ) -> HandlerSchema:
        """Create a handler schema from an OpenAPI operation."""
        handler_schema = HandlerSchema(
            handler_name=operation.operation_id or f"{method}_{hash(path)}",
            http_method=Methods(method),
            route=path,
            request_schemas=[],
            response_schema=None,
        )

        return handler_schema

    def _check_stop_iteration(
        self, operation: Operation, path_item: PathItem, path: str
    ) -> Generator[HandlerSchema, None, None]:
        """Check if the current path and operation combination should stop iteration."""
        if operation.deprecated:
            return StopIteration

        # Skip websocket paths
        if "websocket" in path.lower():
            return StopIteration

        return None

    def generate_service_and_resources(self) -> tuple[ServiceSchema, list[ResourceSchema]]:
        """Generate service and resource schemas from the OpenAPI specification."""
        resource_map: dict[str, ResourceSchema] = {}

        for path_str, path_item in self.schema.paths.items():
            resource_name = self._extract_resource_name(path_str)

            if resource_name not in resource_map:
                resource_map[resource_name] = ResourceSchema(
                    name=resource_name,
                    url=path_str,
                    handlers=[],
                )

            for method, operation in path_item.get_operations().items():
                if (stop := self._check_stop_iteration(operation, path_item, path_str)):
                    if stop is StopIteration:
                        continue

                handler = self._create_handler_method(
                    method=method,
                    operation=operation,
                    path=path_str,
                    path_item=path_item,
                )
                resource_map[resource_name].handlers.append(handler)

        return self.service, list(resource_map.values())

    def _extract_resource_name(self, path_str: str) -> str:
        """Extract resource name from the path string."""
        sanitized_path = path_str.strip("/")
        path_parts = sanitized_path.split("/")

        # Use first meaningful path part
        non_param_parts = [
            part for part in path_parts if not part.startswith("{")
        ]
        if non_param_parts:
            return non_param_parts[0]

        # Fallback to unique path
        return sanitize_name(path_str.replace("/", "_"))

    def _write_resource_files(self, resources: list[ResourceSchema]) -> None:
        """Write resource template files to disk."""
        for resource in resources:
            resource_dir = self.output_dir / resource.name
            resource_dir.mkdir(parents=True, exist_ok=True)

            resource_template = ResourceTemplate(resource=resource)
            resource_content = resource_template.render()

            init_content = f"from .{resource.name}_resource import {convert_to_pascal(resource.name)}Resource\n"

            with open(resource_dir / "__init__.py", "w", encoding="utf-8") as f:
                f.write(init_content)

            with open(
                resource_dir / f"{resource.name}_resource.py",
                "w",
                encoding="utf-8",
            ) as f:
                f.write(resource_content)

        # Write main __init__.py
        self._create_root_init(
            schema_files=[resource.name for resource in resources]
        )

    def _write_service_file(self, service: ServiceSchema) -> None:
        """Write the service template file to disk."""
        service_template = ServiceTemplate(service=service)
        service_content = service_template.render()

        service_dir = self.output_dir
        service_dir.mkdir(parents=True, exist_ok=True)

        with open(service_dir / "service.py", "w", encoding="utf-8") as f:
            f.write(service_content)

    def generate(
        self,
        models: bool = True,
        resources: bool = True,
        service: bool = True,
        fmt: Optional[Format] = None,
        silent: bool = False,
    ) -> None:
        """Main entry point for generating code from the OpenAPI specification.
        """
        self.generate_schema(fmt=fmt, silent=silent)

        if models:
            spec_json = json.dumps(self.schema.model_dump(by_alias=True), indent=2)
            self._write_model_files(spec_json)