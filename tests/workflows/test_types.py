from navigator_orchestrator.workflows.types import WorkflowResult, WorkflowInfo


def test_workflow_result_awaiting_input():
    result = WorkflowResult(
        status="awaiting_input",
        thread_id="abc-123",
        step="review_specs",
        prompt="Review the specs.",
        data={"latency_p99": "100ms"},
        editable_fields=["latency_p99"],
    )
    assert result.status == "awaiting_input"
    assert result.thread_id == "abc-123"
    assert result.step == "review_specs"
    d = result.to_dict()
    assert d["status"] == "awaiting_input"
    assert d["thread_id"] == "abc-123"
    assert d["step"] == "review_specs"
    assert d["data"] == {"latency_p99": "100ms"}


def test_workflow_result_complete():
    result = WorkflowResult(
        status="complete",
        thread_id="abc-123",
        data={"deployment_config": {"replicas": 2}},
    )
    d = result.to_dict()
    assert d["status"] == "complete"
    assert "step" not in d
    assert "prompt" not in d
    assert "editable_fields" not in d


def test_workflow_info():
    info = WorkflowInfo(
        name="model_recommendation",
        description="Recommend a model for deployment",
        steps=["extract_intent", "prepare_specs", "review_specs"],
    )
    assert info.name == "model_recommendation"
    d = info.to_dict()
    assert d["steps"] == ["extract_intent", "prepare_specs", "review_specs"]
