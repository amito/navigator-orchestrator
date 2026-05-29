import pytest

from langgraph.constants import START, END
from langgraph.graph import StateGraph
from langgraph.types import interrupt
from typing_extensions import TypedDict

from navigator_orchestrator.workflows.engine import WorkflowEngine


class SimpleState(TypedDict):
    value: str
    user_response: str | None


def _build_simple_graph():
    """Graph with one interrupt node for testing."""
    builder = StateGraph(SimpleState)

    def step_a(state):
        return {"value": state["value"] + "_processed"}

    def ask_user(state):
        response = interrupt(
            {
                "step": "ask_user",
                "prompt": "Please confirm.",
                "data": {"current": state["value"]},
            }
        )
        return {"user_response": response}

    def step_b(state):
        return {"value": state["value"] + "_" + (state["user_response"] or "")}

    builder.add_node("step_a", step_a)
    builder.add_node("ask_user", ask_user)
    builder.add_node("step_b", step_b)
    builder.add_edge(START, "step_a")
    builder.add_edge("step_a", "ask_user")
    builder.add_edge("ask_user", "step_b")
    builder.add_edge("step_b", END)
    return builder


@pytest.fixture
def engine():
    e = WorkflowEngine()
    e.register_graph("simple", _build_simple_graph())
    return e


async def test_start_hits_interrupt(engine):
    result = await engine.start("simple", {"value": "hello", "user_response": None})
    assert result.status == "awaiting_input"
    assert result.step == "ask_user"
    assert result.prompt == "Please confirm."
    assert result.data == {"current": "hello_processed"}
    assert result.thread_id  # non-empty UUID


async def test_resume_completes(engine):
    result1 = await engine.start("simple", {"value": "hello", "user_response": None})
    assert result1.status == "awaiting_input"

    result2 = await engine.resume(result1.thread_id, "confirmed")
    assert result2.status == "complete"
    assert result2.data["value"] == "hello_processed_confirmed"
    assert result2.data["user_response"] == "confirmed"


async def test_resume_unknown_thread(engine):
    with pytest.raises(KeyError, match="Unknown thread"):
        await engine.resume("nonexistent-thread", "data")


async def test_cancel(engine):
    result = await engine.start("simple", {"value": "hello", "user_response": None})
    cancel_result = await engine.cancel(result.thread_id)
    assert cancel_result.status == "cancelled"

    with pytest.raises(KeyError, match="Unknown thread"):
        await engine.resume(result.thread_id, "too late")


async def test_start_unknown_workflow(engine):
    with pytest.raises(KeyError, match="Unknown workflow"):
        await engine.start("nonexistent", {"value": "x"})
