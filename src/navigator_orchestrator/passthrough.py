from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class ToolPassthrough:
    """Discovers tools from rhoai-mcp and proxies calls through."""

    def __init__(self, mcp_client: Any, exclude_names: set[str] | None = None) -> None:
        self._client = mcp_client
        self._exclude = exclude_names or set()
        self._tools: dict[str, Any] = {}  # name -> tool definition object
        self._discovered = False

    async def discover(self) -> None:
        """Fetch tool list from rhoai-mcp and cache definitions."""
        all_tools = await self._client.list_tools()
        self._tools = {
            t.name: t for t in all_tools if t.name not in self._exclude
        }
        self._discovered = True

    async def ensure_discovered(self) -> None:
        """Try discovery if it hasn't succeeded yet."""
        if self._discovered:
            return
        try:
            await self.discover()
        except BaseException:
            logger.debug("Passthrough discovery deferred — rhoai-mcp not available")

    def tool_names(self) -> set[str]:
        return set(self._tools.keys())

    def tool_definitions(self) -> list[Any]:
        return list(self._tools.values())

    async def call(self, name: str, arguments: dict[str, Any]) -> Any:
        if name not in self._tools:
            raise KeyError(f"Unknown passthrough tool: {name!r}")
        return await self._client.call_tool(name, arguments)
