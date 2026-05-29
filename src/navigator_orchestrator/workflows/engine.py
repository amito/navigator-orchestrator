from __future__ import annotations

import uuid
from typing import Any

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph
from langgraph.types import Command

from navigator_orchestrator.workflows.types import WorkflowResult


class WorkflowEngine:
    def __init__(self) -> None:
        self._checkpointer = MemorySaver()
        self._graphs: dict[str, Any] = {}  # name -> compiled graph
        self._threads: dict[str, str] = {}  # thread_id -> workflow name

    def register_graph(self, name: str, builder: StateGraph) -> None:
        self._graphs[name] = builder.compile(checkpointer=self._checkpointer)

    async def start(self, workflow_name: str, input_data: dict) -> WorkflowResult:
        if workflow_name not in self._graphs:
            raise KeyError(f"Unknown workflow: {workflow_name!r}")

        thread_id = str(uuid.uuid4())
        self._threads[thread_id] = workflow_name
        graph = self._graphs[workflow_name]
        config = {"configurable": {"thread_id": thread_id}}

        await graph.ainvoke(input_data, config)
        return await self._build_result(graph, config, thread_id)

    async def resume(self, thread_id: str, user_input: Any) -> WorkflowResult:
        if thread_id not in self._threads:
            raise KeyError(f"Unknown thread: {thread_id!r}")

        workflow_name = self._threads[thread_id]
        graph = self._graphs[workflow_name]
        config = {"configurable": {"thread_id": thread_id}}

        await graph.ainvoke(Command(resume=user_input), config)
        return await self._build_result(graph, config, thread_id)

    async def cancel(self, thread_id: str) -> WorkflowResult:
        if thread_id not in self._threads:
            raise KeyError(f"Unknown thread: {thread_id!r}")
        del self._threads[thread_id]
        return WorkflowResult(status="cancelled", thread_id=thread_id)

    async def _build_result(self, graph: Any, config: dict, thread_id: str) -> WorkflowResult:
        snapshot = await graph.aget_state(config)

        if snapshot.next:
            # Graph paused at an interrupt — extract interrupt payload
            interrupt_value = snapshot.tasks[0].interrupts[0].value
            return WorkflowResult(
                status="awaiting_input",
                thread_id=thread_id,
                step=interrupt_value.get("step"),
                prompt=interrupt_value.get("prompt"),
                data=interrupt_value.get("data"),
                editable_fields=interrupt_value.get("editable_fields"),
                options=interrupt_value.get("options"),
            )

        # Graph completed — return final state
        final_state = dict(snapshot.values)
        return WorkflowResult(status="complete", thread_id=thread_id, data=final_state)
