from __future__ import annotations

import json
from contextlib import AsyncExitStack
from typing import Any

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client


class RhoaiMCPClient:
    """Thin wrapper around the MCP client SDK for connecting to rhoai-mcp."""

    def __init__(self, url: str, auth_token: str | None = None) -> None:
        self.url = url
        self._auth_token = auth_token
        self._stack = AsyncExitStack()
        self._session: ClientSession | None = None

    async def connect(self) -> None:
        headers: dict[str, str] = {}
        if self._auth_token:
            headers["Authorization"] = f"Bearer {self._auth_token}"
        read, write, _ = await self._stack.enter_async_context(
            streamablehttp_client(self.url, headers=headers)
        )
        self._session = await self._stack.enter_async_context(
            ClientSession(read, write)
        )
        await self._session.initialize()

    async def disconnect(self) -> None:
        await self._stack.aclose()
        self._session = None

    async def list_tools(self):
        """Return the list of tool definitions from rhoai-mcp."""
        result = await self._session.list_tools()
        return result.tools

    async def call_tool(self, name: str, arguments: dict[str, Any]):
        """Call a tool on rhoai-mcp. Raises RuntimeError on tool errors."""
        result = await self._session.call_tool(name, arguments)
        if result.isError:
            error_text = result.content[0].text if result.content else "Unknown error"
            raise RuntimeError(f"rhoai-mcp tool {name!r} failed: {error_text}")
        return result

    async def call_tool_parsed(self, name: str, arguments: dict[str, Any]) -> Any:
        """Call a tool and parse JSON text response into a Python object."""
        result = await self.call_tool(name, arguments)
        text = result.content[0].text
        return json.loads(text)
