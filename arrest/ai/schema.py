from dataclasses import dataclass
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, create_model
from pydantic_xml import BaseXmlModel

from arrest.converters import get_converter_type
from arrest.handler import ResourceHandler
from arrest.params import _File, _Form
from arrest.utils import gen_unique_handler_name

PathParamsT = TypeVar("PathParamsT")
RequestBodyT = TypeVar("RequestBodyT")


class ToolArgs(BaseModel, Generic[PathParamsT, RequestBodyT]):
    """Uniform shape every tool's args model takes

    Parameters:
        path_params: The path parameters of the request, as a dynamic Pydantic model.
        request_body: The request body of the request, as a Pydantic model.
    """

    path_params: PathParamsT
    request_body: RequestBodyT


def build_path_params_model(
    handler: ResourceHandler, resource_name: str
) -> type[BaseModel]:
    """
    Example:

        ```python
        handler = ResourceHandler(
            method="GET",
            route="/{user_id:str}/posts/{post_id:uuid}",
            ...
        )

        path_params_model = build_path_params_model(handler, resource_name="users")

        # class get_users_user_id_posts_post_id_path_params(BaseModel):
        #     user_id: str
        #     post_id: UUID
        ```
    """

    param_types = handler._param_types or {}
    fields: dict[str, Any] = {
        name: (get_converter_type(converter), ...)
        for name, converter in param_types.items()
    }
    model_name = f"{gen_unique_handler_name(resource_name, route=handler.route, method=handler.method)}_path_params"
    return create_model(model_name, **fields)


@dataclass(kw_only=True)
class HandlerSchema:
    tool_args: type[ToolArgs[Any, Any]]
    return_model: type[Any] | None


def is_representable(annotation: Any) -> bool:
    """Whether `annotation` can be used as a tool's request/response schema.

    `None`, and any plain JSON-schema-representable type (`BaseModel`
    subclasses, scalars, containers, etc.), are representable. Only XML
    bodies (`BaseXmlModel`) and multipart bodies (`BaseModel`s with a
    `File()`/`Form()` field) are excluded — neither has a natural
    JSON-schema shape an LLM tool call can fill in. This single function is
    used to check both request and response types, so the two can't drift
    out of sync the way two separately-called checks could.
    """

    if annotation is None:
        return True
    if isinstance(annotation, type) and issubclass(annotation, BaseModel):
        if issubclass(annotation, BaseXmlModel):
            return False
        if any(
            isinstance(field_info, (_File, _Form))
            for field_info in annotation.model_fields.values()
        ):
            return False
    return True


def build_args_model(
    handler: ResourceHandler,
    resource_name: str,
) -> HandlerSchema | None:
    """Build the tool-facing schema for `handler`, or `None` if its request
    body can't be represented as a JSON-schema tool call (multipart or XML)."""

    request_type = handler.request
    if not is_representable(request_type):
        return None

    path_params_model = build_path_params_model(handler, resource_name)

    return HandlerSchema(
        tool_args=ToolArgs[path_params_model, request_type],
        return_model=handler.response if is_representable(handler.response) else None,
    )
