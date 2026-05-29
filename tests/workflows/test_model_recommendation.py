import pytest

from navigator_orchestrator.workflows.engine import WorkflowEngine
from navigator_orchestrator.workflows.model_recommendation import (
    build_model_recommendation,
    WORKFLOW_NAME,
    WORKFLOW_DESCRIPTION,
    WORKFLOW_STEPS,
)
from tests.conftest import MockMCPClient


def _make_engine(mock_client):
    engine = WorkflowEngine()
    builder = build_model_recommendation(mock_client)
    engine.register_graph(WORKFLOW_NAME, builder)
    return engine


@pytest.fixture
def mock_client():
    return MockMCPClient(
        responses={
            "extract_intent": {
                "task_type": "text-generation",
                "use_case": "chatbot",
            },
            "prepare_model_tech_specs": {
                "latency_p99": "100ms",
                "max_batch_size": 32,
                "gpu_type": "A100",
            },
            "get_recommended_models": [
                {"name": "Llama-3-8B", "score": 0.95},
                {"name": "Mistral-7B", "score": 0.88},
            ],
            "get_deployment_config": {
                "replicas": 2,
                "gpu_count": 1,
                "serving_runtime": "vllm",
            },
        }
    )


async def test_start_pauses_at_review_specs(mock_client):
    engine = _make_engine(mock_client)
    result = await engine.start(
        WORKFLOW_NAME,
        {
            "user_input": "deploy a chatbot model",
        },
    )
    assert result.status == "awaiting_input"
    assert result.step == "review_specs"
    assert result.data["latency_p99"] == "100ms"
    assert "latency_p99" in result.editable_fields


async def test_resume_pauses_at_pick_model(mock_client):
    engine = _make_engine(mock_client)
    r1 = await engine.start(WORKFLOW_NAME, {"user_input": "deploy a chatbot model"})
    assert r1.status == "awaiting_input"

    r2 = await engine.resume(r1.thread_id, {"latency_p99": "200ms"})
    assert r2.status == "awaiting_input"
    assert r2.step == "pick_model"
    assert len(r2.options) == 2
    assert r2.options[0]["name"] == "Llama-3-8B"


async def test_full_workflow_completes(mock_client):
    engine = _make_engine(mock_client)
    r1 = await engine.start(WORKFLOW_NAME, {"user_input": "deploy a chatbot model"})
    r2 = await engine.resume(r1.thread_id, {"latency_p99": "200ms"})
    r3 = await engine.resume(r2.thread_id, {"name": "Llama-3-8B", "score": 0.95})

    assert r3.status == "complete"
    assert r3.data["deployment_config"]["serving_runtime"] == "vllm"
    assert r3.data["selected_model"]["name"] == "Llama-3-8B"


async def test_workflow_metadata():
    assert WORKFLOW_NAME == "model_recommendation"
    assert isinstance(WORKFLOW_DESCRIPTION, str)
    assert len(WORKFLOW_STEPS) >= 4
