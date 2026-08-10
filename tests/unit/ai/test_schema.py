from typing import Any
from uuid import UUID

import pytest
from pydantic import BaseModel, ValidationError
from pydantic_xml import BaseXmlModel, element

from arrest.ai.schema import (
    HandlerSchema,
    build_args_model,
    build_path_params_model,
    is_representable,
)
from arrest.handler import H, ResourceHandler
from arrest.http import Methods
from arrest.params import File, Form
from arrest.resource import Resource


class Plain(BaseModel):
    name: str


class PlainResponse(BaseModel):
    id: int
    name: str


class WithFileField(BaseModel):
    name: str
    content: bytes = File()


class WithFormField(BaseModel):
    name: str = Form()


class XmlBody(BaseXmlModel):
    name: str = element()


def make_handler(
    route: str,
    method: Methods = Methods.GET,
    request: Any = None,
    response: Any = None,
) -> ResourceHandler:
    """Build a `ResourceHandler` bound the way `Resource` would bind it, so
    `_param_types` is populated via the real `compile_path` flow instead of
    poking private attributes directly."""

    resource = Resource(
        route="/base",
        handlers=[H(method=method, route=route, request=request, response=response)],
    )
    for handler in resource.routes.values():
        if handler.method == method and handler.route == route:
            return handler
    raise AssertionError(
        f"handler for {method} {route} was not bound"
    )  # pragma: no cover


@pytest.mark.parametrize(
    "annotation, expected",
    [
        (None, True),
        (Plain, True),
        (str, True),
        (int, True),
        (list[Plain], True),
        (dict[str, Plain], True),
        (WithFileField, False),
        (WithFormField, False),
        (XmlBody, False),
    ],
)
def test_is_representable(annotation: Any, expected: bool):
    assert is_representable(annotation) is expected


@pytest.mark.parametrize(
    "route, expected_fields",
    [
        ("/", {}),
        ("/{id}", {"id": str}),
        ("/{id:int}", {"id": int}),
        ("/{id:float}", {"id": float}),
        ("/{id:uuid}", {"id": UUID}),
        ("/{a:int}/sub/{b:uuid}", {"a": int, "b": UUID}),
    ],
)
def test_build_path_params_model_fields(route: str, expected_fields: dict[str, type]):
    handler = make_handler(route)
    model = build_path_params_model(handler, resource_name="widgets")

    actual_fields = {
        name: field.annotation for name, field in model.model_fields.items()
    }
    assert actual_fields == expected_fields
    assert all(field.is_required() for field in model.model_fields.values())


@pytest.mark.parametrize(
    "route, method, expected_name",
    [
        ("/{id}", Methods.GET, "get_widgets_id_path_params"),
        ("/{id}", Methods.POST, "post_widgets_id_path_params"),
        ("/", Methods.DELETE, "delete_widgetss_path_params"),
    ],
)
def test_build_path_params_model_name(route: str, method: Methods, expected_name: str):
    handler = make_handler(route, method=method)
    model = build_path_params_model(handler, resource_name="widgets")
    assert model.__name__ == expected_name


@pytest.mark.parametrize(
    "request_type",
    [WithFileField, WithFormField, XmlBody],
)
def test_build_args_model_skips_unrepresentable_request(request_type: Any):
    handler = make_handler("/{id}", method=Methods.POST, request=request_type)
    assert build_args_model(handler, resource_name="widgets") is None


@pytest.mark.parametrize(
    "response_type",
    [WithFileField, WithFormField, XmlBody],
)
def test_build_args_model_excludes_unrepresentable_return_model(
    response_type: Any,
):
    handler = make_handler("/{id}", method=Methods.GET, response=response_type)
    schema = build_args_model(handler, resource_name="widgets")

    assert schema is not None
    assert schema.return_model is None


def test_build_args_model_normal_request_and_response():
    handler = make_handler(
        "/{id:int}",
        method=Methods.PUT,
        request=Plain,
        response=PlainResponse,
    )
    schema = build_args_model(handler, resource_name="widgets")

    assert isinstance(schema, HandlerSchema)
    assert schema.return_model is PlainResponse

    instance = schema.tool_args(path_params={"id": 5}, request_body={"name": "bob"})
    assert instance.path_params.id == 5
    assert instance.request_body == Plain(name="bob")


def test_build_args_model_no_request_body_requires_explicit_none():
    handler = make_handler("/{id:int}", method=Methods.GET, request=None)
    schema = build_args_model(handler, resource_name="widgets")

    assert schema is not None

    with pytest.raises(ValidationError):
        schema.tool_args(path_params={"id": 5})

    instance = schema.tool_args(path_params={"id": 5}, request_body=None)
    assert instance.request_body is None


def test_build_args_model_scalar_request_body():
    handler = make_handler("/{id}", method=Methods.POST, request=str)
    schema = build_args_model(handler, resource_name="widgets")

    assert schema is not None
    instance = schema.tool_args(path_params={"id": "abc"}, request_body="hello")
    assert instance.request_body == "hello"


def test_build_args_model_no_response_has_no_return_model():
    handler = make_handler("/{id}", method=Methods.DELETE, response=None)
    schema = build_args_model(handler, resource_name="widgets")

    assert schema is not None
    assert schema.return_model is None
