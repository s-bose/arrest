import asyncio
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv
from pydantic_ai import Agent
from pydantic_ai.messages import ToolCallPart, ToolReturnPart
from pydantic_ai.models.anthropic import AnthropicModel

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
load_dotenv(REPO_ROOT / ".env")

from arrest._config import ArrestConfig  # noqa: E402
from arrest.ai.toolset import ArrestToolset  # noqa: E402
from example.app.main import app  # noqa: E402
from example.example_service.services import (  # noqa: E402
    example_fastapi_rest_application as service,
)


async def main() -> None:
    config = ArrestConfig(
        client=httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://localhost:8080",
        )
    )
    toolset = ArrestToolset(service, config=config)

    model = AnthropicModel("claude-haiku-4-5-20251001")
    agent = Agent(model=model, toolsets=[toolset])

    result = await agent.run(
        "Get a random user, then list every task belonging to that user."
    )

    print("\n=== tool calls ===")
    for message in result.all_messages():
        for part in message.parts:
            if isinstance(part, ToolCallPart):
                print(f"  -> {part.tool_name}({part.args})")
            elif isinstance(part, ToolReturnPart):
                print(f"  <- {part.tool_name} returned: {part.content}")

    print("\n=== final output ===")
    print(result.output)


if __name__ == "__main__":
    asyncio.run(main())
