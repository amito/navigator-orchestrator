from __future__ import annotations

import json
from typing import Any

import mcp.types as types

from navigator_orchestrator.passthrough import ToolPassthrough
from navigator_orchestrator.workflows.engine import WorkflowEngine
from navigator_orchestrator.workflows.registry import WorkflowRegistry


class OrchestratorServer:
    """Core server logic — tool listing and call routing.

    Separated from MCP transport so it can be tested without HTTP.
    """

    def __init__(
        self,
        engine: WorkflowEngine,
        passthrough: ToolPassthrough,
        registry: WorkflowRegistry,
    ) -> None:
        self._engine = engine
        self._passthrough = passthrough
        self._registry = registry

    async def handle_list_tools(self) -> list[types.Tool]:
        tools: list[types.Tool] = []

        # Workflow start tools — one per registered workflow
        for info in self._registry.list_workflows():
            tools.append(types.Tool(
                name=f"start_{info.name}",
                description=info.description,
                inputSchema={
                    "type": "object",
                    "properties": {
                        "description": {
                            "type": "string",
                            "description": "Natural language description of what you want to do.",
                        },
                    },
                    "required": ["description"],
                },
            ))

        # Shared workflow management tools
        tools.append(types.Tool(
            name="resume_workflow",
            description="Resume a paused workflow with user input.",
            inputSchema={
                "type": "object",
                "properties": {
                    "thread_id": {"type": "string", "description": "The workflow thread ID."},
                    "user_input": {"type": "object", "description": "User-provided data."},
                },
                "required": ["thread_id", "user_input"],
            },
        ))
        tools.append(types.Tool(
            name="cancel_workflow",
            description="Cancel a running workflow.",
            inputSchema={
                "type": "object",
                "properties": {
                    "thread_id": {"type": "string", "description": "The workflow thread ID."},
                },
                "required": ["thread_id"],
            },
        ))
        tools.append(types.Tool(
            name="list_workflows",
            description="List available workflows with their descriptions and steps.",
            inputSchema={"type": "object", "properties": {}},
        ))

        # Passthrough tools from rhoai-mcp
        for tool_def in self._passthrough.tool_definitions():
            tools.append(types.Tool(
                name=tool_def.name,
                description=tool_def.description or "",
                inputSchema=tool_def.inputSchema,
            ))

        return tools

    async def handle_call_tool(
        self, name: str, arguments: dict[str, Any],
    ) -> list[types.TextContent]:
        # Workflow start tools
        for wf_name in self._registry.names():
            if name == f"start_{wf_name}":
                result = await self._engine.start(
                    wf_name, {"user_input": arguments["description"]},
                )
                return [types.TextContent(type="text", text=json.dumps(result.to_dict()))]

        # Workflow management tools
        if name == "resume_workflow":
            result = await self._engine.resume(
                arguments["thread_id"], arguments["user_input"],
            )
            return [types.TextContent(type="text", text=json.dumps(result.to_dict()))]

        if name == "cancel_workflow":
            result = await self._engine.cancel(arguments["thread_id"])
            return [types.TextContent(type="text", text=json.dumps(result.to_dict()))]

        if name == "list_workflows":
            workflows = [i.to_dict() for i in self._registry.list_workflows()]
            return [types.TextContent(
                type="text", text=json.dumps({"workflows": workflows}),
            )]

        # Passthrough to rhoai-mcp
        if name in self._passthrough.tool_names():
            result = await self._passthrough.call(name, arguments)
            return result.content

        raise ValueError(f"Unknown tool: {name!r}")
