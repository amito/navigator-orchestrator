from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_prefix": "ORCHESTRATOR_"}

    rhoai_mcp_url: str = "http://localhost:8000/mcp"
    host: str = "0.0.0.0"
    port: int = 8001
