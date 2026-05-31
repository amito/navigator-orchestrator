from __future__ import annotations

import json
import logging
from contextlib import AsyncExitStack
from typing import Any

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

logger = logging.getLogger(__name__)


class RhoaiMCPClient:
    """Thin wrapper around the MCP client SDK for connecting to rhoai-mcp."""

    def __init__(self, url: str, auth_token: str | None = None) -> None:
        self.url = url
        self._auth_token = auth_token
        self._stack = AsyncExitStack()
        self._session: ClientSession | None = None

    @property
    def connected(self) -> bool:
        return self._session is not None

    async def connect(self) -> None:
        if self._session is not None:
            return
        # Start with a fresh stack each attempt
        self._stack = AsyncExitStack()

        try:
            headers: dict[str, str] = {}
            if self._auth_token:
                headers["Authorization"] = f"Bearer {self._auth_token}"
            read, write, _ = await self._stack.enter_async_context(
                streamablehttp_client(self.url, headers=headers)
            )
            self._session = await self._stack.enter_async_context(ClientSession(read, write))
            await self._session.initialize()
        except BaseException:
            # Abandon partial state — closing a broken streamablehttp_client
            # async generator can leak anyio cancel scopes into the event loop.
            self._stack = AsyncExitStack()
            self._session = None
            raise

    async def _ensure_connected(self) -> None:
        if self._session is None:
            logger.info("Attempting to connect to rhoai-mcp at %s", self.url)
            await self.connect()

    async def disconnect(self) -> None:
        await self._stack.aclose()
        self._session = None

    async def list_tools(self):
        """Return the list of tool definitions from rhoai-mcp."""
        await self._ensure_connected()
        result = await self._session.list_tools()
        return result.tools

    async def call_tool(self, name: str, arguments: dict[str, Any]):
        """Call a tool on rhoai-mcp. Raises RuntimeError on tool errors."""
        await self._ensure_connected()
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
