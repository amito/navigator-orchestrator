import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from navigator_orchestrator.server import OrchestratorServer
from navigator_orchestrator.workflows.types import WorkflowResult


@pytest.fixture
def mock_engine():
    engine = AsyncMock()
    engine.start = AsyncMock(return_value=WorkflowResult(
        status="awaiting_input",
        thread_id="t-1",
        step="review_specs",
        prompt="Review specs.",
        data={"latency": "100ms"},
        editable_fields=["latency"],
    ))
    engine.resume = AsyncMock(return_value=WorkflowResult(
        status="complete",
        thread_id="t-1",
        data={"deployment": {"replicas": 2}},
    ))
    engine.cancel = AsyncMock(return_value=WorkflowResult(
        status="cancelled",
        thread_id="t-1",
    ))
    return engine


@pytest.fixture
def mock_passthrough():
    pt = AsyncMock()
    tool_def = MagicMock()
    tool_def.name = "create_project"
    tool_def.description = "Create a project"
    tool_def.inputSchema = {"type": "object", "properties": {"name": {"type": "string"}}}
    pt.tool_definitions = MagicMock(return_value=[tool_def])
    pt.tool_names = MagicMock(return_value={"create_project"})
    mock_content = MagicMock()
    mock_content.type = "text"
    mock_content.text = '{"id": "p-1"}'
    mock_result = MagicMock()
    mock_result.content = [mock_content]
    pt.call = AsyncMock(return_value=mock_result)
    return pt


@pytest.fixture
def mock_registry():
    from navigator_orchestrator.workflows.types import WorkflowInfo

    registry = MagicMock()
    registry.names = MagicMock(return_value=["model_recommendation"])
    registry.list_workflows = MagicMock(return_value=[
        WorkflowInfo("model_recommendation", "Recommend a model", ["step1", "step2"]),
    ])
    return registry


@pytest.fixture
def server(mock_engine, mock_passthrough, mock_registry):
    return OrchestratorServer(
        engine=mock_engine,
        passthrough=mock_passthrough,
        registry=mock_registry,
    )


async def test_list_tools(server):
    tools = await server.handle_list_tools()
    names = {t.name for t in tools}
    assert "start_model_recommendation" in names
    assert "resume_workflow" in names
    assert "cancel_workflow" in names
    assert "list_workflows" in names
    assert "create_project" in names


async def test_start_workflow(server, mock_engine):
    result = await server.handle_call_tool(
        "start_model_recommendation",
        {"description": "deploy a chatbot"},
    )
    mock_engine.start.assert_called_once_with(
        "model_recommendation", {"user_input": "deploy a chatbot"},
    )
    content = json.loads(result[0].text)
    assert content["status"] == "awaiting_input"
    assert content["step"] == "review_specs"


async def test_resume_workflow(server, mock_engine):
    result = await server.handle_call_tool(
        "resume_workflow",
        {"thread_id": "t-1", "user_input": {"latency": "200ms"}},
    )
    mock_engine.resume.assert_called_once_with("t-1", {"latency": "200ms"})
    content = json.loads(result[0].text)
    assert content["status"] == "complete"


async def test_cancel_workflow(server, mock_engine):
    result = await server.handle_call_tool(
        "cancel_workflow",
        {"thread_id": "t-1"},
    )
    mock_engine.cancel.assert_called_once_with("t-1")
    content = json.loads(result[0].text)
    assert content["status"] == "cancelled"


async def test_list_workflows(server):
    result = await server.handle_call_tool("list_workflows", {})
    content = json.loads(result[0].text)
    assert len(content["workflows"]) == 1
    assert content["workflows"][0]["name"] == "model_recommendation"


async def test_passthrough_tool(server, mock_passthrough):
    await server.handle_call_tool(
        "create_project",
        {"name": "test-project"},
    )
    mock_passthrough.call.assert_called_once_with("create_project", {"name": "test-project"})
