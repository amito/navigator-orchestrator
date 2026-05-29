from __future__ import annotations

from dataclasses import dataclass
from typing import Any



@dataclass
class MockMCPClient:
    """Mock MCP client that returns predefined responses per tool name."""

    responses: dict[str, Any]

    async def call_tool_parsed(self, name: str, arguments: dict) -> Any:
        if name not in self.responses:
            raise ValueError(f"Unexpected tool call: {name}")
        response = self.responses[name]
        if callable(response):
            return response(arguments)
        return response
