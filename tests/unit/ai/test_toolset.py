from typing import Any

import httpx
import pytest
from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai._run_context import RunContext
from pydantic_ai.exceptions import ModelRetry, ToolFailed, UserError
from pydantic_ai.models.test import TestModel

from arrest._config import ArrestConfig
from arrest.ai.meta import ToolMeta
from arrest.ai.toolset import (
    DEFAULT_RETRY_ON_ERRORS,
    ArrestToolset,
    ArrestToolsetTool,
    matches_include_exclude,
)
from arrest.exceptions import ArrestHTTPException, HandlerNotFound, RequestError
from arrest.handler import H
from arrest.http import Methods
from arrest.params import File
from arrest.resource import Resource
from arrest.response import Response as ArrestResponse
from arrest.service import Service
from arrest.utils import gen_unique_handler_name


class Body(BaseModel):
    name: str


class Out(BaseModel):
    id: int


class WithFileField(BaseModel):
    name: str
    content: bytes = File()


def make_context() -> RunContext[Any]:
    return RunContext(deps=None, model=None, usage=None)


def make_toolset(
    *handlers: Any, resource_name: str = "widgets", **toolset_kwargs: Any
) -> tuple[ArrestToolset, Resource]:
    """A one-resource service and its toolset. Extra kwargs go straight to
    `ArrestToolset` (`config`, `include`, `exclude`, `retry_on_errors`, ...)."""
    service = Service(name="example", url="http://example.com")
    resource = Resource(
        route=f"/{resource_name}", name=resource_name, handlers=list(handlers)
    )
    service.add_resource(resource)
    return ArrestToolset(service, **toolset_kwargs), resource


def fake_response(data: Any = None, status_code: int = 200) -> ArrestResponse:
    return ArrestResponse(
        data=data,
        status_code=status_code,
        url=None,
        elapsed=None,
        raw=None,
        request=None,
    )


def validated_args(tool: Any, path_params: dict[str, Any], request_body: Any) -> Any:
    """Build `call_tool`'s `tool_args` the way pydantic_ai actually does: run
    raw values through the tool's own `args_validator`, producing a live
    `ToolArgs[...]` instance rather than a plain dict."""
    return tool.args_validator.validate_python(
        {"path_params": path_params, "request_body": request_body}
    )


def stub_request(
    resource: Resource, result: Any = None, *, error: Exception | None = None
) -> dict[str, Any]:
    """Swap `resource.request` for a stub that returns `result` (or raises
    `error`). Returns the dict the stub records its call kwargs into."""
    captured: dict[str, Any] = {}

    async def fake_request(**kwargs: Any) -> Any:
        captured.update(kwargs)
        if error is not None:
            raise error
        return result

    resource.request = fake_request
    return captured


async def call_only_tool(
    toolset: ArrestToolset, path_params: dict[str, Any], request_body: Any = None
) -> Any:
    """Resolve the toolset's single tool and invoke it the way pydantic_ai
    would -- through `get_tools` and a validated `tool_args`."""
    ctx = make_context()
    tools = await toolset.get_tools(ctx)
    name, tool = next(iter(tools.items()))
    return await toolset.call_tool(
        name, validated_args(tool, path_params, request_body), ctx, tool
    )


# _build_tools / get_tools


@pytest.mark.asyncio
async def test_get_tools_uses_gen_unique_handler_name():
    toolset, _ = make_toolset(
        H(Methods.PUT, "/{id:int}", Body, Out, tool_meta=ToolMeta())
    )
    tools = await toolset.get_tools(make_context())

    expected_name = gen_unique_handler_name(
        "widgets", route="/{id:int}", method=Methods.PUT
    )
    assert list(tools.keys()) == [expected_name]


@pytest.mark.asyncio
async def test_get_tools_skips_unrepresentable_request():
    toolset, _ = make_toolset(
        H(Methods.POST, "/{id:int}", WithFileField, None, tool_meta=ToolMeta())
    )
    tools = await toolset.get_tools(make_context())

    assert tools == {}


@pytest.mark.asyncio
async def test_get_tools_skips_handlers_without_tool_meta():
    toolset, _ = make_toolset(H(Methods.GET, "/{id:int}", None, Out))
    tools = await toolset.get_tools(make_context())

    assert tools == {}


@pytest.mark.parametrize(
    "spec, resource, method, route, expected",
    [
        # set[str] -- resource-level, any method/route
        ({"widgets"}, "widgets", Methods.GET, "/{id}", True),
        ({"widgets"}, "gadgets", Methods.GET, "/{id}", False),
        # Mapping[str, set[Methods]] -- method-level, any route
        ({"widgets": {Methods.GET}}, "widgets", Methods.GET, "/{id}", True),
        ({"widgets": {Methods.GET}}, "widgets", Methods.PUT, "/{id}", False),
        ({"widgets": {Methods.GET}}, "gadgets", Methods.GET, "/{id}", False),
        # Mapping[str, Mapping[Methods, set[str]]] -- route-level
        ({"widgets": {Methods.GET: {"/{id}"}}}, "widgets", Methods.GET, "/{id}", True),
        (
            {"widgets": {Methods.GET: {"/{id}"}}},
            "widgets",
            Methods.GET,
            "/other",
            False,
        ),
        ({"widgets": {Methods.GET: {"/{id}"}}}, "widgets", Methods.PUT, "/{id}", False),
        ({"widgets": {Methods.GET: {"/{id}"}}}, "gadgets", Methods.GET, "/{id}", False),
    ],
)
def test_matches_include_exclude(
    spec: Any, resource: str, method: Methods, route: str, expected: bool
):
    assert (
        matches_include_exclude(spec, resource=resource, method=method, route=route)
        is expected
    )


@pytest.mark.asyncio
async def test_get_tools_include_filters_by_resource():
    service = Service(name="example", url="http://example.com")
    service.add_resource(
        Resource(
            route="/widgets",
            name="widgets",
            handlers=[H(Methods.GET, "/{id:int}", None, Out, tool_meta=ToolMeta())],
        )
    )
    service.add_resource(
        Resource(
            route="/gadgets",
            name="gadgets",
            handlers=[H(Methods.GET, "/{id:int}", None, Out, tool_meta=ToolMeta())],
        )
    )

    toolset = ArrestToolset(service, include={"widgets"})
    tools = await toolset.get_tools(make_context())

    assert len(tools) == 1
    tool = next(iter(tools.values()))
    assert isinstance(tool, ArrestToolsetTool)
    assert tool.resource.name == "widgets"


@pytest.mark.asyncio
async def test_get_tools_include_filters_by_method():
    toolset, _ = make_toolset(
        H(Methods.GET, "/{id:int}", None, Out, tool_meta=ToolMeta(name="get_widget")),
        H(Methods.PUT, "/{id:int}", Body, Out, tool_meta=ToolMeta(name="put_widget")),
        include={"widgets": {Methods.GET}},
    )

    tools = await toolset.get_tools(make_context())

    assert list(tools.keys()) == ["get_widget"]


@pytest.mark.asyncio
async def test_get_tools_exclude_filters_by_route():
    toolset, _ = make_toolset(
        H(Methods.GET, "/{id:int}", None, Out, tool_meta=ToolMeta(name="get_by_id")),
        H(Methods.GET, "/search", None, Out, tool_meta=ToolMeta(name="search")),
        exclude={"widgets": {Methods.GET: {"/{id:int}"}}},
    )

    tools = await toolset.get_tools(make_context())

    assert list(tools.keys()) == ["search"]


@pytest.mark.asyncio
async def test_get_tools_raises_on_duplicate_name():
    toolset, _ = make_toolset(
        H(Methods.GET, "/{id:int}", None, Out, tool_meta=ToolMeta(name="dup")),
        H(Methods.PUT, "/{id:int}", Body, Out, tool_meta=ToolMeta(name="dup")),
    )

    with pytest.raises(UserError):
        await toolset.get_tools(make_context())


@pytest.mark.parametrize(
    "response, expect_return_schema",
    [
        (Out, True),
        (list[Out], True),
        (None, False),
    ],
)
@pytest.mark.asyncio
async def test_get_tools_return_schema_wiring(
    response: Any, expect_return_schema: bool
):
    toolset, _ = make_toolset(
        H(Methods.GET, "/{id:int}", None, response, tool_meta=ToolMeta())
    )
    tools = await toolset.get_tools(make_context())
    tool_def = next(iter(tools.values())).tool_def

    assert (tool_def.return_schema is not None) is expect_return_schema
    assert tool_def.include_return_schema is expect_return_schema


# call_tool


@pytest.mark.asyncio
async def test_call_tool_dispatches_path_params_and_body():
    toolset, resource = make_toolset(
        H(Methods.PUT, "/{id:int}", Body, Out, tool_meta=ToolMeta())
    )
    captured = stub_request(resource, fake_response({"id": 1}))

    result = await call_only_tool(toolset, {"id": 5}, {"name": "bob"})

    assert result == {"id": 1}
    assert captured["path"] == "/5"
    assert captured["request"] == Body(name="bob")


@pytest.mark.asyncio
async def test_call_tool_with_no_request_body():
    toolset, resource = make_toolset(
        H(Methods.GET, "/{id:int}", None, Out, tool_meta=ToolMeta())
    )
    captured = stub_request(resource, fake_response({"id": 1}))

    await call_only_tool(toolset, {"id": 5})

    assert captured["request"] is None


@pytest.mark.asyncio
async def test_call_tool_returns_raw_result_from_handler_callback():
    # A handler with a `callback` makes `resource.request()` return whatever
    # the callback produces instead of an `ArrestResponse` -- `call_tool`
    # must pass that value straight through (after truncation), not assume
    # it's a response object.
    toolset, resource = make_toolset(
        H(Methods.GET, "/{id:int}", None, Out, tool_meta=ToolMeta())
    )
    stub_request(resource, {"id": 1, "via": "callback"})

    result = await call_only_tool(toolset, {"id": 5})

    assert result == {"id": 1, "via": "callback"}


@pytest.mark.parametrize(
    "error, expected_exception",
    [
        # transport-level failure -- worth another attempt
        (RequestError("request timed out"), ModelRetry),
        # the path we built matched no handler -- retrying can't fix that
        (HandlerNotFound(message="no matching handler"), ToolFailed),
    ],
)
@pytest.mark.asyncio
async def test_call_tool_maps_arrest_errors(
    error: Exception, expected_exception: type[Exception]
):
    toolset, resource = make_toolset(
        H(Methods.GET, "/{id:int}", None, Out, tool_meta=ToolMeta())
    )
    stub_request(resource, error=error)

    with pytest.raises(expected_exception):
        await call_only_tool(toolset, {"id": 5})


# A status code is retryable iff it's in `retry_on_errors`; the exact default
# membership is pinned by `test_default_retry_on_errors_is_transient_only`,
# so these only need one code either side of that line.
@pytest.mark.parametrize(
    "status_code, expected_exception",
    [
        (503, ModelRetry),  # transient
        (400, ToolFailed),  # bad request -- model must change its input
        (501, ToolFailed),  # 5xx, but a permanent capability gap
    ],
)
@pytest.mark.parametrize("raised", [True, False], ids=["raised", "returned"])
@pytest.mark.asyncio
async def test_call_tool_maps_http_status(
    status_code: int, expected_exception: type[Exception], raised: bool
):
    """Arrest surfaces a failed call either by raising `ArrestHTTPException`
    or by returning an unsuccessful `ArrestResponse` (when `raise_for_status`
    is off) -- both must map to the same tool-level outcome."""
    toolset, resource = make_toolset(
        H(Methods.GET, "/{id:int}", None, Out, tool_meta=ToolMeta())
    )
    if raised:
        stub_request(
            resource,
            error=ArrestHTTPException(status_code=status_code, data={"error": "boom"}),
        )
    else:
        stub_request(resource, fake_response({"error": "boom"}, status_code))

    with pytest.raises(expected_exception):
        await call_only_tool(toolset, {"id": 5})


def test_default_retry_on_errors_is_transient_only():
    assert DEFAULT_RETRY_ON_ERRORS == {408, 429, 500, 502, 503, 504}


@pytest.mark.parametrize(
    "status_code, expected_exception",
    [
        (400, ModelRetry),  # opted in, though not transient
        (503, ToolFailed),  # a default entry, opted out
    ],
)
@pytest.mark.asyncio
async def test_call_tool_respects_custom_retry_on_errors(
    status_code: int, expected_exception: type[Exception]
):
    toolset, resource = make_toolset(
        H(Methods.GET, "/{id:int}", None, Out, tool_meta=ToolMeta()),
        retry_on_errors=[400],
    )
    stub_request(
        resource,
        error=ArrestHTTPException(status_code=status_code, data={"error": "boom"}),
    )

    with pytest.raises(expected_exception):
        await call_only_tool(toolset, {"id": 5})


# __aenter__ / __aexit__ -- pydantic_ai's lifecycle hooks, driven here the
# way it drives them: as a context manager.


@pytest.mark.asyncio
async def test_supplied_config_is_merged_into_resource_config():
    toolset, resource = make_toolset(
        H(Methods.GET, "/{id:int}", None, Out, tool_meta=ToolMeta()),
        config=ArrestConfig(headers={"X-Custom": "1"}),
    )

    async with toolset:
        assert resource.config is not None
        assert resource.config.headers == {"X-Custom": "1"}
        # no client supplied -- toolset creates its own pooled one
        assert toolset._client is not None
        assert resource.config.client is toolset._client


@pytest.mark.asyncio
async def test_user_supplied_client_is_reused():
    user_client = httpx.AsyncClient()
    toolset, resource = make_toolset(
        H(Methods.GET, "/{id:int}", None, Out, tool_meta=ToolMeta()),
        config=ArrestConfig(client=user_client),
    )

    async with toolset:
        # a client was already supplied -- toolset must not create its own
        assert toolset._client is None
        assert resource.config is not None
        assert resource.config.client is user_client

    assert not user_client.is_closed
    await user_client.aclose()


@pytest.mark.asyncio
async def test_aexit_restores_resource_config_and_closes_own_client():
    toolset, resource = make_toolset(
        H(Methods.GET, "/{id:int}", None, Out, tool_meta=ToolMeta())
    )
    assert resource.config is None

    async with toolset:
        pooled_client = toolset._client
        assert pooled_client is not None
        assert resource.config is not None

    assert resource.config is None
    assert toolset._client is None
    assert pooled_client.is_closed


def test_id_defaults_from_service_name():
    toolset, _ = make_toolset(
        H(Methods.GET, "/{id:int}", None, Out, tool_meta=ToolMeta())
    )
    assert toolset.id == "arrest-example-service"


def test_id_uses_explicit_override():
    service = Service(name="example", url="http://example.com")
    toolset = ArrestToolset(service, id="custom-id")
    assert toolset.id == "custom-id"


# _apply_truncation


def test_apply_truncation_raise_raises_tool_failed():
    toolset, _ = make_toolset(H(Methods.GET, "/", None, None))
    meta = ToolMeta(max_items=1, on_truncate="raise")

    with pytest.raises(ToolFailed):
        toolset._apply_truncation([1, 2], meta)


def test_apply_truncation_within_limit_is_noop():
    toolset, _ = make_toolset(H(Methods.GET, "/", None, None))
    meta = ToolMeta(max_items=5, on_truncate="note")

    result = toolset._apply_truncation([1, 2], meta)

    assert result == [1, 2]


def test_apply_truncation_note_returns_wrapped_payload():
    toolset, _ = make_toolset(H(Methods.GET, "/", None, None))
    meta = ToolMeta(max_items=1, on_truncate="note")

    result = toolset._apply_truncation([1, 2], meta)

    assert result == {
        "items": [1],
        "truncated": True,
        "total_items": 2,
        "returned_items": 1,
    }


# End-to-end via a real Agent + TestModel -- drives the toolset through
# pydantic_ai's actual tool-calling pipeline, not hand-built `tool_args`.


@pytest.mark.asyncio
async def test_agent_with_test_model_calls_tool_end_to_end():
    toolset, resource = make_toolset(
        H(Methods.PUT, "/{id:int}", Body, Out, tool_meta=ToolMeta())
    )

    captured: dict[str, Any] = {}

    async def fake_request(**kwargs: Any) -> ArrestResponse:
        captured.update(kwargs)
        return fake_response({"id": 1})

    resource.request = fake_request

    agent = Agent(model=TestModel(), toolsets=[toolset])
    result = await agent.run("call the tool")

    assert captured["method"] == Methods.PUT
    assert isinstance(captured["request"], Body)
    assert "path" in captured
    assert result.output is not None
