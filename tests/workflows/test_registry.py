import pytest

from navigator_orchestrator.workflows.registry import WorkflowRegistry


def _dummy_builder(mcp_client):
    """Placeholder builder — returns a string instead of a real graph."""
    return "compiled_graph"


def test_register_and_get():
    registry = WorkflowRegistry()
    registry.register(
        name="model_recommendation",
        builder=_dummy_builder,
        description="Recommend a model",
        steps=["extract_intent", "prepare_specs"],
    )
    defn = registry.get("model_recommendation")
    assert defn.name == "model_recommendation"
    assert defn.builder is _dummy_builder
    assert defn.description == "Recommend a model"


def test_get_unknown_raises():
    registry = WorkflowRegistry()
    with pytest.raises(KeyError, match="no_such_workflow"):
        registry.get("no_such_workflow")


def test_list_workflows():
    registry = WorkflowRegistry()
    registry.register("wf_a", _dummy_builder, "Workflow A", ["step1"])
    registry.register("wf_b", _dummy_builder, "Workflow B", ["step1", "step2"])
    infos = registry.list_workflows()
    assert len(infos) == 2
    names = {i.name for i in infos}
    assert names == {"wf_a", "wf_b"}


def test_names():
    registry = WorkflowRegistry()
    registry.register("alpha", _dummy_builder, "Alpha", [])
    registry.register("beta", _dummy_builder, "Beta", [])
    assert set(registry.names()) == {"alpha", "beta"}
