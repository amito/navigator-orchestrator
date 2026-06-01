"""Entry point: python -m navigator_orchestrator"""

from __future__ import annotations

import asyncio
import logging

from mcp.server.lowlevel import Server
import mcp.types as types

from navigator_orchestrator.auth import auth_token_var, extract_bearer_token
from navigator_orchestrator.config import Settings
from navigator_orchestrator.mcp_client import RhoaiMCPClient
from navigator_orchestrator.passthrough import ToolPassthrough
from navigator_orchestrator.server import OrchestratorServer
from navigator_orchestrator.workflows.engine import WorkflowEngine
from navigator_orchestrator.workflows.model_recommendation import (
    WORKFLOW_DESCRIPTION,
    WORKFLOW_NAME,
    WORKFLOW_STEPS,
    build_model_recommendation,
)
from navigator_orchestrator.workflows.registry import WorkflowRegistry

logger = logging.getLogger(__name__)


async def main() -> None:
    settings = Settings()

    # 1. Create MCP client (connects lazily on first tool call)
    mcp_client = RhoaiMCPClient(settings.rhoai_mcp_url)
    logger.info("rhoai-mcp configured at %s (will connect on demand)", settings.rhoai_mcp_url)

    # 2. Build workflow registry and engine
    registry = WorkflowRegistry()
    registry.register(
        WORKFLOW_NAME, build_model_recommendation, WORKFLOW_DESCRIPTION, WORKFLOW_STEPS
    )

    engine = WorkflowEngine()
    builder = build_model_recommendation(mcp_client)
    engine.register_graph(WORKFLOW_NAME, builder)

    # 3. Set up passthrough (discovers lazily via ensure_discovered)
    workflow_tool_names = {f"start_{n}" for n in registry.names()}
    workflow_tool_names |= {"resume_workflow", "cancel_workflow", "list_workflows"}
    passthrough = ToolPassthrough(mcp_client, exclude_names=workflow_tool_names)

    # 4. Wire up orchestrator server
    orchestrator = OrchestratorServer(engine, passthrough, registry)

    # 5. Create low-level MCP server
    mcp_server = Server("navigator-orchestrator")

    @mcp_server.list_tools()
    async def list_tools() -> list[types.Tool]:
        return await orchestrator.handle_list_tools()

    @mcp_server.call_tool()
    async def call_tool(
        name: str,
        arguments: dict,  # type: ignore[type-arg]
    ) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
        result = await orchestrator.handle_call_tool(name, arguments)
        return result  # type: ignore[return-value]

    # 6. Run with Streamable HTTP transport
    import contextlib
    from collections.abc import AsyncIterator

    from mcp.server.streamable_http_manager import StreamableHTTPSessionManager

    session_manager = StreamableHTTPSessionManager(app=mcp_server)

    from starlette.applications import Starlette
    from starlette.routing import Mount

    @contextlib.asynccontextmanager
    async def lifespan(app: Starlette) -> AsyncIterator[None]:
        async with session_manager.run():
            yield
        await mcp_client.disconnect()

    class AuthTokenMiddleware:
        """ASGI middleware that captures the Bearer token from incoming requests."""

        def __init__(self, app):
            self.app = app

        async def __call__(self, scope, receive, send):
            if scope["type"] == "http":
                headers = dict(scope.get("headers", []))
                raw = headers.get(b"authorization", b"").decode()
                auth_token_var.set(extract_bearer_token(raw))
            await self.app(scope, receive, send)

    app = Starlette(
        routes=[Mount("/mcp", app=session_manager.handle_request)],
        lifespan=lifespan,
    )
    app = AuthTokenMiddleware(app)

    import uvicorn

    config = uvicorn.Config(app, host=settings.host, port=settings.port)
    server = uvicorn.Server(config)
    logger.info("Starting orchestrator on %s:%d", settings.host, settings.port)
    await server.serve()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
