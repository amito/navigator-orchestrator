from unittest.mock import AsyncMock, MagicMock

import pytest

from navigator_orchestrator.passthrough import ToolPassthrough


@pytest.fixture
def mock_mcp_client():
    client = AsyncMock()
    tool_a = MagicMock()
    tool_a.name = "create_project"
    tool_a.description = "Create a project"
    tool_a.inputSchema = {"type": "object", "properties": {"name": {"type": "string"}}}

    tool_b = MagicMock()
    tool_b.name = "list_workbenches"
    tool_b.description = "List workbenches"
    tool_b.inputSchema = {"type": "object", "properties": {}}

    client.list_tools = AsyncMock(return_value=[tool_a, tool_b])
    return client


async def test_discover_tools(mock_mcp_client):
    pt = ToolPassthrough(mock_mcp_client)
    await pt.discover()
    assert pt.tool_names() == {"create_project", "list_workbenches"}


async def test_discover_excludes_workflow_names(mock_mcp_client):
    pt = ToolPassthrough(mock_mcp_client, exclude_names={"create_project"})
    await pt.discover()
    assert pt.tool_names() == {"list_workbenches"}


async def test_get_tool_definitions(mock_mcp_client):
    pt = ToolPassthrough(mock_mcp_client)
    await pt.discover()
    defs = pt.tool_definitions()
    assert len(defs) == 2
    names = {d.name for d in defs}
    assert names == {"create_project", "list_workbenches"}


async def test_call_passthrough(mock_mcp_client):
    mock_content = MagicMock()
    mock_content.text = '{"id": "proj-1"}'
    mock_result = MagicMock()
    mock_result.content = [mock_content]
    mock_result.isError = False
    mock_mcp_client.call_tool = AsyncMock(return_value=mock_result)

    pt = ToolPassthrough(mock_mcp_client)
    await pt.discover()
    result = await pt.call("create_project", {"name": "test"})
    mock_mcp_client.call_tool.assert_called_once_with("create_project", {"name": "test"})
    assert result.content[0].text == '{"id": "proj-1"}'


async def test_call_unknown_tool(mock_mcp_client):
    pt = ToolPassthrough(mock_mcp_client)
    await pt.discover()
    with pytest.raises(KeyError, match="no_such_tool"):
        await pt.call("no_such_tool", {})
