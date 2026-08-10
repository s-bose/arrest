import os
import sys
from pathlib import Path

import httpx
import pytest
from dotenv import load_dotenv
from pydantic_ai import Agent
from pydantic_ai.messages import ToolCallPart, ToolReturnPart
from pydantic_ai.models.anthropic import AnthropicModel

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
load_dotenv(REPO_ROOT / ".env")

from arrest._config import ArrestConfig  # noqa: E402
from arrest.ai.toolset import ArrestToolset  # noqa: E402
from example.app.main import app  # noqa: E402
from example.example_service.services import (  # noqa: E402
    example_fastapi_rest_application as service,
)

pytestmark = pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY"),
    reason="ANTHROPIC_API_KEY is not set",
)


def make_agent() -> Agent:
    config = ArrestConfig(
        client=httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://localhost:8080",
        )
    )
    toolset = ArrestToolset(service, config=config)
    model = AnthropicModel("claude-haiku-4-5-20251001")
    return Agent(model=model, toolsets=[toolset])


@pytest.mark.asyncio
async def test_agent_gets_random_user_then_their_tasks():
    agent = make_agent()

    result = await agent.run(
        "Get a random user, then list every task belonging to that user."
    )

    tool_calls = [
        part
        for message in result.all_messages()
        for part in message.parts
        if isinstance(part, ToolCallPart)
    ]
    tool_returns = [
        part
        for message in result.all_messages()
        for part in message.parts
        if isinstance(part, ToolReturnPart)
    ]

    call_names = [call.tool_name for call in tool_calls]
    assert "get_random_user" in call_names
    assert "get_tasks_for_user" in call_names
    # the user must be fetched before their tasks are looked up
    assert call_names.index("get_random_user") < call_names.index("get_tasks_for_user")

    # every tool call actually resolved to a returned result, none failed
    assert len(tool_returns) == len(tool_calls)

    user_id = next(
        call.args_as_dict()["path_params"]["user_id"]
        for call in tool_calls
        if call.tool_name == "get_tasks_for_user"
    )
    random_user_return = next(
        ret for ret in tool_returns if ret.tool_name == "get_random_user"
    )
    assert str(random_user_return.content.id) == str(user_id)  # type: ignore[union-attr]

    assert result.output
