from __future__ import annotations

from typing import Any, TypedDict

from langgraph.constants import START, END
from langgraph.graph import StateGraph
from langgraph.types import interrupt

WORKFLOW_NAME = "model_recommendation"
WORKFLOW_DESCRIPTION = (
    "Recommend and configure a model for deployment. Walks through intent extraction, "
    "technical spec review, model selection, and deployment configuration."
)
WORKFLOW_STEPS = [
    "extract_intent",
    "prepare_specs",
    "review_specs",
    "get_recommendations",
    "pick_model",
    "get_deployment",
]


class ModelRecommendationState(TypedDict, total=False):
    user_input: str
    intent: dict[str, Any] | None
    specs: dict[str, Any] | None
    user_spec_overrides: dict[str, Any] | None
    recommendations: list[dict[str, Any]] | None
    selected_model: dict[str, Any] | None
    deployment_config: dict[str, Any] | None
    error: str | None


def build_model_recommendation(mcp_client: Any) -> StateGraph:
    """Build the model recommendation LangGraph StateGraph.

    Args:
        mcp_client: Object with async ``call_tool_parsed(name, arguments)`` method.

    Returns:
        An uncompiled StateGraph (caller compiles with checkpointer).
    """
    builder = StateGraph(ModelRecommendationState)

    async def extract_intent(state: ModelRecommendationState):
        result = await mcp_client.call_tool_parsed(
            "extract_intent",
            {"text": state["user_input"]},
        )
        return {"intent": result}

    async def prepare_specs(state: ModelRecommendationState):
        intent = state.get("intent") or {}
        result = await mcp_client.call_tool_parsed("prepare_model_tech_specs", intent)
        return {"specs": result}

    async def get_recommendations(state: ModelRecommendationState):
        specs = state.get("specs") or {}
        overrides = state.get("user_spec_overrides")
        if overrides:
            specs = {**specs, **overrides}
        result = await mcp_client.call_tool_parsed("get_recommended_models", specs)
        return {"recommendations": result}

    async def get_deployment(state: ModelRecommendationState):
        result = await mcp_client.call_tool_parsed(
            "get_deployment_config",
            {"model": state.get("selected_model")},
        )
        return {"deployment_config": result}

    def review_specs(state: ModelRecommendationState):
        response = interrupt(
            {
                "step": "review_specs",
                "prompt": "Review the technical specs for your use case.",
                "data": state.get("specs") or {},
                "editable_fields": ["latency_p99", "max_batch_size", "gpu_type"],
            }
        )
        return {"user_spec_overrides": response}

    def pick_model(state: ModelRecommendationState):
        response = interrupt(
            {
                "step": "pick_model",
                "prompt": "Pick a model to deploy.",
                "options": state.get("recommendations") or [],
            }
        )
        return {"selected_model": response}

    builder.add_node("extract_intent", extract_intent)
    builder.add_node("prepare_specs", prepare_specs)
    builder.add_node("review_specs", review_specs)
    builder.add_node("get_recommendations", get_recommendations)
    builder.add_node("pick_model", pick_model)
    builder.add_node("get_deployment", get_deployment)

    builder.add_edge(START, "extract_intent")
    builder.add_edge("extract_intent", "prepare_specs")
    builder.add_edge("prepare_specs", "review_specs")
    builder.add_edge("review_specs", "get_recommendations")
    builder.add_edge("get_recommendations", "pick_model")
    builder.add_edge("pick_model", "get_deployment")
    builder.add_edge("get_deployment", END)

    return builder
