import httpx
import pytest
from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.models.test import TestModel

from arrest.ai.meta import ToolMeta
from arrest.ai.toolset import ArrestToolset
from arrest.handler import H
from arrest.http import Methods
from arrest.resource import Resource
from arrest.service import Service
from tests import TEST_DEFAULT_SERVICE_NAME, TEST_DEFAULT_SERVICE_URL


class WidgetOut(BaseModel):
    id: int
    name: str


class GadgetOut(BaseModel):
    id: int
    kind: str


def make_service() -> Service:
    """Two resources, each with one tool-enabled handler, wired the way a
    real caller would (`Service(...)` + `add_resource(...)`)."""

    service = Service(name=TEST_DEFAULT_SERVICE_NAME, url=TEST_DEFAULT_SERVICE_URL)
    service.add_resource(
        Resource(
            route="/widgets",
            name="widgets",
            handlers=[
                H(
                    Methods.GET,
                    "/{id:int}",
                    None,
                    WidgetOut,
                    tool_meta=ToolMeta(name="get_widget"),
                )
            ],
        )
    )
    service.add_resource(
        Resource(
            route="/gadgets",
            name="gadgets",
            handlers=[
                H(
                    Methods.GET,
                    "/{id:int}",
                    None,
                    GadgetOut,
                    tool_meta=ToolMeta(name="get_gadget"),
                )
            ],
        )
    )
    return service


@pytest.mark.asyncio
async def test_agent_makes_real_request_to_correct_tool(mock_httpx):
    service = make_service()

    widgets_route = mock_httpx.get(url__regex=r"/widgets/\d+").mock(
        return_value=httpx.Response(200, json={"id": 1, "name": "sprocket"})
    )
    gadgets_route = mock_httpx.get(url__regex=r"/gadgets/\d+").mock(
        return_value=httpx.Response(200, json={"id": 2, "kind": "gizmo"})
    )

    toolset = ArrestToolset(service)
    agent = Agent(model=TestModel(), toolsets=[toolset])

    result = await agent.run("fetch the widget and the gadget")

    # the real call actually went out, exactly once each
    assert widgets_route.call_count == 1
    assert gadgets_route.call_count == 1

    # each call landed on the endpoint belonging to its own tool, not the
    # other one's
    widget_request = widgets_route.calls.last.request
    assert widget_request.url.path == "/widgets/0"

    gadget_request = gadgets_route.calls.last.request
    assert gadget_request.url.path == "/gadgets/0"

    assert result.output is not None
    assert "get_widget" in result.output
    assert "get_gadget" in result.output


@pytest.mark.asyncio
async def test_agent_calls_only_the_selected_tool(mock_httpx):
    """Force the model to call only `get_widget`, and confirm `get_gadget`'s
    endpoint never gets hit -- proving dispatch is keyed by tool name."""

    service = make_service()

    # No mocked route for `/gadgets` at all -- if `get_gadget` were called
    # anyway, respx would raise on the unmatched request.
    widgets_route = mock_httpx.get(url__regex=r"/widgets/\d+").mock(
        return_value=httpx.Response(200, json={"id": 1, "name": "sprocket"})
    )

    toolset = ArrestToolset(service)
    agent = Agent(model=TestModel(call_tools=["get_widget"]), toolsets=[toolset])

    result = await agent.run("fetch only the widget")

    assert widgets_route.call_count == 1
    assert len(mock_httpx.calls) == 1

    assert result.output == '{"get_widget":{"id":1,"name":"sprocket"}}'
