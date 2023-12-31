import json
from typing import IO, Literal

import yaml
from openapi_pydantic import OpenAPI
from openapi_pydantic.v3 import v3_0_3, v3_1_0

# from arrest import Service, Resource


def load_dict(format: Literal["json", "yaml"], spec: IO) -> dict:
    if format == "json":
        return json.load(spec)
    elif format == "yaml":
        return yaml.load(spec, yaml.SafeLoader)


def parse_openapi(format: Literal["json", "yaml"], data: IO) -> OpenAPI:
    spec = load_dict(format, data)

    if spec["openapi"].startswith("3.1"):
        return v3_1_0.OpenAPI(**spec)
    elif spec["openapi"].startswith("3.0"):
        return v3_0_3.OpenAPI(**spec)


# def to_service(spec: OpenAPI):
#     title = spec.info.title
#     # service = Service(name=title, url="abc")
#     spec.servers

# TODO
