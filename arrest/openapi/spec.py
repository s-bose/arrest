"""
Set of pydantic wrappers around openapi dict
supports openapi >= v3.0
"""
from typing import Optional, Union

from pydantic import BaseModel, ConfigDict, Extra, Field

from arrest._config import PYDANTIC_V2


class Base(BaseModel):
    if PYDANTIC_V2:
        model_config = ConfigDict(extra="allow", populate_by_name=True)

    else:

        class Config:
            extra = Extra.allow
            allow_population_by_field_name = True


class Info(Base):
    title: str
    version: str


class ServerVariable(Base):
    enum: Optional[list[str]] = None
    default: str


class Server(Base):
    url: str
    description: Optional[str] = None
    variables: Optional[dict[str, ServerVariable]] = None


class Reference(Base):
    ref: str = Field(alias="$ref")


class MediaType(BaseModel):
    media_type_schema: Optional[Union[Reference, dict]] = Field(default=None, alias="schema")


class RequestBody(BaseModel):
    content: dict[str, MediaType]


class Response(Base):
    content: Optional[dict[str, MediaType]] = None


class Operation(Base):
    responses: Optional[dict[str, Union[Reference, Response]]] = None
    requestBody: Optional[Union[Reference, RequestBody]] = None


class PathItem(Base):
    ref: Optional[str] = Field(default=None, alias="$ref")
    get: Optional[Operation] = None
    post: Optional[Operation] = None
    put: Optional[Operation] = None
    patch: Optional[Operation] = None
    delete: Optional[Operation] = None
    head: Optional[Operation] = None
    options: Optional[Operation] = None


class OpenAPI(Base):
    info: Info
    servers: list[Server] = [Server(url="/")]
    paths: dict[str, PathItem]
