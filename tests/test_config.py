from navigator_orchestrator.config import Settings


def test_default_settings():
    settings = Settings()
    assert settings.rhoai_mcp_url == "http://localhost:8000/mcp"
    assert settings.host == "0.0.0.0"
    assert settings.port == 8001


def test_settings_from_env(monkeypatch):
    monkeypatch.setenv("ORCHESTRATOR_RHOAI_MCP_URL", "http://rhoai:9000/mcp")
    monkeypatch.setenv("ORCHESTRATOR_PORT", "9001")
    settings = Settings()
    assert settings.rhoai_mcp_url == "http://rhoai:9000/mcp"
    assert settings.port == 9001
