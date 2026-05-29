from unittest.mock import AsyncMock, MagicMock

import pytest

from navigator_orchestrator.mcp_client import RhoaiMCPClient


async def test_list_tools():
    mock_tool = MagicMock()
    mock_tool.name = "create_project"
    mock_tool.description = "Create a new project"
    mock_tool.inputSchema = {"type": "object", "properties": {"name": {"type": "string"}}}

    mock_session = AsyncMock()
    mock_session.initialize = AsyncMock()
    mock_tools_result = MagicMock()
    mock_tools_result.tools = [mock_tool]
    mock_session.list_tools = AsyncMock(return_value=mock_tools_result)

    client = RhoaiMCPClient.__new__(RhoaiMCPClient)
    client._session = mock_session

    tools = await client.list_tools()
    assert len(tools) == 1
    assert tools[0].name == "create_project"


async def test_call_tool():
    mock_content = MagicMock()
    mock_content.text = '{"id": "proj-1"}'
    mock_result = MagicMock()
    mock_result.content = [mock_content]
    mock_result.isError = False

    mock_session = AsyncMock()
    mock_session.call_tool = AsyncMock(return_value=mock_result)

    client = RhoaiMCPClient.__new__(RhoaiMCPClient)
    client._session = mock_session

    result = await client.call_tool("create_project", {"name": "test"})
    mock_session.call_tool.assert_called_once_with("create_project", {"name": "test"})
    assert result.content[0].text == '{"id": "proj-1"}'


async def test_call_tool_error():
    mock_result = MagicMock()
    mock_result.isError = True
    mock_content = MagicMock()
    mock_content.text = "Permission denied"
    mock_result.content = [mock_content]

    mock_session = AsyncMock()
    mock_session.call_tool = AsyncMock(return_value=mock_result)

    client = RhoaiMCPClient.__new__(RhoaiMCPClient)
    client._session = mock_session

    with pytest.raises(RuntimeError, match="Permission denied"):
        await client.call_tool("create_project", {"name": "test"})
